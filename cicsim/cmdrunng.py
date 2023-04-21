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


class Simulation(cs.CdsConfig):

    def __init__(self,testbench,corner,runsim,config,index):
         #- Permutation variables

        self.runsim = runsim
        self.corner = corner
        self.index = index
        self.testbench = testbench
        self.rundir = f"output_{self.testbench}"


        self.name =  self.testbench +  "_"+ "".join(corner)
        self.oname = self.rundir + os.path.sep + self.name
        if(index > 0):
            self.oname += "_" + str(index)
            self.name += "_" + str(index)

        self.keys = "|".join(list(self.__dict__.keys()))
        self.config = config

        super().__init__()

    def run(self,ignore=False):
        res = "{cic(%s)}" % self.keys
        self.comment("Available replacements %s" %res)

        #- Run simulation, or not, depends on runsim
        simOk = self.ngspice(ignore)

        if(not simOk):
            self.error(f"Simulation {self.name} failed ")
            return

        #- Run measurement if it exists
        measOk = self.ngspiceMeas(ignore)

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
            self.makeSpiceFile(self.corner)
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
            self.warning(f"Skipping  {self.name}")

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

        with open(self.oname + ".spi","w") as fo:
            print("cicsimgen " + self.testbench,file=fo)
            print(ss,file=fo)

            with open(self.testbench + ".spi","r") as fi:
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


    def ngspiceMeas(self,ignore=False):
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

        #- Run measurement
        cmd = f"cd {self.rundir}; ngspice -b {self.name}.meas  2>&1 | tee {self.name}.logm"
        self.comment(cmd)
        os.system(cmd)

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

    def __init__(self,testbench,oformat,runsim,corners,cornername,count):
        self.testbench = testbench


        self.count = count
        self.oformat = oformat
        self.runsim = runsim
        self.corners = corners
        self.cornername = cornername
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
                c = Simulation(self.testbench,corner,self.runsim,self.config,index)
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
