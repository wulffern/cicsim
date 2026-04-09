#!/usr/bin/env python3

import cicsim as cs
import os
import numpy as np
import pandas as pd
from matplotlib.ticker import EngFormatter

#- Model for wavefiles

class Wave():

    def __init__(self,wfile,key,xaxis):
        self.xaxis = xaxis
        self.wfile = wfile
        self.x = None
        self.y = None
        self.xlabel = "Samples"
        self.key = key
        self.ylabel = key + f" ({wfile.name})"
        self.logx = False
        self.logy = False
        self.xunit = ""
        self.yunit = self._infer_yunit(key)
        self.tag = wfile.getTag(self.key)
        self.line = None
        self.reload()

    @staticmethod
    def _infer_yunit(key):
        kl = key.lower()
        if kl.startswith("v(") or kl.startswith("v-"):
            return "V"
        if kl.startswith("i(") or kl.startswith("i-"):
            return "A"
        return ""

    def deleteLine(self):
        if(self.line):
            self.line.remove()
            self.line = None

    def plot(self,ax):
        x = np.real(self.x) if self.x is not None else None
        y = np.real(self.y) if self.y is not None else self.y
        if(x is not None):
            if(not self.logx and not self.logy):
                self.line, = ax.plot(x,y,label=self.ylabel)
            elif(self.logx and not self.logy):
                self.line, = ax.semilogx(x,y,label=self.ylabel)
            elif(not self.logx and self.logy):
                self.line, = ax.semilogy(x,y,label=self.ylabel)
            elif(self.logx and self.logy):
                self.line, = ax.loglog(x,y,label=self.ylabel)
        else:
            self.line, = ax.plot(y,label=self.ylabel)

        if self.xunit:
            ax.xaxis.set_major_formatter(EngFormatter(unit=self.xunit))
        if self.yunit:
            ax.yaxis.set_major_formatter(EngFormatter(unit=self.yunit))

    def reload(self):
        self.wfile.reload()

        keys = self.wfile.df.columns

        if("time" in keys):
            self.x = self.wfile.df["time"].to_numpy()
            self.xlabel = "Time"
            self.xunit = "s"
            self.y = self.wfile.df[self.key].to_numpy()
        elif("frequency" in keys):
            self.x = self.wfile.df["frequency"].to_numpy()
            self.xlabel = "Frequency"
            self.xunit = "Hz"
            self.logx = True
            self.y = self.wfile.df[self.key].to_numpy()
        elif("v(v-sweep)" in keys):
            self.x = self.wfile.df["v(v-sweep)"].to_numpy()
            self.xlabel = "Voltage"
            self.xunit = "V"
            self.y = self.wfile.df[self.key].to_numpy()
        elif("i(i-sweep)" in keys):
            self.x = self.wfile.df["i(i-sweep)"].to_numpy()
            self.xlabel = "Current"
            self.xunit = "A"
            self.y = self.wfile.df[self.key].to_numpy()
        elif("temp-sweep" in keys):
            self.x = self.wfile.df["temp-sweep"].to_numpy()
            self.xlabel = "Temperature"
            self.xunit = "°C"
            self.y = self.wfile.df[self.key].to_numpy()
        elif(self.xaxis in keys):
            self.x = self.wfile.df[self.xaxis].to_numpy()
            self.xlabel = " "
            self.xunit = ""
            self.y = self.wfile.df[self.key].to_numpy()

        if(self.line):
            if(self.x is not None):
                self.line.set_xdata(self.x)
            self.line.set_ydata(self.y)
        pass


class WaveFile():

    def __init__(self,fname,xaxis,sheet_name=0,df=None):
        self.xaxis = xaxis
        self.fname = fname
        self.sheet_name = sheet_name
        self.name = os.path.basename(fname)
        if isinstance(sheet_name, str):
            self.name += " [%s]" % sheet_name
        self.waves = dict()
        self.df = df
        self._virtual = df is not None
        self.reload()
        pass

    def reload(self):
        if self._virtual:
            return
        if(self.df is None):
            self.df = self._read_file()
            self.modified = os.path.getmtime(self.fname)
        else:
            newmodified = os.path.getmtime(self.fname)

            if(newmodified > self.modified):
                self.df = self._read_file()
                self.modified = newmodified

    PANDAS_READERS = {
        '.csv':     lambda self: self._read_csv(','),
        '.tsv':     lambda self: self._read_csv('\t'),
        '.txt':     lambda self: self._read_csv('\t'),
        '.xlsx':    lambda self: self._read_excel(),
        '.xls':     lambda self: self._read_excel(),
        '.ods':     lambda self: self._read_excel(),
        '.pkl':     lambda self: pd.read_pickle(self.fname),
        '.pickle':  lambda self: pd.read_pickle(self.fname),
        '.json':    lambda self: pd.read_json(self.fname),
        '.parquet': lambda self: pd.read_parquet(self.fname),
        '.feather': lambda self: pd.read_feather(self.fname),
        '.h5':      lambda self: pd.read_hdf(self.fname),
        '.hdf5':    lambda self: pd.read_hdf(self.fname),
        '.html':    lambda self: pd.read_html(self.fname)[0],
        '.xml':     lambda self: pd.read_xml(self.fname),
        '.fwf':     lambda self: pd.read_fwf(self.fname),
        '.stata':   lambda self: pd.read_stata(self.fname),
        '.dta':     lambda self: pd.read_stata(self.fname),
        '.sas7bdat': lambda self: pd.read_sas(self.fname),
        '.sav':     lambda self: pd.read_spss(self.fname),
    }

    def _read_file(self):
        ext = os.path.splitext(self.fname)[1].lower()
        reader = self.PANDAS_READERS.get(ext)
        if reader:
            return reader(self)
        return cs.toDataFrame(self.fname)

    def _read_csv(self, sep):
        try:
            df = pd.read_csv(self.fname, sep=sep)
        except Exception:
            df = pd.read_csv(self.fname, sep=None, engine='python')
        df.columns = [c.strip() for c in df.columns]
        return df

    def _read_excel(self):
        df = pd.read_excel(self.fname, sheet_name=self.sheet_name)
        df.columns = [c.strip() for c in df.columns]
        return df

    @staticmethod
    def excel_sheet_names(fname):
        xl = pd.ExcelFile(fname)
        return xl.sheet_names

    def getWaveNames(self):
        cols = self.df.columns
        return cols

    def getWave(self,yname):

        if(yname not in self.waves):
            wave = Wave(self,yname,self.xaxis)
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

    def open(self,fname,xaxis,sheet_name=0):
        key = fname if sheet_name == 0 else "%s::%s" % (fname, sheet_name)
        self[key] = WaveFile(fname,xaxis,sheet_name)
        self.current = key
        return self[key]

    def openDataFrame(self, df, name, xaxis):
        key = "::virtual::" + name
        self[key] = WaveFile(name, xaxis, df=df)
        self.current = key
        return self[key]

    def select(self,fname):
        if(fname in self):
            self.current = fname

    def remove(self, key):
        """Remove a loaded file by dict key. Updates current if needed."""
        if key not in self:
            return
        del self[key]
        if self.current == key:
            self.current = next(iter(self.keys()), None)

    def clear_all(self):
        """Remove every loaded file."""
        dict.clear(self)
        self.current = None

    def getSelected(self):
        if(self.current is not None):
            return self[self.current]
