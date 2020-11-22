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

import json
import click
import sys
import re
import os
import difflib
import cicsim as cs
import importlib

@click.group()
def cli():
    """Custom IC Creator Simulator Tools

    This package provides helper scripts for simulating integrated circuits in Cadence Spectre
    """
    pass

@cli.command()
@click.argument("spicefile",required=False)
@click.argument("subckt",required=False)
def dut(spicefile,subckt):
    """Make a device under test file for SPICEFILE and SUBCKT
    """
    rc = cs.RunConfig()
    rc.dut(spicefile,subckt)

@cli.command()
@click.argument("testbench")
@click.argument("corner",nargs=-1)
@click.option("--oformat",default="spectre",help="spectre|aimspice")
@click.option("--run/--no-run", default=True, help="Run simulator")
@click.option("--ocn/--no-ocn", default=True, help="Run ocean")
def run(testbench,oformat,run,ocn,corner):
    """Run a simulation of TESTBENCH
    """
    cm = cs.Command()
    filename = testbench + ".scs"
    if(not os.path.exists(filename)):
        cm.error("Testbench '{filename}' does not exists in this folder")
        return
    rc = cs.RunConfig()

    permutations = rc.getPermutations(corner)

    for p in permutations:
        fname = f"output_{testbench}" + os.path.sep + testbench +  "_"+ "".join(p)
        path = fname + ".scs"
        cm.comment(f"Running results {path}")
        simOk = True
        if(run):
            rc.makeSpectreFile(filename,p,path)
            cm.comment(f"Running {p}")
            if( rc.run() > 0):
                simOk = False

        if(not simOk):
            cm.error("Simulation failed ")
            continue

        cm.comment(f"Parsing results {fname}")

        #- Run ocean post parsing if it exists
        ocnscript = testbench + ".ocn"
        if(os.path.exists(ocnscript) and ocn):
            ocnfo = fname + ".ocn"
            resultsDir = os.getcwd() + os.path.sep+ fname + ".psf"
            resultsFile = os.getcwd() + os.path.sep+ fname + ".yaml"

            with open(ocnscript,"r") as fi:
                buffer = fi.read()
                buffer = f"cicResultsDir = \"{resultsDir}\"\ncicResultsFile = \"{resultsFile}\"\n" + buffer
            with open(ocnfo,"w") as fo:
                fo.write(buffer)
            os.system(f"ocean -nograph -replay {ocnfo}")
        else:
            cm.warning(f" {ocnscript} not found")

        #- Run python post parsing if it exists
        pyscript = testbench + ".py"
        if(os.path.exists(pyscript)):
            sys.path.append(os.getcwd())
            tb = importlib.import_module(testbench)
            tb.main(fname)
        else:
            cm.warning(f" {pyscript} not found")


def simdir(library,cell,view,tb):
    """
    Create a simulation directory
    """
    rc = cs.RunConfig(library,cell,view)
    if(rc.makeDirectory()):
        os.chdir(cell)
        rc.netlist(top=(not tb))
        if(not tb):
            rc.dut()
        cs.writeSpectreTestbench("tran.scs",tb=tb)
        with open("Makefile","w") as fo:
            fo.write(cs.template_make)

@cli.command()
@click.argument("library",required=False)
@click.argument("cell",required=False)
@click.argument("view",required=False)
def simtb(library,cell,view):
    """Create a simulation directory for a testbench
    """
    simdir(library,cell,view,True)

@cli.command()
@click.argument("library",required=False)
@click.argument("cell",required=False)
@click.argument("view",required=False)
def simcell(library,cell,view):
    """Create a simulation directory for a Cell
    """
    simdir(library,cell,view,False)


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
    rc = cs.RunConfig(library,cell,view)
    rc.netlist(top=top)

if __name__ == "__main__":
    cli()
