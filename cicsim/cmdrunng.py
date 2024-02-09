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
import datetime
import hashlib


class Simulation(cs.CdsConfig):

    def __init__(self,testbench,corner,runsim,config,index,sha=False):
         #- Permutation variables

        self.runsim = runsim
        self.runmeas = True
        self.corner = corner
        self.index = index
        self.testbench = testbench
        self.rundir = f"output_{self.testbench}"
        self.sha = sha

        #- Store sha128 checksums for files
        self.shas = dict()
        self.oldsha  = dict()

        self.name =  self.testbench +  "_"+ "".join(corner)
        self.oname = self.rundir + os.path.sep + self.name
        if(index > 0):
            self.oname += "_" + str(index)
            self.name += "_" + str(index)

        self.keys = "|".join(list(self.__dict__.keys()))
        self.config = config

        super().__init__()

    def addSha(self,filename):

        #- Clean filename
        filename = filename.replace("\"","")
        if(" " in filename):
            arr = filename.split(" ")
            filename = arr[0]

        if(filename.startswith("/")):
            fpath = filename
        else:
            fpath = self.rundir + os.path.sep + filename


        if(os.path.exists(fpath)):
            self.shas[filename] = hashlib.sha256(open(fpath,"rb").read()).hexdigest()
        else:
            self.warning(f"Could not find referenced file {fpath}")

    def loadSha(self):
        shafile = self.oname + ".sha"
        if(os.path.exists(shafile)):
            with open(shafile) as fi:
                self.oldsha = yaml.safe_load(fi.read())

    def matchSha(self,key):
        match = True
        if(key in self.oldsha):
            if(self.shas[key] != self.oldsha[key]):
                    match =  False
        else:
            match = False
        return match

    def matchAllSha(self):
        match = True
        for f in self.shas:
            if(not self.matchSha(f)):
                match = False

        return match

    def saveSha(self):
        shafile = self.oname + ".sha"
        with open(shafile,"w") as fo:
            fo.write(yaml.dump(self.shas))

    def run(self,ignore=False):

        #- Check SHA option in config
        if("sha" in self.options):
            self.sha = self.options["sha"]


        #- Load shas
        self.loadSha()

        res = "{cic(%s)}" % self.keys
        self.comment("Available replacements %s" %res)

        #- Make spice file
        if(self.runsim):
            self.makeSpiceFile(self.corner)

        #- Maybe run sim if no input files have changed
        if(self.sha and self.matchAllSha()):
            self.comment("No spice files have changed", "yellow")
            self.runsim = False

        #- Run simulation, or not, depends on runsim
        simOk = self.ngspice(ignore)


        if(not simOk):
            self.error(f"Simulation {self.name} failed ")
            return

        self.makeMeasFile()

        #- Run measurement if it exists, check sha though
        if(self.sha and not self.runsim and self.matchSha(self.name + ".meas")):
            self.comment("No meas files have changed", "yellow")
            self.runmeas = False
        measOk = self.ngspiceMeas(ignore)


        self.saveSha()

        if(simOk and measOk):
            self.parseLog()
            return True
        else:
            return False




    def removeFile(self,filename):
        os.remove(filename) if os.path.exists(filename) else 0

    def ngspice(self,ignore=True):
        simOk = True

        if(self.runsim):
            tickTime = datetime.datetime.now()

            self.comment(f"Running {self.name}")

            options = ""
            includes = ""
            if("ngspice" in self.config):
                if("options" in self.config["ngspice"]):
                    options = self.config["ngspice"]["options"]
                else:
                    options = ""

            cmd = f"cd {self.rundir}; ngspice {options} {includes} {self.name}.spi -r {self.name}.raw 2>&1 |tee {self.name}.log"

            self.comment(cmd)

            rawcmd = f"cd {self.rundir} && rm -f {self.name}*.raw"
            os.system(rawcmd)

            self.removeFile(self.oname + ".yaml")

            # Run NGSPICE
            try:
                self.err = os.system(cmd)
            except Exception as e:
                print(e)

            #- Exit directly if Ctrl-C is pressed
            if(self.err == 2):
                exit()

            if(self.err > 0):
                simOk = False

            nextTime = datetime.datetime.now()
            self.comment("Corner simulation time : " + str(nextTime - tickTime))
            tickTime = nextTime
        else:
            self.warning(f"Skipping simulation of {self.name}.spi")

         #- Check logfile. ngspice does not always exit cleanly
        errors = list()
        with open(self.oname + ".log") as fi:
            for l in fi:
                if(re.search("(Error|ERROR):",l)):
                    #- Skip reporting error if it's only the graphics
                    if(not re.search("no graphics interface",l)):
                        errors.append(l)

        if(len(errors) > 0):
            simOk = False
            for line in errors:
                print(line.strip())

        return simOk if not ignore else True

    def makeSimDir(self):

        if("useTmpDir" in self.options and self.options["useTmpDir"]):
            path = "/tmp/cicsim/" + os.environ["USER"] + "/" + self.library + "/" + self.cell + "/" + self.rundir
            os.makedirs(path,exist_ok=True)
            if(not os.path.exists(self.rundir)):
                os.system(f"ln -s {path} {self.rundir} ")
            pass
        else:
            os.makedirs(self.rundir,exist_ok=True)

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

        self.makeSimDir()


        with open(self.oname + ".spi","w") as fo:

            buffer = ""

            buffer += "cicsimgen " + self.testbench
            buffer += ss

            with open(self.testbench + ".spi","r") as fi:
                #- Check for #defines
                state = 0

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

                sfile = self.replaceLine(buffer)

                if("useTmpDir" in self.options and self.options["useTmpDir"]):
                    sfile = re.sub("\.include\s+\.\./",f".include {os.getcwd()}/",sfile)
                    sfile = re.sub("\.include\s+\"\.\./",f".include \"{os.getcwd()}/",sfile)
                    sfile = re.sub("\.lib\s+\"\.\./",f".lib \"{os.getcwd()}/",sfile)
                    sfile = re.sub("\.lib\s+\.\./",f".lib {os.getcwd()}/",sfile)

                #- Store shas for any includes
                incfiles = re.findall(r"\.include\s+(.*)",sfile,flags=re.MULTILINE)

                for f in incfiles:
                    self.addSha(f)

                libfiles = re.findall(r"\.lib\s+(.*)",sfile,flags=re.MULTILINE)


                for f in libfiles:
                    self.addSha(f)

                print(sfile,file=fo)


        #- Store the Sha for the testbench
        self.addSha(self.name + ".spi")

    def makeMeasFile(self,ignore=False):
        meas_src = self.testbench + ".meas"
        meas_dst = self.oname + ".meas"

        #- Check for a meas file, ignore measurement sim if it's not there
        if(not os.path.exists(meas_src)):
            return True

        #- Create the measurement file
        with open(meas_src) as fi:
            with open(meas_dst,"w") as fo:
                for line in fi:
                    line = self.replaceLine(line)
                    fo.write(line)

        #- Store the sha for the measurement file
        self.addSha(self.name + ".meas")

    def ngspiceMeas(self,ignore=False):

        #- Run measurement
        if(self.runmeas):
            cmd = f"cd {self.rundir}; ngspice -b {self.name}.meas  2>&1 | tee {self.name}.logm"
            self.comment(cmd)
            os.system(cmd)
        else:
            self.comment(f"Skipping measurment run of {self.name}.meas","yellow")

        #- Check meas logfile. ngspice does not always exit cleanly
        errors = list()
        with open(self.oname + ".logm") as fi:
            for l in fi:
                if(re.search("Error:",l) or re.search("failed",l)):
                    errors.append(l.strip())
#                if(re.search("^([^\s]+)\s*=\s*([^\s]+)\s",l)):
#                    self.comment(l.strip(),"cyan")

        if(len(errors) > 0):
            for line in errors:
                self.comment(line,"red")
            return False if not ignore else True
        else:
            return True

    def parseLog(self):
        analysis = False

        #- Parse main log file for measurements
        data = dict()
        with open(self.oname + ".log") as fi:
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
        measlog = self.oname + ".logm"
        if(os.path.exists(measlog)):
            analysis = False
            with open(measlog) as fi:
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

        yamlfile = self.oname + ".yaml"
        with open(yamlfile,"w") as fo:
            self.comment(f"Writing {yamlfile}")
            yaml.dump(data,fo)


    def replaceLine(self,line):
        res = "{cic(%s)}" % self.keys
        m = re.search(res,line)

        if(m is not None):
            for mg in m.groups():
                self.comment("Replacing  {cic%s} = %s" %(mg,self.__dict__[mg]))

                line = line.replace("{cic%s}" %mg,str(self.__dict__[mg]))
        return line

class CmdRunNg(cs.CdsConfig):
    """ Run ngspice
    """

    def __init__(self,testbench,oformat,runsim,corners,cornername,count,sha):
        self.testbench = testbench


        self.count = count
        self.oformat = oformat
        self.runsim = runsim
        self.corners = corners
        self.cornername = cornername
        self.sha = sha
        super().__init__()

        if("_" in self.testbench ):
            self.error("Testbench name cannot contain '_'")
            exit(1)



    def run(self,ignore=False):
        startTime = datetime.datetime.now()
        
        self.filename = self.testbench + ".spi"
        if(not os.path.exists(self.filename)):
            self.error(f"Testbench {filename} does not exists in this folder")
            return

        permutations = self.getPermutations(self.corners)
        pyRunLater = list()
        files = list()
        simOk = True
        for corner in permutations:
            for index in range(0,self.count):
                if(not simOk):
                    self.error(f"Previous simulation failed, skipping {index}")
                    continue

                #- Run a simulation for a corner
                c = Simulation(self.testbench,corner,self.runsim,self.config,index,self.sha)
                if(not c.run(ignore)):
                    simOk = False
                    continue


                files.append(c.oname)


                #- Run python post parsing if py file exist and simulation is OK
                pyscript = c.testbench + ".py"
                if(simOk and os.path.exists(pyscript)):
                    pyRunLater.append(c.oname)


        endTime = datetime.datetime.now()
        self.comment("Total simulation time : " + str(endTime - startTime))

        #- Make runfile
        if(self.cornername):
            view = "_"
            runfile = self.testbench + "_" + self.cornername + ".run"
        else:
            runfile = self.testbench + "_" + self.getShortName(self.corners) + ".run"

        with open(runfile,"w") as fo:
            for f in files:
                fo.write(f + "\n")

        if(simOk):
            #- Run python
            if(len(pyRunLater) > 0):
                sys.path.append(os.getcwd())
                tb = importlib.import_module(self.testbench)
                for perm in pyRunLater:
                    self.comment(f"Running {self.testbench}.py with {perm}")
                    tb.main(perm)
            #- Extract results
            r = cs.CmdResults(runfile)
            r.run()
        else:
            self.warning("Skipping post processing, one simulation failed")
