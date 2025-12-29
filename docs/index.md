---
layout: home
---

cicsim is a collection of scripts that I use to simplify my life when it comes to
analog simulation.

cicsim is short for Custom Integrated Circuit Simulation (or Carsten's
Integrated Circuit Simulation). 

I pronounce `cicsim` as C I C SIM, while my students sometimes call it 'sick-sim'.

The commands are 

```bash
cicsim --no-color --help
```

```bash
Usage: cicsim [OPTIONS] COMMAND [ARGS]...

  Custom Integrated Circuit Simulation

  This package provides helper scripts for simulating integrated circuits

  Check website for more information : http://analogicus.com/cicsim/

Options:
  --color / --no-color  Enable/Disable color output
  --help                Show this message and exit.

Commands:
  archive      Save a cicisim run output
  plot         Plot from rawfile
  portreplace  Replace ${PORTS} and ${VPORTS} with the subcircuit ports...
  results      Results of single runfile
  run          Run a ngspice simulation of TESTBENCH
  simcell      Create a ngspice simulation directory for a Cell
  srun         Run a spectre simulation of TESTBENCH
  summary      Generate simulation summary for results
  template     Run an IP template with <options> YAML file
  wave         Open waveform viewer

```



## Install stable version 

I sometimes release a version to pypi, so you can do 

```
python3 -m pip install cicsim
```

## Install latest and greatest 

```
git clone https://github.com/wulffern/cicsim
cd cicsim
python3 -m pip install --user -e .
```


## Other sources and demos 

- [Tutorial on analog simulation and
cicsim](https://analogicus.com/aic2026/sky130nm_tutorial)

- [Advanced Integrated Circuits Examples](https://analogicus.com/aicex/)
