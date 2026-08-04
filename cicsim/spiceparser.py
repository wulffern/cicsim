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
import difflib

class SpiceParser():

    def __init__(self):
        pass

    def logicalLines(self,fi):
        """Yield logical spice lines, with continuations folded in

        Spice marks a continuation with a leading '+' on the next line. Some
        tools instead mark it with a trailing '\\' on the current line. Handle
        both, otherwise the '+' style silently truncates the port list.
        """
        current = None
        #- Did the previous line end with a backslash?
        pending = False

        for line in fi:
            line = line.rstrip("\n")

            #- Full line comments
            if(re.match(r"\s*\*",line)):
                continue

            isCont = pending or line.strip().startswith("+")

            pending = bool(re.search(r"\\\s*$",line))
            line = re.sub(r"\\\s*$","",line)
            line = re.sub(r"^\s*\+\s*"," ",line)

            if(isCont and current is not None):
                current += " " + line.strip()
            else:
                if(current is not None):
                    yield current
                current = line

        if(current is not None):
            yield current

    def portsFromHeader(self,header):
        """Pull the port names out of a folded .SUBCKT header line"""

        #- '$' and ';' start an inline comment, but only after whitespace,
        #- since net names are allowed to contain '$'
        header = re.split(r"(?:\s|^)[$;]",header)[0]

        tokens = header.split()
        #- Remove .SUBCKT and the subckt name
        tokens = tokens[2:]

        ports = []
        for t in tokens:
            #- The parameter list ends the ports, in either spelling
            if(t.lower() == "params:" or "=" in t):
                break
            ports.append(t)

        return ports

    def fastGetPortsFromFile(self,spicefile,subckt):
        ckts = []
        header = None

        with open(f"{spicefile}","r") as fi:
            for line in self.logicalLines(fi):
                m = re.match(r"\s*\.SUBCKT\s+(\S+)",line,re.IGNORECASE)
                if(m is None):
                    continue

                ckts.append(m.group(1))

                #- Compare as tokens, not as a regex, so that a name which is
                #- a prefix of another, or contains regex characters, is safe
                if(header is None and m.group(1).lower() == subckt.lower()):
                    header = line

        if header is None:
            cktopt= difflib.get_close_matches(subckt,ckts)
            print(f"Error: Could not find '{subckt}', maybe you meant " + str(cktopt))
            return

        return self.portsFromHeader(header)
