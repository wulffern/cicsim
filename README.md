
# Custom IC Creator Simulation Tools


[![tests](https://github.com/wulffern/cicsim/actions/workflows/main.yml/badge.svg)](https://github.com/wulffern/cicsim/actions/workflows/main.yml)

# Caution
If you're looking for the cicsim that controlled spectre, then look in the
cadence branch. From 2022-10-14 I decided to go all in on open source tools like
ngspice, and thus discontinued support for spectre

# Why
This is a script package I use to control ngspice, it can
- Run corner simulations
- Create IPs (used in wulffern/aicex)
- Create simulation directories

# Changelog

| Version | Status                      | Comment                 |
|:--------|:----------------------------|:------------------------|
| 0.0.3   | All in on open source tools |                         |
| 0.0.2   | to be released              | Probably bugfixes       |
| 0.0.1   | :white_check_mark:          | First version of cicsim |

# Install this module
If you want to follow the latest and greatest
``` sh
mkdir pro
cd pro
git clone https://github.com/wulffern/cicsim
cd cicsim
python3 -m pip install -r requirements.txt --user
python3 -m pip install --no-deps -e . --user
```
# Get started with simulation
Head over to [wulffern/aicex](https://github.com/wulffern/aicex) to see how it works

# Commands

``` 
Usage: cicsim [OPTIONS] COMMAND [ARGS]...

  Custom IC Creator Simulator Tools

  This package provides helper scripts for simulating integrated circuits in
  ngspice

Options:
  --help  Show this message and exit.

Commands:
  run      Run a simulation of TESTBENCH
  simcell  Create a simulation directory for a cell
```

## Know what python you're running

Python is great, however, python exists in many different versions, and you can
never trust that the right version is installed on the system that you're going
to use. As such, always know what you're running.

### Option 1: Build yourself
If you don't control the system, then you can still install locally
https://randomwalk.in/python/2019/10/27/Install-Python-copy.html

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
