#!/usr/bin/env python3

import cicsim as cs
import os
import yaml

class SpecMinMax:
    def __init__(self,obj = None):

        self.min = None
        self.max = None
        self.name = None
        self.unit = "V"
        self.scale = 1
        self.typ = 0
        self.digits = 2
        self.sources = list()

        if(obj):
            if("src" in obj):
                if(type(obj["src"]) is list):
                    for s in obj["src"]:
                        self.sources.append(s)
                else:
                    self.sources.append(obj["src"])
            if("typ" in obj):
                if(type(obj["typ"]) is str):
                    self.typ = eval(obj["typ"])
                else:
                    self.typ = obj["typ"]

            if("min" in obj):
                if(type(obj["min"]) is str):
                    s  = obj["min"]
                    if("%" in s):
                        self.min = self.typ*(1 + float(s.replace("%",""))/100)
                    else:
                        self.min = eval(s)
                else:
                    self.min = obj["min"]

            if("max" in obj):
                if(type(obj["max"]) is str):
                    s  = obj["max"]
                    if("%" in s):
                        self.max = self.typ*(1 + float(s.replace("%",""))/100)
                    else:
                        self.max = eval(s)
                else:
                    self.max = obj["max"]
            if("scale" in obj):
                self.scale = float(obj["scale"])
            if("unit" in obj):
                self.unit = obj["unit"]
            if("digits" in obj):
                self.digits = obj["digits"]

            if("name" in obj):
                self.name = obj["name"]
            else:
                self.name = ""

            #print(self.min,self.typ,self.max)


    def css(self,ser):

        css = list()
        for v in ser:

            if(self.max and self.min and (v > self.max or v < self.min)):
                css.append('background-color:lightcoral')
            else:
                css.append('')
        return css


    def format(self):
        return "{0:.%df} %s" % (self.digits,self.unit)

    def applyScale(self,s):

        return s*self.scale
    def OK(self,v):
        if(self.min and self.max and (v > self.max or v < self.min)):
            return False
        else:
            return True
    def string(self,v):
        if(v):
            return str.format(self.format(),v)
        else:
            return ""

    def stringNoUnit(self,v):
        if(v is None):
            return ""
        return str.format("{0:.%df}" % (self.digits),v)

    def markdown(self,v):
        if(v is None):
            return ""
        md = str.format("{0:.%df}" % (self.digits),v)
        if(self.OK(v)):
            return md
        else:
            return "<span style='color:red'>**" + md + "**</span>"



class Specification(dict):

    def __init__(self,testbench):
        self.fname = testbench + ".yaml"
        self.sources = list()

        if(os.path.exists(self.fname)):
            with open(self.fname,"r") as fi:
                specobj = yaml.safe_load(fi)
            if(specobj):
                for k, v in specobj.items():
                    if("type"in v):
                        #Preparing for future types
                        pass
                    else:
                        self[k] = SpecMinMax(v)
                        for s in self[k].sources:
                            self.sources.append(s)
                            self[s] = self[k]

    def css(self,s):
        if(s.name in self):
            return self[s.name].css(s)
        else:
            return ['' for v in s]

    def scale(self,s):
        if(s.name in self):
            return self[s.name].applyScale(s)
        else:
            return s

    def OK(self,s):
        isOk = True
        for field in s.index:

            if(field in self):
                isOk &= self[field].OK(s[field])
        return isOk
        #return isOk


    def format_dict(self):

        d = dict()
        for s,v in self.items():
            d[s] = v.format()
        return d
