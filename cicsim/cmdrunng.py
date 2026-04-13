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
import yaml
import sys
import importlib
import datetime
import hashlib
import inspect
import subprocess
import numpy as np
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("cicsim")

class Simulation(cs.CdsConfig):

    def __init__(self,testbench,corner,runsim,config,index,sha=None,progress=False):
         #- Permutation variables
        self.runsim = runsim
        self.runmeas = True
        self.corner = corner
        self.index = index
        self.testbench = testbench
        self.pyscript = testbench + ".py"
        self.rundir = f"output_{self.testbench}"
        self.sha = sha
        self.progress = progress

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
        self.replace = None
        self.replace_re = None

        super().__init__()

    def loadReplace(self,replace):
        if(replace is None):
            return
        self.replace = replace
        self.replace_re = "{(%s)}" %("|".join(self.replace.keys()))

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
            with open(fpath,"rb") as f:
                self.shas[filename] = hashlib.sha256(f.read()).hexdigest()
        else:
            if not self.progress:
                logger.warning(f"Could not find referenced file {fpath}")

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

        #- Check SHA option in config if sha is not set on command line
        if(self.sha is None and "sha" in self.options):
            self.sha = self.options["sha"]


        #- Load shas
        self.loadSha()

        res = "{cic(%s)}" % self.keys
        logger.info("Available replacements %s" %res)

        #- Make spice file
        if(self.runsim):
            self.makeSpiceFile(self.corner)

        #- Maybe run sim if no input files have changed
        if(self.sha and self.matchAllSha()):
            if not self.progress:
                logger.warning("No spice files have changed")
            self.runsim = False

        #- Run simulation, or not, depends on runsim
        simOk = self.ngspice(ignore)

        if(not simOk):
            logger.error(f"Simulation {self.name} failed")
            return

        self.makeMeasFile()

        #- Run measurement if it exists, check sha though
        if(self.sha and not self.runsim and self.matchSha(self.name + ".meas")):
            if not self.progress:
                logger.warning("No meas files have changed")
            self.runmeas = False
        measOk = self.ngspiceMeas(ignore)


        #- Don't save sha if we have not run a simulation
        if(self.sha):
            if(self.runsim):
                self.saveSha()
            else:
                if not self.progress:
                    logger.warning("Not storing sha file, no simulation run")

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

            logger.info(f"Running {self.name}")

            options = ""
            includes = ""
            if("ngspice" in self.config):
                if("options" in self.config["ngspice"]):
                    options = self.config["ngspice"]["options"]
                else:
                    options = ""


            #- Remove old simulation results
            rawcmd = f"cd {self.rundir} && rm -f {self.name}*.raw"
            subprocess.run(rawcmd, shell=True)
            self.removeFile(self.oname + ".yaml")

            # Run NGSPICE
            if self.progress:
                cmd = f"cd {self.rundir}; ngspice {options} {includes} {self.name}.spi -r {self.name}.raw > {self.name}.log 2>&1"
            else:
                cmd = f"cd {self.rundir}; ngspice {options} {includes} {self.name}.spi -r {self.name}.raw 2>&1 |tee {self.name}.log"
            logger.debug("Cmd: " + cmd)
            try:
                result = subprocess.run(cmd, shell=True)
                self.err = result.returncode
            except KeyboardInterrupt:
                sys.exit(2)
            except Exception as e:
                logger.error(str(e))

            if(self.err > 0):
                simOk = False

            nextTime = datetime.datetime.now()
            logger.info("Corner simulation time: " + str(nextTime - tickTime))
            tickTime = nextTime
        else:
            if not self.progress:
                logger.warning(f"Skipping simulation of {self.name}.spi")

         #- Check logfile. ngspice does not always exit cleanly
        errors = list()
        logfile = self.oname + ".log"
        if(os.path.exists(logfile)):
            with open(logfile) as fi:
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
                os.symlink(path, self.rundir)
            pass
        else:
            os.makedirs(self.rundir,exist_ok=True)

    def parseIfdef(self,fi):
        buffer = ""
        #- Check for #defines
        state = 0
        buffif = ""
        buffelse = ""
        dkey = ""
        for l in fi:
            if(l.startswith("#ifdef")):
                d = re.split(r"\s+",l)
                dkey = d[1]
                state = 1
                continue
                #l = "*" + l
            if(l.startswith("#else")):
                state = 2
                #l = "*" + l
                continue
            if(l.startswith("#endif")):
                if(dkey in self.corner):
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
        return buffer


            
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
            buffer += "*cicsimgen " + self.testbench + "\n\n"

            #- Add seed so runs become reproducible
            buffer += f".option SEED={self.index+1}\n"

            buffer += ss

            with open(self.testbench + ".spi","r") as fi:

                buffer += self.parseIfdef(fi)
                sfile = self.replaceLine(buffer)

                if("useTmpDir" in self.options and self.options["useTmpDir"]):
                    sfile = re.sub(r"\.include\s+\.\./",f".include {os.getcwd()}/",sfile)
                    sfile = re.sub(r"\.include\s+\"\.\./",f".include \"{os.getcwd()}/",sfile)
                    sfile = re.sub(r"\.lib\s+\"\.\./",f".lib \"{os.getcwd()}/",sfile)
                    sfile = re.sub(r"\.lib\s+\.\./",f".lib {os.getcwd()}/",sfile)

                #- Store shas for any includes
                incfiles = re.findall(r"^\s*\.include\s+(.*)",sfile,flags=re.MULTILINE)
                for f in incfiles:
                    self.addSha(f)

                #- Add non-spice sha's
                incfiles = re.findall(r"^\s*\*#include\s+(.*)",sfile,flags=re.MULTILINE)
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
                buffer = self.parseIfdef(fi)
                buffer = self.replaceLine(buffer)
                fo.write(buffer)

        #- Store the sha for the measurement file
        self.addSha(self.name + ".meas")

    def ngspiceMeas(self,ignore=False):

        #- Run measurement
        if(self.runmeas):
            if self.progress:
                cmd = f"cd {self.rundir}; ngspice -b {self.name}.meas > {self.name}.logm 2>&1"
            else:
                cmd = f"cd {self.rundir}; ngspice -b {self.name}.meas  2>&1 | tee {self.name}.logm"
            logger.debug("Cmd: " + cmd)
            subprocess.run(cmd, shell=True)
        else:
            if not self.progress:
                logger.warning(f"Skipping measurement run of {self.name}.meas")

        #- Check meas logfile. ngspice does not always exit cleanly
        errors = list()
        measlogfile = self.oname + ".logm"
        if not os.path.exists(measlogfile):
            return True
        with open(measlogfile) as fi:
            for l in fi:
                if(re.search("Error:",l) or re.search("failed",l)):

                    #- Skip the "No netlist" message in ngspice-45 and on
                    if(re.search("incomplete or empty netlist",l)):
                        continue
                    errors.append(l.strip())

        if(len(errors) > 0):
            for line in errors:
                logger.error(line)
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
                    m = re.search(r"^([^\s]+)\s*=\s*([^\s]+)\s",l)
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
            prepareTable = False
            table = False
            table_data = list()
            table_header = None
            with open(measlog) as fi:
                for l in fi:


                    if(analysis):
                        #print(table,prepareTable,l)
                            # Parse tables
                        if(not prepareTable and re.search("^---------------------------------",l)):
                            prepareTable = True
                            continue
                        #print(l,end="")
                        #print(re.search(r"^\d",l))
                        if(table and not prepareTable and (not re.search(r"^\d",l) )):
                            table = False

                        if(prepareTable and re.search("^Index",l)):
                            arr = re.split(r"\s+",l)
                            table_header = arr[1:]
                            table = True
                            continue

                        if(table and not prepareTable):
                            arr = re.split(r"\s+",l)

                            for k,v in zip(table_header,arr[1:]):
                                if(v== ""):
                                    continue
                                if(k not in data):
                                    data[k] = list()
                                data[k].append(float(v))


                        if(prepareTable):
                            prepareTable = False

                    #- Find key=val pairs
                    if(analysis and re.search("=",l)):
                        m = re.search(r"^([^\s]+)\s*=\s*([^\s]+)\s",l)
                        if(m):
                            key = m.groups()[0].strip()
                            val = m.groups()[1].strip()
                            data[key] = float(val)
                    if(re.search(r"^\s*MEAS_START",l)):
                        analysis = True
                    if(re.search(r"^\s*MEAS_END",l)):
                        analysis = False

        yamlfile = self.oname + ".yaml"
        with open(yamlfile,"w") as fo:
            logger.info(f"Writing {yamlfile}")
            yaml.dump(data,fo)


    def replaceLine(self,line):

        #- Find and replace {} stuff
        if(self.replace):
            m = re.findall(self.replace_re,line,flags=re.MULTILINE)
            if(len(m) > 0):
                for mg in m:
                    logger.info("Replacing {%s} = %s" %(mg,self.replace[mg]))
                    line = line.replace("{%s}" %mg,str(self.replace[mg]))

        #- Find and replace {cic.*} stuff
        res = "{cic(%s)}" % self.keys
        m = re.findall(res,line,flags=re.MULTILINE)

        if(len(m) > 0):
            for mg in m:
                logger.info("Replacing {cic%s} = %s" %(mg,self.__dict__[mg]))
                line = line.replace("{cic%s}" %mg,str(self.__dict__[mg]))

        #- Eval expressions
        m = re.findall(r"\s+\[([^\]]+)\]",line)
        for mg in m:
            try:
                logger.info("Evaluating %s"%mg)
                eresult = str(self.safe_eval(mg))
                logger.info("Replacing  [%s] = %s" %(mg,eresult))
                line = line.replace("[%s]" %mg,eresult)
            except Exception as e:
                logger.warning(f"Could not eval [{mg}]: {e}")
                pass

        return line

class CmdRunNg(cs.CdsConfig):
    """ Run ngspice
    """

    def __init__(self,testbench,runsim,corners,cornername,count,sha,threads=1,progress=False):
        self.testbench = testbench
        self.count = count
        self.runsim = runsim
        self.corners = corners
        self.cornername = cornername
        self.sha = sha
        self.threads = max(1, threads)
        self.progress = progress
        self.replace = None

        super().__init__()

        if("_" in self.testbench ):
            logger.error("Testbench name cannot contain '_'")
            exit(1)

    def loadReplacements(self,freplace):

        if(freplace is None):
            return

        if(not os.path.exists(freplace)):
            raise(Exception(f"Could not find replacement file {freplace}"))

        with open(freplace) as fi:
            obj = yaml.safe_load(fi)
        self.replace = obj


    def run(self,ignore=False):
        startTime = datetime.datetime.now()

        self.filename = self.testbench + ".spi"

        if(not os.path.exists(self.filename)):
            logger.error(f"Testbench {self.testbench}.spi does not exist in this folder")
            return

        permutations = self.getPermutations(self.corners)

        # Build ordered list of (corner, index) jobs
        jobs = [(corner, index) for corner in permutations for index in range(self.count)]

        def run_one(job):
            corner, index = job
            c = Simulation(self.testbench, corner, self.runsim, self.config, index, self.sha,
                           progress=self.progress)
            c.loadReplace(self.replace)
            ok = c.run(ignore)
            return c, bool(ok)

        if self.progress:
            from tqdm import tqdm
            from cicsim.command import suppress_console_logging
            with suppress_console_logging():
                if self.threads > 1:
                    with ThreadPoolExecutor(max_workers=self.threads) as executor:
                        results = list(tqdm(executor.map(run_one, jobs),
                                           total=len(jobs), desc=self.testbench, unit="sim"))
                else:
                    results = list(tqdm((run_one(job) for job in jobs),
                                       total=len(jobs), desc=self.testbench, unit="sim"))
        elif self.threads > 1:
            logger.info(f"Running {len(jobs)} simulation(s) with {self.threads} threads")
            with ThreadPoolExecutor(max_workers=self.threads) as executor:
                results = list(executor.map(run_one, jobs))
        else:
            results = [run_one(job) for job in jobs]

        pyRunLater = list()
        files = list()
        simOk = True
        failed_names = []

        for c, ok in results:
            if not ok:
                simOk = False
                failed_names.append(c.name)
                if not self.progress:
                    logger.error(f"Simulation {c.name} failed")
            else:
                files.append(c.oname)
                if os.path.exists(c.pyscript):
                    pyRunLater.append(c)

        endTime = datetime.datetime.now()
        elapsed = str(endTime - startTime)

        if self.progress:
            passed = len(results) - len(failed_names)
            print(f"Done: {passed}/{len(results)} passed  [{elapsed}]")
            for name in failed_names:
                print(f"  FAILED: {name}")
        else:
            logger.info("Total simulation time: " + elapsed)

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
                tb = importlib.import_module(c.testbench)
                for c in pyRunLater:
                    logger.info(f"Running {c.testbench}.py with {c.oname}")
                    if(len(inspect.signature(tb.main).parameters) > 1):
                        tb.main(c.oname,c.corner)
                    else:
                        tb.main(c.oname)
            #- Extract results
            r = cs.CmdResults(runfile, progress=self.progress)
            r.run()
        else:
            logger.warning("Skipping post processing, one simulation failed")
