---
layout: page
title:  portreplace 
math: true
---

* TOC
{:toc }

## Command
```bash
cicsim --no-color portreplace --help
```

```bash
Usage: cicsim portreplace [OPTIONS] TESTBENCH SOURCE CELL

  Replace ${PORTS} and ${VPORTS} with the subcircuit ports of SOURCE CELL

Options:
  --help  Show this message and exit.

```


## Description

`portreplace` is a utility that reads a SPICE subcircuit definition and
replaces port placeholders in a testbench file.

This is useful when you want a testbench to automatically adapt to the ports
of the device under test, without manually listing them.

### Usage

```bash
cicsim portreplace TESTBENCH SOURCE CELL
```

Where:

- **TESTBENCH** is the SPICE file to modify (edited in-place)
- **SOURCE** is the SPICE file containing the subcircuit definition
- **CELL** is the name of the subcircuit to extract ports from

### Placeholders

The command looks for two placeholders in the testbench:

| Placeholder | Replaced with |
|-------------|---------------|
| `${PORTS}` | Space-separated list of port names |
| `${VPORTS}` | Space-separated list of `v(port)` voltage probes |

### Example

Given a subcircuit in `netlist.spice`:

```spice
.SUBCKT MY_AMP INP INN OUT VDD VSS
...
.ENDS
```

And a testbench `tran.spi`:

```spice
XDUT ${PORTS} MY_AMP
.save ${VPORTS}
```

Running:

```bash
cicsim portreplace tran.spi netlist.spice MY_AMP
```

Will modify `tran.spi` to:

```spice
XDUT INP INN OUT VDD VSS MY_AMP
.save v(INP) v(INN) v(OUT) v(VDD) v(VSS)
```
