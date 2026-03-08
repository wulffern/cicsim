---
layout: page
title:  wave 
math: true
---

* TOC
{:toc }

## Command
<!--run_output:
run: cicsim --no-color wave --help
-->

## Description

`wave` is a simple waveform viewer built with tkinter. It can open ngspice raw
files and display waveforms interactively.

This is useful when you want a quick look at simulation results without leaving
the terminal. For scripted or publication-quality plots, see the
[plot](/cicsim/plot) command instead.

### Requirements

`wave` requires `tkinter`, which is not always installed by default.

- **macOS (brew):** `brew install python3-tk`
- **Ubuntu/Debian:** `apt install python3-tk`

### Usage

Open a single raw file:

```bash
cicsim wave output_tran/tran_SchTtVt.raw
```

Open multiple raw files:

```bash
cicsim wave output_tran/tran_SchTtVt.raw output_tran/tran_SchThVh.raw
```

Specify which signal to use as x-axis:

```bash
cicsim wave output_tran/tran_SchTtVt.raw --x time
```
