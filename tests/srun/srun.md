---
layout: page
title:  srun 
math: true
---

* TOC
{:toc }

## Command
<!--run_output:
run: cicsim --no-color srun --help
-->

## Description

`srun` runs a Spectre simulation. It works similarly to the `run` command but
targets the Cadence Spectre simulator instead of ngspice.

### Requirements

- Cadence Spectre must be installed and available in your `PATH`
- An optional OCEAN script (`.ocn`) can be used for post-processing

### Corner handling

Corners work the same way as for `run`. The `cicsim.yaml` file defines the
mapping from corner names to Spectre include statements:

```yaml
corner:
  Sch: 'include "../MYDESIGN_schematic.scs"'
  Lay: 'include "../MYDESIGN_layout.scs"'
  Tt: 'include "/path/to/models" section=tt'
```

### Usage

Run a typical corner:

```bash
cicsim srun tran Sch Tt Vt
```

Generate the spice file without running:

```bash
cicsim srun tran Sch Tt Vt --no-run
```

Skip OCEAN post-processing:

```bash
cicsim srun tran Sch Tt Vt --no-ocn
```

### OCEAN post-processing

If a `<testbench>.ocn` file exists (e.g. `tran.ocn`), `srun` will execute it
with OCEAN after the simulation completes. This is useful for extracting
measurements from Spectre PSF results.

Inside the OCEAN script, `cicsim` provides the variable `cicResultsDir` which
points to the PSF results directory for the current corner.
