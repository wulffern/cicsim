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


#- Few words on the coding in this file:
# 1. I use click, its really nice, just google "python click"
# 2. I try the design pattern "one command, one file in commands/* that inherits commands/command.py".
#    That's why it's instanciating a class below and doing <obj>.run()

@click.group()
def cli():
    """Custom IC Creator Simulator Tools

    This package provides helper scripts for simulating integrated circuits in Cadence Spectre
    """
    pass

@cli.command()
@click.argument("testbench")
@click.argument("corner",nargs=-1)
@click.option("--oformat",default="spectre",help="spectre|aimspice")
@click.option("--run/--no-run", default=True, help="Run simulator")
@click.option("--ocn/--no-ocn", default=True, help="Run ocean")
def run(testbench,oformat,run,ocn,corner):
    """Run a spectre simulation of TESTBENCH
    """
    r = cs.CmdRun(testbench,oformat,run,ocn,corner)
    r.run()

@cli.command()
@click.argument("testbench")
@click.argument("corner",nargs=-1)
@click.option("--oformat",default="spectre",help="spectre|aimspice")
@click.option("--run/--no-run", default=True, help="Run simulator")
@click.option("--ocn/--no-ocn", default=True, help="Run ocean")
def runng(testbench,oformat,run,ocn,corner):
    """Run a ngspice simulation of TESTBENCH
    """

    #TODO Add timing info

    r = cs.CmdRunNg(testbench,oformat,run,ocn,corner)
    r.run()


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
@click.argument("testbench")
def results(testbench):
    """Summarize results of TESTBENCH
    """
    r = cs.CmdResults(testbench)
    r.run()

@cli.command()
@click.argument("library",required=False)
@click.argument("cell",required=False)
@click.argument("view",required=False)
def simtb(library,cell,view):
    """Create a simulation directory for a testbench
    """
    simdir = cs.CmdSimDir(library,cell,view,True)
    simdir.run()

@cli.command()
@click.argument("library",required=False)
@click.argument("cell",required=False)
@click.argument("view",required=False)
def simcell(library,cell,view):
    """Create a simulation directory for a Cell
    """
    simdir = cs.CmdSimDir(library,cell,view,False)
    simdir.run()

@cli.command()
@click.argument("library",required=False)
@click.argument("cell",required=False)
@click.argument("view",required=False)
@click.option("--top/--no-top", default=False, help="Add subckt on top level")
def netlist(library,cell,view,top):
    """Netlist from a cadence library. This command will look for cicsim.yaml in the current directory and expects to find.

    cadence:\n
      library: <library name>\n
      cell: <cell name>\n
      view: <view name>\n

    or, you can specify on the commandline.

    """
    cds = cs.CdsConfig(library,cell,view)
    cds.netlist(top=top)

@cli.command("ip",help=cs.CmdIp.__doc__,short_help="make ip from a YAML template file")
@click.argument("ip",required=True)
@click.argument("template",required=True)
@click.option("--src", default=None, help="Copy files from another IP")
def cmd_ip(ip,template,src):
    c_ip = cs.CmdIp(ip,template,src)
    c_ip.run()

@cli.command("spider",help=cs.CmdSpider.__doc__,short_help="Make spider plot from Assembler csv file")
@click.argument("csvfile",required=True)
def cmd_ip(csvfile):
    c = cs.CmdSpider(csvfile)
    c.run()

    
if __name__ == "__main__":
    cli()
