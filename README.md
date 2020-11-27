
# Custom IC Creator Simulation Tools

# Why
This is a script package I use to control spectre, it can
- Netlist from cadence
- Run corner simulations
- Run ocean scripts on spectre results
- Run python scripts to combine ocean results
- Combine results

 
# Plan
- [x] Learn how to use setup.py
- [x] Add wrapper script for netlisting
- [x] Add wrapper sript for generating corners based on YAML files
- [x] Add script for simulating
- [x] Add hooks for adding custom python output parsing
- [x] Add hooks to run a post python script per corner
- [x] Aggregate extracted parmeters and store in a dataframe
- [ ] Write the scripts as easy as I can, and understandable as I can.


# Requirements:
- Python > 3.6.6


## Know what python you're running

Python is great, however, python exists in many different versions, and you can
never trust that the right version is installed on the system that you're going
to use. As such, always know what you're running.

### Option 1: Build yourself
If you don't control the system, then you can still install locally
http://thelazylog.com/install-python-as-local-user-on-linux/

It's not straightforward though, and it can be a rabbit hole that takes some
time

### Option 2: Check version
Try 

  python3 --version

Or

  python --version 

### Option 3: Set version
Sometimes multiple versions can be installed, if so, then you can add the
following lines to your .bashrc file
  
  alias python3='/usr/local/bin/python3.8'
  alias pip3='/usr/local/bin/pip3.8'

# Install this module
If you want to follow the latest and greatest
``` sh
mkdir pro
cd pro
git clone https://github.com/wulffern/cicsim
cd cicsim
pip3 install -r requirements.txt --user
pip3 install --no-deps -e .
```
# Get started with simulation
See tests/ for how cicsim
expects the simulation directory to be layed out.

### tests/cicsim.yaml
This is the main config file for cicsim, it sets up corners, links to cadence,
how to find the model files etc

### tests/BFX1_CV/cicsim.yaml
This is the child config file. The general rule is, one cell, one directory with
a cicsim.yaml file. The YAML file must contain the following:

``` yaml
cadence:
  library: <cadence library name>
  cell: <cadence cell name>
  view: <cadence view, usually schematic is the one you want>
```

The `tests/BFX1_CV/cicsim.yaml' example also shows how you can add corners to
include the spice file.

# Commands
---
##cicsim simdir
There are two senarios for the simulation directory creation. 

1. Top level is a cadence testbench, with sources etc
2. Top level is the circuit top level (to testbench structures)

If you'd like to do everything, include the testbench, in spectre, you want the
first option. If you want to draw the testbench in cadence, choose the second

### Barebone spectre

Run cicsim simdir, for example
``` sh
cicsim simcell AGNEZA_SAR9B_GF130N SAR9B_CV schematic 
```

cicsim expects to be told via the cicsim.yaml where the cadence work directory
is via the cicsim.yaml file

``` yaml
cadence:
  cds_dir: $PROJECT/work/wulff
```

cicsim simcell will, as of the time of writing, generate
- Directory from cell name
- Netlist the schematic
- Create a dut spectre file (cell/dut.scs)
- Create default testbench (cell/tran.scs)
- Create default Makefile (cell/Makefile)
- Create default YAML file (cell/cicsim.yaml)

Once it's complete, you should be able to go into cell directory and run "make
typical" and spectre will tell you what's missing

### Cadence testbench
Run cicsim simtb, for example
``` sh
cicsim simtb AGNEZA_SAR9B_GF130N TB_SAR9B_CV schematic
```

cicsim simtb will, as of the time of writing, generate
- Directory from cell name
- Netlist the schematic
- Create default testbench (cell/tran.scs)
- Create default Makefile (cell/Makefile)
- Create default YAML file (cell/cicsim.yaml)

Once it's complete, you should be able to go into cell directory and run "make
typical" and spectre will tell you what's missing

## cicsim netlist

## cicsim run

## cicsim results






