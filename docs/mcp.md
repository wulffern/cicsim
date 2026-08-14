---
layout: page
title:  mcp
math: true
---

* TOC
{:toc }

## Description

`cicsim-mcp` is an [MCP](https://modelcontextprotocol.io) server that
exposes cicsim's simulation bookkeeping as tools an agent can call
directly. It answers the questions that otherwise cost a waveform
viewer session or a hexdump: what vectors does this `.raw` actually
contain, did this node ever move, which measurements are out of spec
and in which corners, and are these results still valid for the netlist
they were run against.

Every tool is read-only. Nothing here launches ngspice — `cicsim run`
is long and corner-expanded, and belongs in a Makefile where its
progress is visible, not behind a tool call that blocks until it
finishes.

It requires the `mcp` extra, and Python 3.10+ (the
[MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)'s
own requirement — the rest of cicsim supports 3.8+):

```bash
pip install "cicsim[mcp]"
```

Both SDK generations work: 1.x (`FastMCP`) and 2.x, which renamed that
class to `MCPServer` and moved it out of `mcp.server.fastmcp`.

## Running it

```bash
cicsim-mcp
```

This speaks MCP over stdio, so it's normally launched by an MCP client
rather than run directly. For Claude Code:

```bash
claude mcp add cicsim -- cicsim-mcp
```

## Tools

### raw_info

Lists the vectors present in an ngspice `.raw` file, with the plot
metadata and the span of the x axis — the latter tells you whether the
run actually reached the time a measurement asks about. Takes an
optional case-insensitive regex to filter the names.

Read this when a measurement fails with `no such vector as v(x.y)`. A
probe path is only valid for the view it was written for. An extracted
(`Lay`) netlist is flat, so the layout's cell hierarchy ends up inside
the node *name*:

```
schematic:  v(xdut.vc)
extracted:  v(xdut.xbias.vc)
```

if the layout groups blocks into a wrapper cell the schematic does not
have. LVS passing does not tell you the internal names match — only the
ports are compared — so this shows up first as a failed measurement.

### raw_signals

Reports min/max/mean plus first and last value for chosen vectors, and
optionally the value at a given point on the x axis. A node whose min
equals its max never switched, which is usually what you want to know
before opening a viewer at all.

### results

Returns the measurements of a `.run` with their spec verdict, scaled
into the units the spec is written in. Specs come from
`<testbench>.yaml`, so the verdict matches what `cicsim summary` puts
in the README. Pass `only_fails` on a wide corner sweep to get just the
violations and the corners they occurred in.

### sim_status

Lists the runs in a simulation directory and reports how many of each
run's corners are stale, and which files changed.

Staleness is decided by re-hashing the dependencies cicsim recorded in
each corner's `.sha` — the same comparison `cicsim run` uses to decide
whether to re-simulate — so "stale" means those corners really would
re-run. Modification times are not usable for this: the design flow
regenerates the netlist on every invocation, so its mtime always moves
and an mtime test calls everything stale.

One false positive is worth knowing about. A magic parasitic extraction
(`<cell>_lpe.spi`) is not byte-stable: re-extracting an unchanged layout
emits the same capacitors, with the same values and the same nodes, in a
different order and under different `C<n>` names. The hash moves, the
circuit does not. So a `Lay` run reported stale *only* on a `_lpe.spi`
is usually still valid — check with something like

```bash
diff <(grep '^C' a.spi | sed 's/^C[0-9]* //' | sort) \
     <(grep '^C' b.spi | sed 's/^C[0-9]* //' | sort)
```

before spending the runtime on a re-simulation.

### corners

Lists the corner names available to `cicsim run`, read from
`cicsim.yaml` here and in the parent directory, grouped by the leading
letter of the naming convention (K process, T temperature, V supply).
