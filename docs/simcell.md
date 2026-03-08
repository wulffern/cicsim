---
layout: page
title:  simcell 
math: true
---

* TOC
{:toc }

## Command
```bash
cicsim --no-color simcell --help
```

```bash
Usage: cicsim simcell [OPTIONS] LIBRARY CELL TEMPLATE

  Create a ngspice simulation directory for a Cell

Options:
  --help  Show this message and exit.

```


## Description

`simcell` creates a new ngspice simulation directory from a template for a
specific cell. It is a convenience wrapper around the `template` command,
tailored for creating simulation directories for individual cells.

### Usage

```bash
cicsim simcell LIBRARY CELL TEMPLATE
```

Where:

- **LIBRARY** is the design library name
- **CELL** is the cell name to simulate
- **TEMPLATE** is the path to a YAML template file

### Example

```bash
cicsim simcell sun_pll_sky130nm SUN_PLL_BUF sim_template.yaml
```

This will:

1. Create a directory named `SUN_PLL_BUF`
2. Generate a `cicsim.yaml` configuration file
3. Process the template to create testbench files and a Makefile
4. Replace `${CELL}` and `${IP}` variables in the template with the actual
   cell and library names

### Templates

The template file is a YAML file that describes what directories to create,
which files to copy, and what commands to run. See the
[template](/cicsim/template) command for the full template format.
