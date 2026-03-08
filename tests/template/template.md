---
layout: page
title:  template 
math: true
---

* TOC
{:toc }

## Command
<!--run_output:
run: cicsim --no-color template --help
-->

## Description

`template` creates a new IP directory from a YAML template file. It reads a
template that describes the directory structure, files to copy, files to create
from inline content, and commands to run.

### Usage

```bash
cicsim template TEMPLATE OPTIONS
```

Where:

- **TEMPLATE** is the path to the YAML template file
- **OPTIONS** is a YAML file with variables (must contain at least `library`)

Optionally specify the output directory name:

```bash
cicsim template TEMPLATE OPTIONS --dname my_output_dir
```

### The options file

The options YAML file provides variables that are substituted into the
template. It must define at least `library`:

```yaml
library: sun_pll_sky130nm
cell: SUN_PLL
description: "Phase-locked loop top level"
```

### Template format

The template is a YAML file with the following sections:

```yaml
dirs:
  - work
  - sim
  - doc

copy:
  - Makefile
  - cicsim.yaml

create:
  README.md: |
    # ${IP}
    ${description}

do:
  - git init
```

| Section | Description |
|---------|-------------|
| `dirs` | List of directories to create |
| `copy` | List of files to copy from the template directory |
| `create` | Dictionary of filename to content, created inline |
| `do` | List of shell commands to run after setup |

### Variable substitution

Before parsing the YAML, `cicsim` replaces `${NAME}` variables in the
following order:

1. `${CELL}` and `${cell}` — the cell name (upper/lower case)
2. `${IP}` and `${ip}` — the library/IP name (upper/lower case)
3. Any key from the options YAML file
4. Environment variables (e.g. `${USER}`, `${HOME}`)
