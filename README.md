
# Custom IC Creator Simulation Tools

[![tests](https://github.com/wulffern/cicsim/actions/workflows/main.yml/badge.svg)](https://github.com/wulffern/cicsim/actions/workflows/main.yml)

# Caution
If you're looking for the cicsim that controlled spectre, then look in the
cadence branch. From 2022-10-14 I decided to go all in on open source tools like
ngspice, and thus discontinued support for spectre.

# Why
This is a script package I use to control ngspice, it can
- Run corner simulations
- Create IPs (used in  [wulffern/aicex](https://github.com/wulffern/aicex) )
- Create simulation directories

# Changelog

| Version | Status                      | Comment                 |
|:--------|:----------------------------|:------------------------|
| 0.0.1   | :white_check_mark:          | First version of cicsim |
| 0.0.3   | All in on open source tools |                         |
| 0.1.2   | First version on pipy      |                         |

# Install this module
If you want to follow the latest and greatest
``` sh
git clone https://github.com/wulffern/cicsim
cd cicsim
python3 -m pip install --user -e . 
```

If you want the latest stable

``` bash
python3 -m pip install cicpy
```

# Get started with simulation
Head over to [Open source analog integrated circuit flow on Skywater
130nm](https://analogicus.com/rply_ex0_sky130nm/tutorial) to see cicsim in action.

# Commands

``` 
Usage: cicsim [OPTIONS] COMMAND [ARGS]...

  Custom IC Creator Simulator Tools

  This package provides helper scripts for simulating integrated circuits

Options:
  --help  Show this message and exit.

Commands:
  ip           make ip from a YAML template file
  plot         Plot from rawfile
  portreplace  Replace ${PORTS} and ${VPORTS} with the subcircuit ports...
  results      Results of single runfile
  run          Run a ngspice simulation of TESTBENCH
  simcell      Create a ngspice simulation directory for a Cell
  summary      Generate simulation summary for results
```
