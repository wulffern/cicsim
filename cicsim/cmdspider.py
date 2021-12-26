#!/usr/bin/env python3

######################################################################
##        Copyright (c) 2020 Carsten Wulff Software, Norway
## ###################################################################
## Created       : wulff at 2020-12-11
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
import pandas as pd
import numpy as np
import re
import os
import io
import errno
import yaml
import shutil as sh

class CmdSpider(cs.Command):
    """Make spinder plots from csv file
    """


    def __init__(self,fname):
        self.fname = fname
        super().__init__()

    def loadFile(self):
        if(not os.path.exists(self.fname)):
            print("Could not find self.fname")
            return

        buffer = ""


        with open(self.fname) as fi:
            for line in fi:
                if(re.search("^Test",line)):
                    self.loadHeader(buffer)
                    buffer = ""
                buffer += line
            self.loadCorners(buffer)

    def loadHeader(self,buffer):
        self.hf = pd.read_csv(io.StringIO(buffer))

    def loadCorners(self,buffer):
        self.df = pd.read_csv(io.StringIO(buffer))

    def getRotationMatrix(self,angle):
        return np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]])


    def getGroup(self,cr,crn,grpcrn):
        ch = cr[0]
        for c in crn:
            if(c.startswith(ch)):

                if(c == "Msf" or c == "Mfs"):
                    grpcrn["M2"] = dict()
                    grpcrn["M2"]["Mfs"] = 1
                    grpcrn["M2"]["Msf"] = 1

                else:
                    if(ch not in grpcrn):
                        grpcrn[ch] = dict()
                    grpcrn[ch][c] = 1

    def computeRotationMatrices(self):
        crn = dict()
        cnt = 0
        # Figure out what corners are unique
        for c in self.hf.columns:
            if(re.search("Unnamed|Parameter",c)):
               continue
            ser = self.hf[c]
            for s in ser:
                if(s in crn):
                    crn[s] += 1
                else:
                    crn[s] = 1
            cnt += 1

        #- Remove constant corners
        ldel = list()
        for c in crn:
            if(crn[c] == cnt):
                ldel.append(c)
        for l in ldel:
            crn.pop(l)

        #- Group corners
        grpcrn = dict()
        for c in crn:
            self.getGroup(c,crn,grpcrn)
        print(grpcrn)

        angle_step = np.pi/(len(grpcrn.keys())+1)
        mat = dict()
        a  = 0
        for ch in grpcrn:
            d = grpcrn[ch]
            cnt = len(d.keys())
            step = 4/cnt
            pos = 1
            for c in d:

                if(pos > 0):
                    mat[c]  = self.getRotationMatrix(-a)
                elif(pos < 0):
                    mat[c]  = self.getRotationMatrix(np.pi - a)
                else:
                    mat[c]  = self.getRotationMatrix(0)

                pos -= step
            a += angle_step

        self.mat = mat

    def run(self):
        self.loadFile()
        self.computeRotationMatrices()
        print(self.df)
