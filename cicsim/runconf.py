######################################################################
##        Copyright (c) 2020 Carsten Wulff Software, Norway
## ###################################################################
## Created       : wulff at 2020-10-23
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

import yaml
import os
import cicsim as cs

rcfg = "cicsim.yaml"

class RunConfig:

    def __init__(self):
        self.config = None
        self.cm = cs.Command()
        self.readYamlConfig(".." + os.path.sep + rcfg)
        self.readYamlConfig(rcfg)
        if("cadence" in self.config):
            self.cadence =  self.config["cadence"]
        else:
            self.cadence = {}

    def merge(self,dest,source):
        for key,val in source.items():
            if(isinstance(val,dict)):
                if(key in dest):
                    dest[key] = self.merge(dest[key],val)
                else:
                    dest[key] = val
            elif(isinstance(val,list)):
                if(key in dest):
                    for v in val:
                        dest[key].append(v)
                else:
                    dest[key] = val
            else:
                dest[key] = val
        return dest

        

    def readYamlConfig(self,filename):

        if(os.path.exists(filename)):
            with open(filename,"r") as fi:
                ys = yaml.load(fi,Loader=yaml.FullLoader)

                if(ys == None):
                    return

                if(self.config is None):
                    self.config = ys
                else:
                    self.config = self.merge(self.config,ys)
                    
        else:
            self.cm.Error(f"Could not find config file '{filename}'")
                    
    def makeSpectreFile(self,fsource,corner,fdest):

        ss = ""
        if("corner" in self.config):
            for c in corner:
                if(c in self.config["corner"]):
                    ss += self.config["corner"][c]

        dirn = os.path.dirname(fdest)

        self.rundir = dirn
        self.fname = os.path.basename(fdest)
        self.fdest = fdest
        self.fsource = fsource
        os.makedirs(dirn,exist_ok=True)

        with open(fdest,"w") as fo:
            print("cicsimgen" + fsource.replace(".scs",""),file=fo)
            print(ss,file=fo)
            with open(fsource,"r") as fi:
                print(fi.read(),file=fo)


    def getCadenceWithName(self,val,name):
        if(val is None and name in self.cadence):
            val = self.cadence[name]
        elif(val):
            pass
        else:
            self.cm.error(f"Argument cadence->{name} is not specified, specify either on command line or in config file")
        return val


    def getCadence(self,key):
        if(key in self.cadence):
            return self.cadence[key]
        else:
            self.cm.error(f"Argument cadence->{key} is not specified, specify either on command line or in config file")


    def getPermutations(self,corner):
        data = []
        single = []
        multiple = []
        for c in corner:
            if("," in c):
                multiple.append(c.split(","))
            else:
                single.append(c)

        data = []

        data.append(" ".join(single))
        for mc in multiple:
            da = []
            for m in mc:
                for d in data:
                    da.append(d + " " + m )
            data = da

        corner = []
        for d in data:
            corner.append(d.split(" "))
        return corner





    def netlist(self,library,cell,view,top=True):
        library = self.getCadenceWithName(library,"library")
        cell = self.getCadenceWithName(cell,"cell")
        view = self.getCadenceWithName(view,"view")
        cds_dir = os.path.expandvars(self.getCadence("cds_dir"))
        curdir = os.getcwd()

        if(library is None or cell is None or view is None or cds_dir is None):
            return

        tosubckt = ""
        if(top):
            topsubckt = "envOption( 'setTopLevelAsSubckt  t )"

        scr = f"""
envSetVal("asimenv.startup" "projectDir" `string "{curdir}")
simulator('spectre)
design("{library}" "{cell}" "{view}")
{topsubckt}
createNetlist(?recreateAll t ?display nil)
exit()
        """



        with open(cds_dir + os.path.sep + "netlist.ocean","w") as fo:
            fo.write(scr)


        os.system(f"cd {cds_dir};ocean -nograph < netlist.ocean")
        fname = f"{cell}_{view}.scs"
        if(not os.path.exists(fname)):
            os.system(f"ln -s {cell}/spectre/{view}/netlist/netlist {fname}")


    def run(self):

        options = ""
        includes = ""
        if("spectre" in self.config):
            if("options" in self.config["spectre"]):
                options = self.config["spectre"]["options"]
            if("includes" in self.config["spectre"]):
                for I in self.config["spectre"]["includes"]:
                    includes += " -I" + I

        cmd = f"spectre  {options} {includes}  -raw " + self.fname.replace(".scs",".psf") + f" {self.fname}"
        cm = cs.Command()
        cm.comment(cmd)
        os.system(f"cd {self.rundir}; {cmd}")
        pass
