---
layout: page
title:  summary 
math: true
---

* TOC
{:toc }

## Command
<!--run_output:
run: cicsim --no-color summary --help
-->

## Description

`summary` generates a combined markdown summary from multiple simulation
result sets. This is useful for producing a single document that covers all
testbenches in a design.

### The summary.yaml file

The `summary` command reads a YAML configuration file (default
`summary.yaml`) that defines which simulations and results to include.

An example `summary.yaml`:

```yaml
description: "Simulation summary for SUN_PLL"

simulations:
  tran:
    name: "Transient analysis"
    description: "Transient simulation of the PLL"
    data:
      - name: "Typical"
        src: "results/tran_Sch_typical"
        method: "typ"
      - name: "Temp/Voltage"
        src: "results/tran_Sch_tempvall"
        method: "minmax"
      - name: "Monte-Carlo"
        src: "results/tran_Sch_mc"
        method: "3std"
```

### Data methods

The `method` field controls how the results are summarized:

| Method | Description |
|--------|-------------|
| `typ` | Report the median value |
| `minmax` | Report min, median, and max across all corners |
| `std` | Report mean +/- 1 standard deviation |
| `3std` | Report mean +/- 3 standard deviations (for Monte-Carlo) |

### Usage

Generate with default filenames:

```bash
cicsim summary
```

Specify input and output:

```bash
cicsim summary --filename summary.yaml --output README.md
```

The output is a markdown file with tables showing each parameter against its
specification, with values color-coded for pass/fail.
