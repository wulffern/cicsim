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


import cicsim as cs
import re
import os
import errno
import yaml
import shutil as sh
import sys
import importlib

class CmdRunNg(cs.CdsConfig):
    """ Run ngspice
    """

    def __init__(self,testbench,oformat,runsim,ocn,corners):
        self.testbench = testbench
        self.oformat = oformat
        self.runsim = runsim
        self.ocn = ocn
        self.corners = corners

        super().__init__()


    def ngspice(self):
        options = ""
        includes = ""
        if("ngspice" in self.config):
            if("options" in self.config["ngspice"]):
                options = self.config["ngspice"]["options"]
            else:
                options = ""

        cmd = f"ngspice {options} {includes} {self.fname} -r {self.raw} | tee {self.log}"
        
        self.comment(cmd)
        return os.system(f"cd {self.rundir}; {cmd}")

    def makeSpiceFile(self,fsource,corner,fdest):

        ss = ""
        if("corner" in self.config):
            for c in corner:
                if(c in self.config["corner"]):
                    ss += self.config["corner"][c] + "\n"
                else:
                    ss += "#define " + c.upper() + "\n"


        dirn = os.path.dirname(fdest)

        self.rundir = dirn
        self.fname = os.path.basename(fdest)
        self.fdest = fdest
        self.fsource = fsource
        os.makedirs(dirn,exist_ok=True)

        self.log = self.fname.replace(".spi",".log")
        self.raw = self.fname.replace(".spi",".raw")

        data = self.fname.replace(".spi","_data")
        self.datadir = data
        if(not os.path.exists(self.rundir + os.path.sep + data)):
            os.mkdir(self.rundir + os.path.sep + data)


        with open(fdest,"w") as fo:
            print("cicsimgen " + fsource.replace(".spi",""),file=fo)
            print(ss,file=fo)

            selfkeys = "|".join(list(self.__dict__.keys()))

            with open(fsource,"r") as fi:
                line = fi.read()

                res = "{cic(%s)}" % selfkeys

                self.comment("Available replacements %s" %res)

                m = re.search(res,line)

                if(m is not None):
                    for mg in m.groups():
                        self.comment("Replacing  {cic%s} = %s" %(mg,self.__dict__[mg]))

                        line = line.replace("{cic%s}" %mg,self.__dict__[mg])

                print(line,file=fo)

    def run(self):
        
        filename = self.testbench + ".spi"
        if(not os.path.exists(filename)):
            self.error(f"Testbench '{filename}' does not exists in this folder")
            return

        permutations = self.getPermutations(self.corners)

        pyRunLater = list()
        files = list()
        for p in permutations:
            fname = f"output_{self.testbench}" + os.path.sep + self.testbench +  "_"+ "".join(p)
            path = fname + ".spi"
            files.append(fname)

            simOk = True
            if(self.runsim):
                self.comment(f"Running  {path}")
                self.makeSpiceFile(filename,p,path)
                self.comment(f"Running {p}")
                if(self.ngspice() > 0):
                    simOk = False
            else:
                self.warning(f"Skipping  {path}")


            if(not simOk):
                self.error("Simulation failed ")
                return




            #- Run python post parsing if it exists
            pyscript = self.testbench + ".py"
            if(os.path.exists(pyscript)):
                pyRunLater.append(fname)


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
