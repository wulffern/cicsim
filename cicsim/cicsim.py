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
# 2. I try the design pattern "one command, one file in commands/* that inherits commands/command.py".
#    That's why it's instanciating a class below and doing <obj>.run()



@click.group()
def cli():
    """Custom IC Creator Simulator Tools

    This package provides helper scripts for simulating integrated circuits
    """
    pass

@cli.command()
@click.argument("testbench")
@click.argument("corner",nargs=-1)
@click.option("--oformat",default="spectre",help="spectre|aimspice")
@click.option("--run/--no-run", default=True, help="Run simulator")
@click.option("--count", default=1, help="Run each corner count times, useful for Monte-Carlo")
@click.option("--name", default=None, help="Control name of run file")
@click.option("--ignore/--no-ignore", default=False,is_flag=True, help="Ignore error check")
def run(testbench,oformat,run,corner,count,name,ignore):
    """Run a ngspice simulation of TESTBENCH
    """
    r = cs.CmdRunNg(testbench,oformat,run,corner,name,count)
    r.run(ignore)


@cli.command()
@click.argument("filename")
@click.argument("xname")
@click.argument("yname")
@click.option("--ptype",default="", help="Plot options")
def plot(filename,xname,yname,ptype):
    """Plot from rawfile
    """
    cs.rawplot(filename,xname,yname,ptype)
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

@cli.command("ip",help=cs.CmdIp.__doc__,short_help="make ip from a YAML template file")
@click.argument("ip",required=True)
@click.argument("template",required=True)
@click.option("--src", default=None, help="Copy files from another IP")
def cmd_ip(ip,template,src):
    c_ip = cs.CmdIp(ip,template,src)
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
