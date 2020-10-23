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

    def __init__(self,simconf):
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

    def addForce(self,ftype,name,val):
        if(ftype == "vdc"):
            self.fo.write(f"v{name.lower()} ({name} 0) vsource type=dc dc={val} \n")
        if(ftype == "idc"):
            self.fo.write(f"i{name.lower()} (0 {name}) isource type=dc dc={val} \n")
        if(ftype == "resistance"):
            self.fo.write(f"r{name.lower()} ({name} 0) resistor r={val} \n")
        if(ftype == "capacitance"):
            self.fo.write(f"c{name.lower()} ({name} 0) capacitor c={val} \n")

        
    def addSubckt(self,subckt,nodes):
        self.fo.write("xdut (" +" ".join(nodes) +  f") {subckt}\n")


def writeSpectreTestbench(filename):

        stb = spectreTbTemplate

        stb = stb.replace("{name}",filename.replace(".scs",""))

#        m = re.findall("\"(\w+\.scs)\"",stb)
#        for mg in m:
#            if(not os.path.exists(mg)):
#                with open(mg,"w") as fo:
#                    fo.write("")

        with open(filename,"w") as fo:
            print(stb,file=fo)


spectreTbTemplate="""
{name}

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
include "../dut.scs"

//-----------------------------------------------------------------
// FORCE
//-----------------------------------------------------------------


//-----------------------------------------------------------------
// ANALYSIS
//-----------------------------------------------------------------

"""
