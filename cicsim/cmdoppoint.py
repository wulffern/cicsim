#!/usr/bin/env python3


import cicsim as cs
import cicspi as csi
import re
import glob
import os
from cicsim.utils import parse_runfile

class CmdOpPoint(cs.Command):

    def __init__(self):
        pass

    def calcOpPoints(self,runfile):
        files = parse_runfile(runfile)

        for f in files:
            self.calcOpPoint(f)

    def _getInstance(self,sp,path):

        print(path)


        print(path)


    def calcOpPoint(self,fname):

        sp = csi.SpiceParser()

        #print(fname + ".spi")
        fspice = fname + ".spi"
        dirname = os.path.dirname(fspice)
        fspicebase = os.path.basename(fspice)
        with self.pushd(dirname):
            sp.parseFile(fspicebase,includeLocal=True)

        #print(sp.keys())
        raws = glob.glob(fname + "*.raw")

        devices = dict()
 #       data = list()
        for raw in raws:
            df = cs.toDataFrame(raw)

            #- Get mosfet currents
            for k in df.keys():
                m = re.search(r"^(\S+)\((.*)\)$",k)
                if(m):
                    #print(m.groups())
                    stype = m.groups()[0]
                    path = m.groups()[1]
                    #if(stype != "v"):
                    #
                    device_type = "x"
                    if(path.startswith("m")):
                        device_type = "m"
                        path = path[2:]

                    if(path.startswith("@")):
                        device_type = path[1]
                        path = path[3:]


                    patharr = path.upper().split(".")
                    (inst,foundpath) = sp.getPathInstance(patharr)
                    if(inst is not None):
                        #print(path,inst.subcktName)
                        if(re.search("((n|p)fet)|((n|p)ch)|ATR",inst.subcktName)):
                            if(foundpath not in devices):
                                devices[foundpath] = dict()
                                devices[foundpath]["inst"] = inst
                                devices[foundpath]["path"] = dict()
                            devices[foundpath]["path"][path] = df
                        #print(inst.subcktName)
                        pass
        for key in sorted(devices.keys()):
            obj = devices[key]
            #print("\n".join(obj["path"].keys()))
            #print("\n\n")


        #print(spi)
#        print(data)

#        print(raws)
        #raws = glob
        #df = cs.
