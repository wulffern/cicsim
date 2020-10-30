######################################################################
##        Copyright (c) 2020 Carsten Wulff Software, Norway
## ###################################################################
## Created       : wulff at 2020-10-16
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

import os
import re

class SpectreWriter:

    def __init__(self,simconf=None):
        self.simconf = simconf
        self.simdir = None
        self.simfile = None

    def run(self):
        os.system(f"""cd {self.simdir};spectre {self.simfile}  +escchars +log spectre.out -raw psf -format psfascii""")

    def write(self):

        with open(self.simconf.filename,"w") as fo:
            self.fo = fo
            
            self.addHeader("DEVICE UNDER TEST")

            self.simconf.writeSubckt(self)

            self.simconf.writePorts(self)

    def addParam(self,key,val):
        self.fo.write(f"parameters {key}={val}\n")


    def addInclude(self,spicefile):
        self.fo.write(f"include \"{spicefile}\"\n")


    def addComment(self,ss):
        self.fo.write(f"// {ss}\n")

    def addHeader(self,name):
        self.fo.write(f"""
//-----------------------------------------------------------------
// {name}
//-----------------------------------------------------------------
""")

    def addLine(self):
        self.fo.write("\n")

    def addForceComment(self,condition,ss):

        if(condition):
            self.fo.write( ss)
        else:
            self.fo.write("//" +ss)

        
    def addForce(self,ftype,name,val):
        self.addForceComment(ftype == "vdc",f"v{name.lower()} ({name} 0) vsource type=dc dc={val} \n")
        self.addForceComment(ftype == "idc",f"i{name.lower()} (0 {name}) isource type=dc dc={val} \n")
        self.addForceComment(ftype == "resistance",f"r{name.lower()} ({name} 0) resistor r={val} \n")
        self.addForceComment(ftype == "capacitance",f"c{name.lower()} ({name} 0) capacitor c={val} \n")

        
    def addSubckt(self,subckt,nodes):
        self.fo.write("xdut (" +" ".join(nodes) +  f") {subckt}\n")

    def writeSpectreDutfile(self,spicefile,subckt,ports):

        stf = spectreForceTemplate

        with open(spicefile,"w") as fo:
            self.fo = fo
            self.addHeader("DEVICE UNDER TEST")

            self.addSubckt(subckt,ports)

            for p in ports:
                if(not p):
                    continue
                s = stf.replace("{name}",p).replace("{lname}",p.lower())
                self.fo.write(s)
            

def writeSpectreTestbench(filename,tb=False):

        stb = spectreTbTemplate


        stb = stb.replace("{name}",filename.replace(".scs",""))

        if(tb):
            stb = stb.replace("{top}","")
        else:
            stb = stb.replace("{top}","include \"../dut.scs\"")

        with open(filename,"w") as fo:
            print(stb,file=fo)


spectreForceTemplate="""
// Force {name}
//vdc_{lname} ({name} 0 ) vsource type=dc dc="0"
//vac_{lname} ({name} 0 ) vsource type=dc dc="0" mag=1
//vpulse_{lname} ({name} 0 ) vsource type=pulse val0=0 vall=vdda period=1/cfs rise=50p fall=50p width=1/cfs/2
//i{lname} (0 {name})  isource type=dc dc="0"
//r{lname} ({name} 0) resistor r=10M
//c{lname} ({name} 0) capacitor c=10f
"""

spectreTbTemplate="""

//-----------------------------------------------------------------
// OPTIONS
//-----------------------------------------------------------------

global 0

simulatorOptions options reltol=1e-6 vabstol=1e-6 save=selected \\
iabstol=1e-12 gmin=1e-15 redefinedparams=warning digits=7 cols=80 \\ 
pivrel=1e-3  checklimitdest=both

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
