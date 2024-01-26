#!/usr/bin/env python3

import cicsim as cs
import os
import numpy as np

#- Model for wavefiles

class Wave():

    def __init__(self,wfile,key):
        self.wfile = wfile
        self.x = None
        self.y = None
        self.xlabel = "Samples"
        self.key = key
        self.ylabel = key + f" ({wfile.name})"
        self.logx = False
        self.logy = False
        self.tag = wfile.getTag(self.key)
        self.line = None
        self.reload()

    def deleteLine(self):
        if(self.line):
            self.line.remove()
            self.line = None

    def plot(self,ax):
        if(self.x is not None):
            if(not self.logx and not self.logy):
                self.line, = ax.plot(self.x,self.y,label=self.ylabel)
            elif(self.logx and not self.logy):
                self.line, = ax.semilogx(self.x,self.y,label=self.ylabel)
            elif(not self.logx and self.logy):
                self.line, = ax.semilogy(self.x,self.y,label=self.ylabel)
            elif(self.logx and self.logy):
                self.line, = ax.loglog(self.x,self.y,label=self.ylabel)
        else:
            self.line, = ax.plot(self.y,label=self.ylabel)

        #ax.set_xlabel(self.xlabel)

    def reload(self):
        self.wfile.reload()

        keys = self.wfile.df.columns

        if("time" in keys):
            self.x = self.wfile.df["time"]
            self.xlabel = "Time [s]"
            self.y = self.wfile.df[self.key]
        elif("frequency" in keys):
            self.x = self.wfile.df["frequency"]
            self.xlabel = "Frequency [Hz]"
            self.logx = True
            self.y = self.wfile.df[self.key]
        elif("v-sweep" in keys):
            self.x = self.wfile.df["v-sweep"]
            self.xlabel = "Voltage [V]"
            self.y = self.wfile.df[self.key]
        elif("temp-sweep" in keys):
            self.x = self.wfile.df["temp-sweep"]
            self.xlabel = "Temperature [C]"
            self.y = self.wfile.df[self.key]

        if(self.line):
            if(self.x is not None):
                self.line.set_xdata(self.x)
            self.line.set_ydata(self.y)
        pass


class WaveFile():

    def __init__(self,fname):
        self.fname = fname
        self.name = os.path.basename(fname)
        self.waves = dict()
        self.df = None
        self.reload()
        pass

    def reload(self):
        if(self.df is None):
            self.df = cs.toDataFrame(self.fname)
            self.modified = os.path.getmtime(self.fname)
        else:
            newmodified = os.path.getmtime(self.fname)

            if(newmodified > self.modified):
                self.df = cs.toDataFrame(self.fname)
                self.modified = newmodified

    def getWaveNames(self):
        cols = self.df.columns
        return cols

    def getWave(self,yname):

        if(yname not in self.waves):
            wave = Wave(self,yname)
            self.waves[yname] = wave

        wave = self.waves[yname]
        wave.reload()

        return wave

    def getTag(self,yname):
        return self.fname + "/" + yname


class WaveFiles(dict):

    def __init__(self):
        self.current = None
        pass

    def open(self,fname):
        self[fname] = WaveFile(fname)
        self.current = fname
        return self[fname]

    def select(self,fname):
        if(fname in self):
            self.current = fname

    def getSelected(self):
        if(self.current is not None):
            return self[self.current]
