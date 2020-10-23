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
        self.readYamlConfig(".." + os.path.sep + rcfg)
        self.readYamlConfig(rcfg)

    def readYamlConfig(self,filename):

        if(os.path.exists(filename)):
            with open(filename,"r") as fi:
                ys = yaml.load(fi,Loader=yaml.FullLoader)

                if(ys == None):
                    return

                if(self.config is None):
                    self.config = ys
                else:
                    if("spectre" in ys):
                        for k in ys["spectre"]:
                            obj = ys["spectre"][k]
                            if(type(obj) is list):
                                for l in obj:
                                    self.config["spectre"][k].append(l)
                            else:
                                self.config["spectre"][k] = obj
                    ys.pop("spectre")
                    self.config.update(ys)
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

    def run(self):

        options = ""
        includes = ""
        if("spectre" in self.config):
            if("options" in self.config["spectre"]):
                options = self.config["spectre"]["options"]
            if("includes" in self.config["spectre"]):
                for I in self.config["spectre"]["includes"]:
                    includes += " -I" + I

        cmd = f"spectre  {options} {includes}  -raw " + self.fname.replace(".scs","psf") + f" {self.fname}"
        cm = cs.Command()
        cm.comment(cmd)
        os.system(f"cd {self.rundir}; {cmd}")
        pass
