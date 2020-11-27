
# Custom IC Creator Simulation Tools

![tests/sim/BFX1_CV](https://github.com/wulffern/cicsim/workflows/tests/sim/BFX1_CV/badge.svg)

# Why
This is a script package I use to control spectre, it can
- Netlist from cadence
- Run corner simulations
- Run ocean scripts on spectre results
- Run python scripts to combine ocean results
- Combine results

 
# Changelog

| Version | Status | Comment |
|:--|:--|:--|
|0.0.2| to be released | Probably bugfixes|
|0.0.1| :white_check_mark: | First version of cicsim|

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
See tests/sim for how cicsim
expects the simulation directory to be layed out.

### tests/sim/cicsim.yaml
This is the main config file for cicsim, it sets up corners, links to cadence,
how to find the model files etc

### tests/sim/project/spectre
This is an example on how you can setup the model includes in spectre. Of
course, the current setup is empty, as the foundry PDKs are under NDA. 

### tests/sim/BFX1_CV
This directory contains an example of how you can run simulations with cicsim. If you go into
this directory, and type

``` sh
make
```

It should try to run a simulation. 

The directory contains a number of files

``` yaml
Makefile: cmake file to run the simulations
BFX1_CV_model.scs: Simplified model of a buffer that should run without a PDK
cicsim.yaml : This is the child config file. It contains the link to library,cell,view, and custom corners
dut.scs: Setup of the device under test
tran.scs: Main spectre file
tran.ocn: Ocean script to extract results after spectre simulation
tran.py: Python script to collate the ocean results, and anything else from the spectre simulation
tran.md: Results from simulation
```


# Commands

``` 
Usage: cicsim [OPTIONS] COMMAND [ARGS]...

  Custom IC Creator Simulator Tools

  This package provides helper scripts for simulating integrated circuits in
  Cadence Spectre

Options:
  --help  Show this message and exit.

Commands:
  netlist  Netlist from a cadence library.
  results  Summarize results of TESTBENCH
  run      Run a simulation of TESTBENCH
  simcell  Create a simulation directory for a cell
  simtb    Create a simulation directory for a testbench
```


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
