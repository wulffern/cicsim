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


import logging
import cicsim as cs
import re
import os
import subprocess
import yaml
import sys
import importlib

logger = logging.getLogger("cicsim")

class CmdRun(cs.CdsConfig):
    """ Create a simulation directory
    """

    def __init__(self,testbench,oformat,runsim,ocn,corners):
        self.testbench = testbench
        self.oformat = oformat
        self.runsim = runsim
        self.ocn = ocn
        self.corners = corners

        self.runObjFile = """
HEADER
"PSFversion" "1.00"
"Run Generator" "drlRun rev. 1.0"
TYPE
"runObject" STRUCT(
"logName" ARRAY( * ) STRING *
"parent" STRING *
"sweepVariable" ARRAY( * ) STRING *
) PROP( "key" "runObject" )
VALUE
"Run1" "runObject" (
(
"logFile"
"artistLogFile"
"matlabLogFile"
)
""
()
)
END
        """

        super().__init__()


    def spectre(self):
        options = ""
        includes = ""
        if("spectre" in self.config):
            if("options" in self.config["spectre"]):
                options = self.config["spectre"]["options"]
            if("includes" in self.config["spectre"]):
                for I in self.config["spectre"]["includes"]:
                    includes += " -I" + I

        psf = self.fname.replace(".scs",".psf")
        psf = self.rundir + os.path.sep +psf
        if(not os.path.exists(psf)):
            os.mkdir(psf)

        with open(psf + os.path.sep + "runObjFile","w") as fo:
            fo.write(self.runObjFile)


        cmd = f"spectre  {options} {includes}  -E -raw " + self.fname.replace(".scs",".psf") + f" {self.fname}"
        
        logger.debug(cmd)
        return subprocess.run(cmd, shell=True, cwd=self.rundir).returncode

    def makeSpectreFile(self,fsource,corner,fdest):

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

        with open(fdest,"w") as fo:
            print("cicsimgen" + fsource.replace(".scs",""),file=fo)
            print("parameters tbname=\"" + os.path.basename(fdest).replace(".scs","") + "\" ",file=fo)
            print(ss,file=fo)
            with open(fsource,"r") as fi:
                print(fi.read(),file=fo)

    def run(self):
        
        filename = self.testbench + ".scs"
        if(not os.path.exists(filename)):
            logger.error(f"Testbench '{filename}' does not exist in this folder")
            return

        permutations = self.getPermutations(self.corners)

        oceanRunLater = list()
        pyRunLater = list()

        for p in permutations:
            fname = f"output_{self.testbench}" + os.path.sep + self.testbench +  "_"+ "".join(p)
            path = fname + ".scs"
            logger.info(f"Running  {path}")
            simOk = True
            if(self.runsim):
                self.makeSpectreFile(filename,p,path)
                logger.info(f"Running {p}")
                if(self.spectre() > 0):
                    simOk = False

            if(not simOk):
                logger.error("Simulation failed")
                continue



            #- Run ocean post parsing if it exists
            ocnscript = self.testbench + ".ocn"
            if(os.path.exists(ocnscript) and self.ocn):
                ocnfo = fname + ".ocn"
                resultsDir = os.getcwd() + os.path.sep+ fname + ".psf"
                resultsFileName = os.getcwd() + os.path.sep+ fname
                resultsFile = resultsFileName + ".yaml"


                with open(ocnscript,"r") as fi:
                    buffer = ""
                    yamlprint = list()
                    for line in fi:

                        line = re.sub(r"\?result",f" ?resultsDir cicResultsDir ?result",line)

                        m = re.search(r";\s*yamlprint\s(.*)$",line)
                        if(m):
                            ll = re.split(r"\s*,\s*",m.group(1))
                            for l in ll:
                                yamlprint.append(l)
                        buffer += line

                    if(len(yamlprint) > 0):
                        buffer += "fo = outfile(cicResultsFile)\n"
                        yamlprint.sort()
                        for yvar in yamlprint:
                            buffer += f"ocnPrint(?output fo ?numberNotation \"scientific\"  ?numSpaces 0 \"{yvar}: \" {yvar})\n"
                        buffer += "close(fo)\n"
                    
                    buffer = f"cicResultsDir = \"{resultsDir}\"\ncicResultsFile = \"{resultsFile}\"\ncicResultsFileName = \"{resultsFileName}\"\n" + buffer
                with open(ocnfo,"w") as fo:
                    fo.write(buffer)

                oceanRunLater.append(ocnfo)

            #- Run python post parsing if it exists
            pyscript = self.testbench + ".py"
            if(os.path.exists(pyscript)):
                pyRunLater.append(fname)

        #- Run oceanscripts



        if(len(oceanRunLater) == 1 and self.ocn):
            ocnfo = oceanRunLater[0]
            logger.info(f"Running ocean {ocnfo}")
            subprocess.run(f"ocean -nograph -replay {ocnfo} -log {ocnfo}.log", shell=True)
        elif(len(oceanRunLater) > 1 and self.ocn):
            buff = ""
            for focn in oceanRunLater:
                buff += f"load(\"{focn}\")\n"
            focean_all = f"output_{self.testbench}" + os.path.sep + self.testbench + "_" + self.getShortName(self.corners) + ".ocn"

            with open(focean_all,"w") as fo:
                fo.write(buff)
            logger.info(f"Running ocean {focean_all}")
            subprocess.run(f"ocean -nograph -replay {focean_all} -log {focean_all}.log", shell=True)


        #- Run python
        if(len(pyRunLater) > 0):
            sys.path.append(os.getcwd())
            tb = importlib.import_module(self.testbench)
            for perm in pyRunLater:
                logger.info(f"Running {self.testbench}.py with {perm}")
                tb.main(perm)
