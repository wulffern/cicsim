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

def getSimConf(subckt,ports):

    sc = SimConf(subckt)
    for p in ports:
        sc.addConf(p)
    return sc

def is_int(s):
    s = str(s)
    if s[0] in ('-', '+'):
        return s[1:].isdigit()
    return s.isdigit()

class SimConfPort:

    def __init__(self,name=None,parent=None):
        self.name = name
        self.parent = parent
        self.porttype = ""
        self.force = {
            "vdc": None,
            "idc" : None,
            "resistance" : None,
            "capacitance" : None
        }

        self.guessType()

    def guessType(self):
        if("VSS" in self.name):
            self.force["vdc"] = 0
            self.porttype = "ground"
        elif("VDD" in self.name):
            self.force["vdc"] = self.name.lower()

            self.porttype = "supply"
        elif(re.search(r"(_\d+V\d+|_[CE]V)$|<\d+>",self.name)):
            self.force["resistance"] = "1M"
            self.force["capacitance"] = "10f"
            self.porttype = "digital"
        else:
            self.porttype = "analog"

    def write(self,writer):
        #- Write forces
        for f in self.force:
            if(self.force[f] is not None):
                val = self.force[f]
                writer.addForce(f,self.name,val)




    def toJson(self):
        d = {}
        d["name"] = self.name
        d["porttype"] = self.porttype
        d["force"] = self.force
        return d

    def fromJson(self,o):
        self.name = o["name"]
        self.porttype = o["porttype"]
        self.force = o["force"]

        


class SimConf:
    def __init__(self,name=None):
        self.ports = {}
        self.nodes =[]
        self.filename = "dut.scs"
        self.name = name
        self.version = 1


    def addConf(self,p):
        sp = SimConfPort(p,self)
        self.nodes.append(p)
        self.ports[sp.name]  = sp



    def toJson(self):
        d = {}
        d["version"] = self.version
        d["nodes"] = self.nodes
        d["name"] = self.name
        d["filename"] = self.filename
        p = {}
        for pn in self.ports:
            p[pn] = self.ports[pn].toJson()
        d["ports"] = p
        return d

    def fromJson(self,o):
        self.version = o["version"]
        self.name = o["name"]
        self.nodes = o["nodes"]
        self.filename = o["filename"]
        
        for p in o["ports"]:
            sc = SimConfPort(p,self)
            sc.fromJson(o["ports"][p])
            self.ports[p] = sc



    def toFile(self,fname):
        data = self.toJson()
        with open(fname,"w") as fo:
            json.dump(data,fo,indent=4)

    def fromFile(self,fname):
        with open(fname,"r") as fi:
            data = json.load(fi)
            self.fromJson(data)
        return self

    def writePorts(self,writer):
        for p in self.ports:
            writer.addComment("Force " + p)
            pd = self.ports[p]
            pd.write(writer)
            writer.addLine()

    def writeSubckt(self,writer):
        
        writer.addSubckt(self.name,self.nodes)
        writer.addLine()
