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

import re
import json
import difflib

class SpiceParser():

    def __init__(self):
        pass

    def fastGetPortsFromFile(self,spicefile,subckt):
        cktbuff = []
        ckts = []
        with open(f"{spicefile}","r") as fi:
            match = False

            for line in fi:
                if(match):
                    cktbuff.append(line)

                if(re.search(f"\s*.?SUBCKT\s+{subckt}\s+",line,re.IGNORECASE)):
                    match = True
                    cktbuff.append(line)

                if(not re.search(r"\s*[\+\\]\n?$",line)):
                    match = False

                m = re.search("\s*.?SUBCKT\s+([^\s]+)",line,re.IGNORECASE)
                if(m is not None):
                    ckts.append(m.group(1))

        if(cktbuff is None):
            cktopt= difflib.get_close_matches(subckt,ckts)
            print(f"Error: Could not find '{subckt}', maybe you meant " + str(cktopt))
            return

        cktstr = ""
        for line in cktbuff:
            line = re.sub(r"[\+\\]\n$","",line)

            cktstr += line

        cktstr = re.sub("\s+"," ",cktstr)


        ports = cktstr.split(" ")
        #- Remove .SUBCKT
        ports.pop(0)
        #- Remove subckt name
        ports.pop(0)

        # TODO Is this dirty hackish?? Let's see if it fails in the future
        for i in range(0,len(ports)):
            if(ports[i] == ""):
                ports.pop(i)
                i = i-1


        return ports
