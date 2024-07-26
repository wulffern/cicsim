#!/usr/bin/env python3
######################################################################
##        Copyright (c) 2020 Carsten Wulff Software, Norway
## ###################################################################
## Created       : wulff at 2020-10-23
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

import yaml
import errno
import json
import click
import sys
import re
import os
import cicsim as cs
import importlib
import glob
import pandas as pd
import matplotlib.pyplot as plt
import datetime


#- Few words on the coding in this file:
# 1. I use click, its really nice, just google "python click"
# 2. I try the design pattern "one command, one file in cmd* that inherits command.py".
#    That's why it's instanciating a class below and doing <obj>.run()


@click.group()
def cli():
    """Custom Integrated Circuit Simulation

    This package provides helper scripts for simulating integrated circuits

    Check website for more information : http://analogicus.com/cicsim/

    """
    pass

@cli.command()
@click.argument("testbench")
@click.argument("corner",nargs=-1)
@click.option("--run/--no-run", default=True, help="Run simulator")
@click.option("--count", default=1, help="Run each corner count times, useful for Monte-Carlo")
@click.option("--name", default=None, help="Control name of run file")
@click.option("--ignore/--no-ignore", default=False,is_flag=True, help="Ignore error checks")
@click.option("--sha/--no-sha", default=None, help="Check SHA of input files")
@click.option("--replace",default=None, help="YAML file with replacements for netlist")
def run(testbench,run,corner,count,name,ignore,sha,replace):
    """Run a ngspice simulation of TESTBENCH
    """
    r = cs.CmdRunNg(testbench,run,corner,name,count,sha)
    r.loadReplacements(replace)

    r.run(ignore)

@cli.command()
@click.argument("files",nargs=-1)
def wave(files):
    """Open waveform viewer"""

    if not importlib.util.find_spec("tkinter"):
        print("Error: Could not find tkinter. Install python3-tk")
        print("On mac with brew: brew install python3-tk")
        print("On ubuntu: apt install python3-tk")
        exit()

    c = cs.CmdWave()
    for f in files:
        c.openFile(f)
    c.run()



@cli.command()
@click.argument("testbench")
@click.argument("corner",nargs=-1)
@click.option("--oformat",default="spectre",help="spectre")
@click.option("--run/--no-run", default=True, help="Run simulator")
@click.option("--ocn/--no-ocn", default=True, help="Run ocean")
#@click.option("--count", default=1, help="Run each corner count times, useful for Monte-Carlo")
#@click.option("--name", default=None, help="Control name of run file")
#@click.option("--ignore/--no-ignore", default=False,is_flag=True, help="Ignore error check")
#@click.option("--sha/--no-sha", default=False, help="Check SHA of input files")
def srun(testbench,corner,oformat,run,ocn,count,name,ignore,sha):
    """Run a spectre simulation of TESTBENCH
    """

    r = cs.CmdRun(testbench,oformat,run,ocn,corner)
    r.run(ignore)


@cli.command()
@click.argument("filename")
@click.argument("xname")
@click.argument("yname")
@click.option("--ptype",default="", help="Plot options")
@click.option("--show/--no-show",default=True,help="Show plot or not")
@click.option("--fname",default="", help="Plot filename")
def plot(filename,xname,yname,ptype,show,fname):
    """Plot from rawfile

Example:\n
    Plot vp and vn versus time.\n
    $ cicsim plot test.raw time "v(vp),v(vn)"

    Plot vp and vn in the same plot\n
    $ cicsim plot test.raw time "v(vp),v(vn)" --ptype "same"


    """
    cs.rawplot(filename,xname,yname,ptype,fname=fname)
    if(show):
        plt.show()

@cli.command()
@click.argument("runfile")
def results(runfile):
    """Results of single runfile
    """
    r = cs.CmdResults(runfile)
    r.run()

@cli.command()
@click.option("--filename",default="summary.yaml",help="Input config file")
@click.option("--output",default="summary.md",help="Output summary file")
def summary(filename,output):
    """Generate simulation summary for results
    """
    r = cs.CmdSummary(filename,output)
    r.run()

@cli.command()
@click.argument("library",required=True)
@click.argument("cell",required=True)
@click.argument("template",required=True)
def simcell(library,cell,template):
    """Create a ngspice simulation directory for a Cell
    """
    c_ip = cs.CmdIp(library,template,cell=cell)
    c_ip.run()

@cli.command()
@click.argument("testbench",required=True)
@click.argument("source",required=True)
@click.argument("cell",required=True)
def portreplace(testbench,source,cell):
    """ Replace ${PORTS} and ${VPORTS} with the subcircuit ports of SOURCE CELL
    """
    stb = ""
    with open(testbench) as fi:
        for l in fi:
            stb += l

    sp = cs.SpiceParser()
    ports = sp.fastGetPortsFromFile(source,cell)
    stb = stb.replace("${PORTS}"," ".join(ports))

    stb = stb.replace("${VPORTS}"," ".join(map(lambda x: "v(%s)"%x,ports)))
    with open(testbench,"w") as fo:
        fo.write(stb)


if __name__ == "__main__":
    cli()
