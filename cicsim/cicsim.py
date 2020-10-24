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

def writeDutFile(cfg,oformat):
    #- Check if default config file exist
    if(cfg == None and os.path.exists("dut.cfg")):
        cfg = "dut.cfg"
    if(cfg):
        sc = cs.SimConf()
        sc.fromFile(cfg)

        if(oformat == "spectre"):
            ss = cs.SpectreWriter(sc)
            ss.write()
    

@click.group()
def cli():
    """Custom IC Creator Simulator Tools

    This package provides helper scripts for simulating integrated circuits in Cadence Spectre
    """
    pass

@cli.command()
@click.argument("spicefile")
@click.argument("subckt")
def dutconf(spicefile,subckt):
    """Make a JSON configuration from a SPICEFILE and a SUBCKT

    Default output filename will be tmp_sim.cfg
    """
    sp = cs.SpiceParser()
    ports = sp.fastGetPortsFromFile(spicefile,subckt)
    sc = cs.getSimConf(subckt,ports)
    sc.toFile("tmp_sim.cfg")

@cli.command()
@click.argument("testbench")
@click.argument("corner",nargs=-1)
@click.option("--cfg", default=None, help="DUT Config file")
@click.option("--oformat",default="spectre",help="spectre|aimspice")
@click.option("--run/--no-run", default=False, help="Run simulator")
def run(cfg,testbench,oformat,run,corner):
    """Run a simulation of TESTBENCH
    """
    cm = cs.Command()
    filename = testbench + ".scs"
    if(not os.path.exists(filename)):
        cm.error("Testbench '{filename}' does not exists in this folder")
        return

    

    writeDutFile(cfg,oformat)
    rc = cs.RunConfig()

    permutations = rc.getPermutations(corner)
    
    for p in permutations:
        path = f"output_{testbench}" + os.path.sep + testbench +  "_"+ "".join(p) + ".scs"
        rc.makeSpectreFile(filename,p,path)
        cm.comment("Running {p}")
        rc.run()


@cli.command()
@click.argument("library",required=False)
@click.argument("cell",required=False)
@click.argument("view",required=False)
def netlist(library,cell,view):
    """Netlist from a cadence library. This command will look for cicsim.yaml in the current directory and expects to find.

    cadence:\n
      library: <library name>\n
      cell: <cell name>\n
      view: <view name>\n

    or, you can specify on the commandline.

    """
    rc = cs.RunConfig()
    rc.netlist(library,cell,view)
    

#@cli.command()
#@click.argument("testbench")
#@click.option("--force/--no-force",default=False,help="Force testbench override")
#def tb(testbench,force):
#    cm = cs.Command()
#    if(not force and os.path.exists(testbench)):
#        cm.error(f"Error: {testbench} aready exists, don't want to override when force is off")
#        return

#    cs.writeSpectreTestbench(testbench)

if __name__ == "__main__":
    cli()
