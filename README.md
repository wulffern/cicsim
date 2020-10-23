
# Custom IC Creator Simulation Tools

 **This is a work in progress**

# Plan

cicsim/
 psd-utils   # Use submodule to get psd
 cics.py     # Run spectre and generate netlist based on cics.yaml files
 cicxdut.py  # Take a spice netlist, and generate xdut.scs
 setup.py    #


- Learn how to use setup.py
- Write the scripts as easy as I can, and understandable as I can.


# Requirements:

- Python > 3.6.6
- 


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

## Option 3: Set version
Sometimes multiple versions can be installed, if so, then you can add the
following lines to your .bashrc file
  
  alias python3='/usr/local/bin/python3.8'
  alias pip3='/usr/local/bin/pip3.8'

