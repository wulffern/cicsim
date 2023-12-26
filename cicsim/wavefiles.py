#!/usr/bin/env python3

import cicsim as cs
import os

#- Model for wavefiles


class WaveFile():

    def __init__(self,fname):
        self.fname = fname
        self.name = os.path.basename(fname)

        self.df = cs.toDataFrame(fname)
        pass


    def getWaveNames(self):
        cols = self.df.columns
        return cols

    def getX(self):

        if("time" in self.df.columns):
            x = self.df["time"]
            xlabel = "time [s]"
        elif("frequency" in self.df.columns):
            x = self.df["frequency"]
            xlabel = "Frequency [Hz]"
        elif("v-sweep" in self.df.columns):
            x = self.df["v-sweep"]
            xlabel = "Voltage [V]"
        elif("temp-sweep" in self.df.columns):
            x = self.df["temp-sweep"]
            xlabel = "Temperature [C]"
        else:
            x = None

        return (x,xlabel)


    def getTag(self,yname):
        return self.fname + "/" + yname
    
    def getY(self,yname):
        return self.df[yname]




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
