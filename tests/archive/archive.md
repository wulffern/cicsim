---
layout: page
title:  archive 
math: true
---

* TOC
{:toc }

## Command
<!--run_output:
run: cicsim --no-color archive --help
-->

## Description

`archive` saves simulation results to a timestamped directory for safekeeping.
This is useful when you want to preserve a set of results before re-running
simulations, or for record keeping.

### Usage

```bash
cicsim archive NAME RUNFILES...
```

Where:

- **NAME** is a descriptive label for the archive (spaces are replaced with
  underscores)
- **RUNFILES** are one or more `.run` files produced by the `run` command

### Example

Save the typical and Monte-Carlo results:

```bash
cicsim archive "Tapeout v1" tran_Sch_typical.run tran_Sch_mc.run
```

This creates a directory like:

```
archive/2025-03-08_14-30_Tapeout_v1/
```

All output files referenced by the run files (`.yaml`, `.raw`, `.log`, etc.)
are copied into the archive directory, along with updated run files that point
to the archived copies.

### When to archive

- Before re-running simulations with updated parameters
- After a successful tapeout milestone
- When sharing results with colleagues
