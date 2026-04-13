---
layout: page
title:  results 
math: true
---

* TOC
{:toc }

## Command
```bash
cicsim --no-color results --help
```

```bash
Usage: cicsim results [OPTIONS] RUNFILE

  Results of single runfile

Options:
  --help  Show this message and exit.

```


## Description

`results` reads a `.run` file produced by the `run` command and collects all
the measurement YAML files referenced in it. The measurements are printed as a
formatted table in the terminal, and if a specification file
(`<testbench>.yaml`) exists, the results are checked against the spec.

### The .run file

When `cicsim run` finishes, it writes a `.run` file that lists the output
paths for every corner that was simulated. For example,
`tran_Sch_typical.run` might contain:

```
output_tran/tran_SchTtVt
```

Each line corresponds to a set of output files (`.yaml`, `.raw`, `.log`, etc.)
in the output directory.

### Usage

```bash
cicsim results tran_Sch_typical.run
```

This will:

1. Read each YAML file listed in the run file
2. Print a summary table of all measurements in the terminal
3. If `tran.yaml` (the spec file) exists, check results against min/typ/max
   and write HTML and CSV reports to the `results/` directory

### Terminal table

The terminal table is rendered using [rich](https://github.com/Textualize/rich)
and adapts to the width of your terminal.

- Column headers show the unit in square brackets when defined in the spec,
  e.g. `ug [MHz]` or `i(v1) [uA]`
- Values are scaled by the spec scale factor before display, so they match the
  unit shown in the header
- If the table is wider than the terminal it is **folded** into multiple
  sub-tables, each repeating the `name` and `type` columns for context

### Specification checking

If a `<testbench>.yaml` specification file is present (e.g. `tran.yaml`), the
`results` command highlights values in the terminal table and writes colored
HTML and CSV reports to the `results/` directory.

Terminal color coding:

- **Green**: within spec
- **Bold red**: out of spec

HTML report color coding:

- **Green**: within spec
- **Orange**: near the spec boundary (within 5%)
- **Red**: out of spec
