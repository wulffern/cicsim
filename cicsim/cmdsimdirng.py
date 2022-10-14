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
import os
import yaml




class CmdSimDirNg(cs.CdsConfig):
    """ Create a simulation directory for ngspice
    """

    def __init__(self,library,cell):
        super().__init__(cell=cell,library=library)

    def makeDirectory(self):

        if(os.path.exists(self.cell)):
            self.cm.error(f"I refuse to override the simulation directory '{self.cell}'. You should delete it.\nIf you'r trying to simulate another library with the same cell name, don't do that. Always have unique cellnames cross libraries.")
            return False

        os.makedirs(self.cell)

        d = {
            "ngspice":{
                "cell" : self.cell,
            },
            "corner":{
                "Sch": "",
                "Lay": ""

            }
        }
        with open(self.cell + os.path.sep + "cicsim.yaml","w") as fo:
            yaml.dump(d,fo)
        return True


    def writeSpiceTestbench(self,filename,tb=False):

        stb = """*{library}/{cell}
*----------------------------------------------------------------
* Include
*----------------------------------------------------------------
#ifdef Lay
.include ../../../work/lpe/{cell}_lpe.spi
#else
.include ../../../work/xsch/{cell}.spice
#endif

*-----------------------------------------------------------------
* OPTIONS
*-----------------------------------------------------------------
#ifdef Debug
.option reltol=1e-3 srcsteps=1 ramptime=10n noopiter keepopinfo gmin=1e-12
#else
.option reltol=1e-5 srcsteps=1 ramptime=10n noopiter keepopinfo gmin=1e-15
#endif

*-----------------------------------------------------------------
* PARAMETERS
*-----------------------------------------------------------------
.param TRF = 10p

.param AVDD = {vdda}

*-----------------------------------------------------------------
* FORCE
*-----------------------------------------------------------------
VSS  VSS  0     dc 0
VDD  VDD_1V8  VSS  pwl 0 0 10n {AVDD}

*-----------------------------------------------------------------
* DUT
*-----------------------------------------------------------------
XDUT {ports} {cell}

*----------------------------------------------------------------
* MEASURES
*----------------------------------------------------------------


*----------------------------------------------------------------
* PROBE
*----------------------------------------------------------------

#ifdef Debug
.save all
#else
.probe {vports}
#endif

*----------------------------------------------------------------
* NGSPICE control
*----------------------------------------------------------------
.control
set num_threads=8
set color0=white
set color1=black
unset askquit

#ifdef Debug
tran 10p 1n 1p
*quit
#else
tran 10p 10n 1p
write
quit
#endif

.endc

.end

"""


        stb = stb.replace("{name}",filename.replace(".spi",""))
        stb = stb.replace("{cell}",self.cell)
        stb = stb.replace("{library}",self.library)

        sp = cs.SpiceParser()
        ports = sp.fastGetPortsFromFile(f"../../work/xsch/{self.cell}.spice",self.cell)
        stb = stb.replace("{ports}"," ".join(ports))

        stb = stb.replace("{vports}"," ".join(map(lambda x: "v(%s)"%x,ports)))


        with open(filename,"w") as fo:
            print(stb,file=fo)

    def run(self):
        if(self.makeDirectory()):
            os.chdir(self.cell)
            mk = """
TB=tran
VIEW=Sch
#VIEW=Lay

OPT=

netlist:
	cd ../../work && xschem -q -x -b -s -n ../design/{library}/{cell}.sch
	perl -pi -e "s/\*\*\.subckt/\.subckt/ig;s/\*\*\.ends/\.ends/ig;" ../../work/xsch/{cell}.spice


test:
	${MAKE} typical OPT="Debug"

typical:
	cicsim runng ${TB} ${OPT} ${VIEW} Gt Att Tt Vt

slow:
	cicsim runng ${TB} ${OPT} ${VIEW} Gt Ass "Th,Tl" Vl

fast:
	cicsim runng ${TB} ${OPT} ${VIEW} Gt Aff "Th,Tl" Vh

tfs:
	cicsim runng ${TB} ${OPT} ${VIEW} Gt "Att,Ass,Aff" "Tt,Th,Tl" Vt

ttffss:
	cicsim runng ${TB} ${OPT} ${VIEW} Gt "Att,Ass,Aff" "Tt" Vt

temp:
	cicsim runng ${TB} ${OPT} ${VIEW} Gt "Att" "Tt,Th,Tl" Vt

clean:
	-rm -rf output_*
	-rm -rf __pycache__
	-rm *.run
	-rm *.pdf
	-rm *.csv
"""

            mk = mk.replace("{cell}",self.cell)
            mk = mk.replace("{library}",self.library)
            with open("Makefile","w") as fo:
                fo.write(mk)
            os.system("make netlist")
            self.writeSpiceTestbench("tran.spi")
