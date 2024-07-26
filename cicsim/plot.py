#!/usr/bin/env python3

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sys
from .command import *
import math
#import tikzplotlib
from .ngraw import *


def plot(df,xname,yname,ptype=None,ax=None,label=""):

    cmd = Command()
    if(xname not in df.columns):
        cmd.error("Could not find name %s in %s" %(xname,",".join(df.columns)))
        exit()
    if(yname not in df.columns):
        cmd.error("Could not find name %s in %s" %(xname,",".join(df.columns)))
        exit()
        #raise Exception("Could not find name %s in %s" %(yname,",".join(df.columns)))

    x = df[xname]
    y = df[yname]

    #- Plot
    if("logy" in ptype):
        ax.semilogy(x,y,label=yname+label)
    elif("ln2" in ptype):
        ax.plot(x,np.log(y)/np.log(2),label=yname+label)
    elif("logx" in ptype):
        ax.semilogx(x,y,label=yname+label)
    elif("db20" in ptype):
        ax.semilogx(x,20*np.log10(y),label="dB20(" + yname + label + ")")
    else:
        ax.plot(x,y,label=yname+label)

    ax.legend()

    if(ptype == ""):
        ax.set_ylabel(yname)
    ax.grid()
    return (x,y)


def rawplot(fraw,xname,yname,ptype=None,axes=None,fname=None):


    dfs = toDataFrames(ngRawRead(fraw))


    if(len(dfs)> 0):
        df = dfs[0]

    else:
        raise "You have multiple plots in .raw file, that's not supported"

    if("," in yname):
        names = yname.split(",")

        if("same" in ptype):
            f,axes = plt.subplots(1,1)
        else:
            f,axes = plt.subplots(len(names),1,sharex=True)

        for i in range(0,len(names)):
            if("same" in ptype):
                plot(df,xname,names[i],ptype,ax=axes)
            else:
                plot(df,xname,names[i],ptype,ax=axes[i])
        plt.xlabel(xname + "(" + fraw + ")")
    elif(axes is not None):
        plot(df,xname,yname,ptype,axes,label=" %s" %fraw)
    else:
        f,axes = plt.subplots(1,1)
        plot(df,xname,yname,ptype,axes,label=" %s" %fraw)



    plt.tight_layout()

    #if("tikz" in ptype):
    #    tikzplotlib.save(fname.replace(".csv",".pgf"))



    if(fname is not None):
        plt.savefig(fname)

    #if("pdf" not in ptype):
    #    plt.show()
