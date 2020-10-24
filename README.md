
# Custom IC Creator Simulation Tools

 **This is a work in progress**

# Plan
- [x] Learn how to use setup.py
- [x] Add wrapper script for netlisting
- [x] Add wrapper sript for generating corners based on YAML files
- [x] Add script for simulating
- [ ] Add hooks for adding custom python output output parsing
- - Run a script per corner
- - Aggregate extracted parmeters and store in a dataframe
- [ ] Write the scripts as easy as I can, and understandable as I can.


# Requirements:

- Python > 3.6.6


# Getting started:


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

## Install this script
If you want to follow the latest and greatest
``` sh
mkdir pro
cd pro
git clone https://github.com/wulffern/cicsim
cd cicsim
pip3 install -r requirements.txt --user
pip3 install --no-deps -e --user .
```
## Get started with simulation
For now, it requires some manual work to get started. See tests/ for how cicsim
expects the simulation directory to be layed out.

### tests/cicsim.yaml
This is the main config file for cicsim, it sets up corners, links to cadence,
how to find the model files etc

### tests/IVX1_CV/cicsim.yaml
This is the child config file. The general rule is, one cell, one directory with
a cicsim.yaml file. The YAML file must contain the following:

``` yaml
cadence:
  library: <cadence library name>
  cell: <cadence cell name>
  view: <cadence view, usually schematic is the one you want>
```

The tests/IVX1_CV/cicsim.yaml example also shows how you can add corners to
include the spice file.

# CICSIK commands

## cicsim netlist

## cicsim run






