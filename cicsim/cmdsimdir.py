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




class CmdSimDir(cs.CdsConfig):
    """ Create a simulation directory
    """

    def __init__(self,library,cell,view,isTestbench=False):
        self.isTestbench = isTestbench
        super().__init__(library,cell,view)

    def dut(self,spicefile=None,subckt=None):
        sp = cs.SpiceParser()
        if(not spicefile or not subckt):
            spicefile = self.netlistname
            subckt = self.cell
        ports = sp.fastGetPortsFromFile(spicefile,subckt)
        #sw = cs.SpectreWriter()
        self.writeSpectreDutfile("dut.scs",subckt,ports)

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



    def addHeader(self,name):
        self.fo.write(f"""
//-----------------------------------------------------------------
// {name}
//-----------------------------------------------------------------
""")
        
    def writeSpectreDutfile(self,spicefile,subckt,ports):

        stf = """
// Force {name}
//vdc_{lname} ({name} 0 ) vsource type=dc dc=0
//vac_{lname} ({name} 0 ) vsource type=dc dc=0 mag=1
//vpulse_{lname} ({name} 0 ) vsource type=pulse val0=0 vall=vdda period=1/cfs rise=50p fall=50p width=1/cfs/2
//i{lname} (0 {name})  isource type=dc dc=0
//r{lname} ({name} 0) resistor r=10M
//c{lname} ({name} 0) capacitor c=10f
"""

        with open(spicefile,"w") as fo:
            self.fo = fo
            self.addHeader("DEVICE UNDER TEST")

            
            self.fo.write("xdut (" +" ".join(ports) +  f") {subckt}\n")

            for p in ports:
                if(not p):
                    continue
                s = stf.replace("{name}",p).replace("{lname}",p.lower())
                self.fo.write(s)


    def writeSpectreTestbench(self,filename,tb=False):

        stb = """

//-----------------------------------------------------------------
// OPTIONS
//-----------------------------------------------------------------

global 0

simulatorOptions options reltol=1e-6 vabstol=1e-6 save=selected \\
iabstol=1e-12 gmin=1e-15 redefinedparams=warning digits=7 cols=80 \\
pivrel=1e-3  checklimitdest=both

params info what=parameters where=rawfile

//-----------------------------------------------------------------
// PARAMETERS
//-----------------------------------------------------------------


//-----------------------------------------------------------------
// DUT
//-----------------------------------------------------------------
{top}

//-----------------------------------------------------------------
// FORCE
//-----------------------------------------------------------------


//-----------------------------------------------------------------
// ANALYSIS
//-----------------------------------------------------------------
tran tran start=0 stop=1u
"""


        stb = stb.replace("{name}",filename.replace(".scs",""))

        if(tb):
            stb = stb.replace("{top}","")
        else:
            stb = stb.replace("{top}","include \"../dut.scs\"")

        with open(filename,"w") as fo:
            print(stb,file=fo)

    def run(self):
        if(self.makeDirectory()):
            os.chdir(self.cell)
            self.netlist(top=(not self.isTestbench))
            netlistTop = "--no-top"
            if(not self.isTestbench):
                self.dut()
                netlistTop ="--top"


            self.writeSpectreTestbench("tran.scs",tb=self.isTestbench)
            with open("Makefile","w") as fo:
                fo.write("""
TB=tran
VIEW=Sch
#VIEW=Lay

netlist:
	cicsim netlist %s

typical:
	cicsim run ${TB} ${OPT} ${VIEW} Gt Mtt Rt Ct Tt Vt Dt Bt

slow:
	cicsim run ${TB} ${OPT} ${VIEW} Gt Mss Rh Ch Bf Df "Th,Tl" Vl

fast:
	cicsim run ${TB} ${OPT} ${VIEW} Gt Mff Rl Cl Bs Ds "Th,Tl" Vh

tfs:
	${MAKE} typical slow fast

""" % (netlistTop))
