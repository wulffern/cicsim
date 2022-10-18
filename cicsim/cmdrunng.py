######################################################################
##        Copyright (c) 2020 Carsten Wulff Software, Norway
## ###################################################################
## Created       : wulff at 2020-12-13
## ###################################################################
##  The MIT License (MIT)
##
##  Permission is hereby granted, free of charge, to any person obtaining a copy
##  of this software and associated documentation files (the "Software"), to deal
##  in the Software without restriction, including without limitation the rights
##  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
##  copies of the Software, and to permit persons to whom the Software is
##  furnished to do so, subject to the following conditions:
##
##  The above copyright notice and this permission notice shall be included in all
##  copies or substantial portions of the Software.
##
##  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
##  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
##  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
##  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
##  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
##  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
##  SOFTWARE.
##
######################################################################

# TODO Add hash of spice netlist. Don't rerun if all spice files are the same.
#       However, what should I do about .includes?

import cicsim as cs
import re
import os
import errno
import yaml
import shutil as sh
import sys
import importlib
import datetime

class CmdRunNg(cs.CdsConfig):
    """ Run ngspice
    """

    def __init__(self,testbench,oformat,runsim,corners):
        self.testbench = testbench
        self.oformat = oformat
        self.runsim = runsim
        self.corners = corners

        super().__init__()


    def removeFile(self,filename):
        os.remove(filename) if os.path.exists(filename) else 0

    def ngspice(self):
        options = ""
        includes = ""
        if("ngspice" in self.config):
            if("options" in self.config["ngspice"]):
                options = self.config["ngspice"]["options"]
            else:
                options = ""

        cmd = f"ngspice {options} {includes} {self.ldst_spi} -r {self.raw} | tee {self.log}"
        
        self.comment(cmd)

        #- Remove old files
        self.removeFile(self.log)
        self.removeFile(self.raw)
        self.removeFile(self.dst_yaml)


        return os.system(f"cd {self.rundir}; {cmd}")

    def ngspiceMeas(self):

        cmd = f"ngspice -b {self.ldst_meas}  | tee {self.ldst_meas_log}"

        self.comment(cmd)

        #- Remove old files
        self.removeFile(self.fname + ".logm")
        return os.system(f"cd {self.rundir}; {cmd}")

    def replaceLine(self,line):

        selfkeys = "|".join(list(self.__dict__.keys()))
        res = "{cic(%s)}" % selfkeys
        m = re.search(res,line)

        if(m is not None):
            for mg in m.groups():
                self.comment("Replacing  {cic%s} = %s" %(mg,self.__dict__[mg]))

                line = line.replace("{cic%s}" %mg,self.__dict__[mg])
        return line

    def makeSpiceFile(self,corner):

        ss = ""
        if("corner" in self.config):
            for c in corner:
                if(c in self.config["corner"]):
                    sstr = self.config["corner"][c] + "\n"

                    #- Expand any os variables in lib string
                    sstr = os.path.expandvars(sstr)
                    ss += sstr
                else:
                    ss += "*define " + c.upper() + "\n"

        os.makedirs(self.rundir,exist_ok=True)

        with open(self.fdest,"w") as fo:
            print("cicsimgen " + self.testbench,file=fo)
            print(ss,file=fo)

            with open(self.filename,"r") as fi:

                #- Check for #defines
                state = 0
                buffer = ""
                buffif = ""
                buffelse = ""
                dkey = ""
                for l in fi:
                    if(l.startswith("#ifdef")):
                        d = re.split("\s+",l)
                        dkey = d[1]
                        state = 1
                        continue
                        #l = "*" + l
                    if(l.startswith("#else")):
                        state = 2
                        #l = "*" + l
                        continue
                    if(l.startswith("#endif")):
                        if(dkey in corner):
                            buffer += buffif
                        else:
                            buffer += buffelse
                        state = 0
                        dkey = 0
                        buffif = ""
                        buffelse = ""
                        continue
                        #l = "*" + l

                    if(state == 0):
                        buffer += l
                    elif(state == 1 ):
                        buffif += l
                    elif(state == 2 ):
                        buffelse += l
                
                line = buffer

                line = self.replaceLine(line)

                print(line,file=fo)

    def makeMeasFile(self):
        #- Check for a meas file
        with open(self.src_meas) as fi:
            with open(self.dst_meas,"w") as fo:
                for line in fi:
                    line = self.replaceLine(line)
                    fo.write(line)


    def parseLog(self):

        analysis = False
        data = dict()
        with open(self.dst_log) as fi:
            for l in fi:
                if(analysis and re.search("=",l)):
                    m = re.search("^([^\s]+)\s*=\s*([^\s]+)\s",l)
                    if(m):
                        key = m.groups()[0].strip()
                        val = m.groups()[1].strip()
                        data[key] = float(val)

                if(re.search("binary raw file",l)):
                    analysis = False

                m = re.search("Measurements for (.*)$",l)
                if(m):
                    analysis = True

        #- Check if there is a measurement log, and read it
        if(os.path.exists(self.dst_meas_log)):
            analysis = False
            with open(self.dst_meas_log) as fi:
                for l in fi:
                    if(analysis and re.search("=",l)):
                        m = re.search("^([^\s]+)\s*=\s*([^\s]+)\s",l)
                        if(m):
                            key = m.groups()[0].strip()
                            val = m.groups()[1].strip()
                            data[key] = float(val)
                    if(re.search("^\s*MEAS_START",l)):
                        analysis = True
                    if(re.search("^\s*MEAS_END",l)):
                        analysis = False



        with open(self.dst_yaml,"w") as fo:
            self.comment(f"Writing {self.dst_yaml}")
            yaml.dump(data,fo)


    def run(self):
        startTime = datetime.datetime.now()
        
        self.filename = self.testbench + ".spi"
        if(not os.path.exists(self.filename)):
            self.error(f"Testbench {filename} does not exists in this folder")
            return

        permutations = self.getPermutations(self.corners)

        self.src_meas = self.testbench + ".meas"
        self.src_py = self.testbench + ".py"

        pyRunLater = list()
        files = list()
        for p in permutations:

            #- Permutation variables
            self.fname = f"output_{self.testbench}" + os.path.sep + self.testbench +  "_"+ "".join(p)
            self.name =  self.testbench +  "_"+ "".join(p)
            self.fdest = self.fname + ".spi"
            self.ldst_spi = self.name + ".spi"
            self.dst_meas = self.fname + ".meas"
            self.ldst_meas = self.name + ".meas"
            self.dst_meas_log = self.fname + ".logm"
            self.ldst_meas_log = self.name + ".logm"
            self.log = self.name + ".log"
            self.dst_log = self.fname + ".log"
            self.dst_yaml = self.fname + ".yaml"
            self.ldst_yaml = self.name + ".yaml"
            self.dst_raw = self.fname + ".raw"
            self.raw = self.name + ".raw"


            self.rundir = os.path.dirname(self.fdest)


            selfkeys = "|".join(list(self.__dict__.keys()))
            res = "{cic(%s)}" % selfkeys
            self.comment("Available replacements %s" %res)

            files.append(self.fname)

            simOk = True

            if(self.runsim):
                tickTime = datetime.datetime.now()
                self.comment(f"Running  {self.fdest}")
                self.makeSpiceFile(p)
                self.comment(f"Running {p}")
                if(self.ngspice() > 0):
                    simOk = False
                nextTime = datetime.datetime.now()
                self.comment("Corner simulation time : " + str(nextTime - tickTime))
                tickTime = nextTime
            else:
                self.warning(f"Skipping  {self.fdest}")


            if(not simOk):
                self.error("Simulation failed ")
                return

            #- Run measurement if it exists
            if(os.path.exists(self.src_meas)):
                self.makeMeasFile()
                self.ngspiceMeas()

            #- If log file exists, then parse the log and create yaml file


            if(os.path.exists(self.dst_log)):
                self.parseLog()

            #- Run python post parsing if it exists
            pyscript = self.testbench + ".py"
            if(os.path.exists(pyscript)):
                pyRunLater.append(self.fname)


        endTime = datetime.datetime.now()
        self.comment("Total  simulation time : " + str(endTime - startTime))
        runfile = self.testbench + "_" + self.getShortName(self.corners) + ".run"

        with open(runfile,"w") as fo:
            for f in files:
                fo.write(f + "\n")

        #- Run python
        if(len(pyRunLater) > 0):
            sys.path.append(os.getcwd())
            tb = importlib.import_module(self.testbench)
            for perm in pyRunLater:
                self.comment(f"Running {self.testbench}.py with {perm}")
                tb.main(perm)
