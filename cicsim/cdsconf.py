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

class CdsConfig(cs.Command):

    def __init__(self,library=None,cell=None,view=None):
        self.config = None
        self.cm = cs.Command()
        pparent = ".." + os.path.sep + ".." + os.path.sep + rcfg
        if(os.path.exists(pparent)):
            self.readYamlConfig(pparent)
        parent = ".." + os.path.sep + rcfg
        if(os.path.exists(parent)):
            self.readYamlConfig(".." + os.path.sep + rcfg)
        self.readYamlConfig(rcfg)

        if("cadence" in self.config):
            self.cadence =  self.config["cadence"]
        else:
            self.cadence = {}


        if(library):
            self.cadence["library"] = library
        if(cell):
            self.cadence["cell"] = cell
        if(view):
            self.cadence["view"] = view

        super().__init__()

    @property
    def library(self):
        return self.getCadence("library")
    @property
    def cell(self):
        return self.getCadence("cell")
    @property
    def view(self):
        return self.getCadence("view")

    @property
    def netlistname(self):
        return self.cell + "_" + self.view + ".scs"
    @property
    def cdsdir(self):
        return os.path.expandvars(self.getCadence("cds_dir"))


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
                if(key in dest):
                    if(isinstance(val,str)):
                        dest[key] += " "+ val
                else:
                    dest[key] = val
        return dest

        
    def readYamlConfig(self,filename):

        if(os.path.exists(filename)):
            with open(filename,"r") as fi:
                #ys = yaml.load(fi,Loader=yaml.FullLoader)
                ys = yaml.safe_load(fi)

                if(ys == None):
                    return

                if(self.config is None):
                    self.config = ys
                else:
                    self.config = self.merge(self.config,ys)
                    
        else:
            self.cm.error(f"Could not find config file '{filename}'")

    def makeDirectory(self):
        
        if(os.path.exists(self.cell)):
            self.cm.error(f"I refuse to override the simulation directory '{self.cell}'. You should delete it.\nIf you'r trying to simulate another library with the same cell name, don't do that. Always have unique cellnames cross libraries.")
            return False

        os.makedirs(self.cell)

        d = {
            "cadence":{
                "library": self.library,
                "cell" : self.cell,
                "view" : self.view,
            },
            "corner":{
                "Sch": f"""include "../{self.cell}_{self.view}.scs"\n"""

            }
        }
        with open(self.cell + os.path.sep + "cicsim.yaml","w") as fo:
            yaml.dump(d,fo)
        return True





    def getCadence(self,key):
        if(key in self.cadence):
            return self.cadence[key]
        else:
            self.cm.error(f"Argument cadence->{key} is not specified, specify either on command line or in config file")


    def getShortName(self,corner):

        sname = ""
        for c in corner:
            c = c.replace(",","")
            sname += c
        return sname

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

    def getShortName(self,corner):
        ss = ""
        for c in corner:
            ss += c.replace(",","")
        return ss

        
    

    def netlist(self,top=True):
        
        curdir = os.getcwd()

        if(self.library is None or self.cell is None or self.view is None or self.cdsdir is None):
            return

        topsubckt = ""
        if(top):
            topsubckt = "envOption( 'setTopLevelAsSubckt  t )"

        scr = f"""
envSetVal("asimenv.startup" "projectDir" `string "{curdir}")
simulator('spectre)
design("{self.library}" "{self.cell}" "{self.view}")
{topsubckt}
createNetlist(?recreateAll t ?display nil)
exit()
        """

        with open(self.cdsdir + os.path.sep + "netlist.ocean","w") as fo:
            fo.write(scr)


        os.system(f"cd {self.cdsdir};ocean  < netlist.ocean")
        fname = self.netlistname

        if(not os.path.exists(fname)):
            os.system(f"ln -s {self.cell}/spectre/{self.view}/netlist/netlist {fname}")
