---
layout: page
title:  wave 
math: true
---

* TOC
{:toc }

## Command
```bash
cicsim --no-color wave --help
```

```bash
Usage: cicsim wave [OPTIONS] [FILES]...

  Open waveform viewer.

  Interactive waveform viewer for SPICE simulation results (.raw files).

Options:
  --x TEXT                     Specify x-axis
  --backend [tk|pg]            GUI backend: tk (tkinter+matplotlib) or pg
                               (PySide6+pyqtgraph)
  --sheet TEXT                 Sheet name for Excel files (default: first sheet)
  --pivot TEXT                 Pivot spec file (YAML/JSON)
  --pivot-info                 Print pivot dimensions and exit
  --session TEXT               Load session file (.cicwave.yaml)
  --export TEXT                Export plot to file (PDF/PNG/SVG) and exit
  --help                       Show this message and exit.

```

There is also a standalone command `cicwave` which defaults to the `pg`
backend:

```bash
cicwave [FILES]...
```

## Description

`wave` is an interactive waveform viewer for inspecting simulation results
directly from the terminal. It supports two GUI backends and a wide range of
file formats.

For scripted or publication-quality plots, see the [plot](/cicsim/plot) command
instead.

## Backends

| Backend | Toolkit | Install | Notes |
|---------|---------|---------|-------|
| `tk` (default for `cicsim wave`) | tkinter + matplotlib | `brew install python3-tk` (macOS) or `apt install python3-tk` (Ubuntu) | No extra Python packages needed |
| `pg` (default for `cicwave`) | PySide6 + pyqtgraph | `pip install cicsim[pg]` | Hierarchical wave browser, automatic dual Y-axes, GPU-accelerated rendering, sessions, analysis functions |

Select a backend explicitly:

```bash
cicsim wave --backend pg output_tran/tran_SchTtVt.raw
```

## Supported file formats

| Extension | Format |
|-----------|--------|
| `.raw` | ngspice / SPICE raw files |
| `.csv` | Comma-separated values |
| `.tsv`, `.txt` | Tab-separated values |
| `.xlsx`, `.xls`, `.ods` | Excel / OpenDocument spreadsheets |
| `.json` | JSON (pandas-compatible) |
| `.parquet` | Apache Parquet |
| `.feather` | Apache Feather / Arrow IPC |
| `.h5`, `.hdf5` | HDF5 |
| `.pkl`, `.pickle` | Python pickle |

Use `--sheet` to select a specific sheet when opening Excel files:

```bash
cicsim wave data.xlsx --sheet "Sheet2"
```

## Usage

Open a single raw file:

```bash
cicsim wave output_tran/tran_SchTtVt.raw
```

Open multiple files:

```bash
cicsim wave output_tran/tran_SchTtVt.raw output_tran/tran_SchThVh.raw
```

Specify which signal to use as x-axis:

```bash
cicsim wave output_tran/tran_SchTtVt.raw --x time
```

## Keyboard shortcuts

### File

| Shortcut | Action |
|----------|--------|
| Ctrl+O | Open file |
| Ctrl+S | Save session (pg) |
| Ctrl+P | Export to PDF/PNG/SVG |
| Ctrl+Q | Quit |

### Edit

| Shortcut | Action |
|----------|--------|
| Ctrl+N | New plot tab (pg) |
| Ctrl+W | Close current tab (pg) |
| Ctrl+A | Add axis (tk) |
| Ctrl+L | Set axis labels (pg) |
| Ctrl+T | Add annotation (pg) |
| R | Reload all waveforms |
| F | Auto scale (fit all) |
| Shift+Z | Zoom in |
| Ctrl+Z | Zoom out |
| Delete | Remove selected wave (tk) |

### Cursors

| Shortcut | Action |
|----------|--------|
| A | Set cursor A at mouse position |
| B | Set cursor B at mouse position |
| Escape | Clear cursors |

When two cursors are placed the readout panel shows ΔX, per-signal ΔY, and
derivative values at both cursor positions.

### View

| Shortcut | Action |
|----------|--------|
| L | Toggle legend |
| Ctrl+Up | Increase line width |
| Ctrl+Down | Decrease line width |
| Ctrl+= | Increase font size |
| Ctrl+- | Decrease font size |

### Mouse (pg backend)

| Action | Effect |
|--------|--------|
| Scroll | Zoom x-axis |
| Shift+Scroll | Zoom y-axis |
| Left-drag | Pan |
| Shift+Right-drag | Zoom x-axis |
| Ctrl+Right-drag | Zoom y-axis |
| Click cursor line | Drag to reposition |

### Browser (pg backend)

| Action | Effect |
|--------|--------|
| Double-click wave | Add to current plot |
| Right-click wave | Context menu (plot, remove, change style, analysis) |
| Flat checkbox | Toggle flat list vs hierarchical grouping |
| Regex filter | Filter waves by regular expression |

## Plot styles (pg backend)

The style dropdown in the browser panel sets the default style for newly
plotted waves. You can also set the style per wave via the right-click context
menu.

| Style | Description |
|-------|-------------|
| Lines | Continuous line (default) |
| Markers | Scatter plot with circle markers |
| Lines+Markers | Line with markers at data points |
| Steps | Step plot (sample-and-hold style) |

## Analysis functions (pg backend)

Right-click a wave in the browser to access these analysis functions. Each
opens in a new tab.

| Analysis | Description |
|----------|-------------|
| FFT / PSD | Power spectral density (log frequency, dB scale) |
| Histogram | Distribution histogram with Gaussian fit overlay |
| Differentiate (dy/dx) | Numerical derivative |
| X vs Y | Parametric plot of one signal against another |

## Dual Y-axes (pg backend)

The pg backend automatically assigns waves to left or right Y-axes based on
their unit. For example, voltage signals (`v(...)`) use the left axis and
current signals (`i(...)`) use the right axis.

## Sessions (pg backend)

Save the current viewer state (loaded files, plotted waves, axis labels,
annotations) to a YAML file and restore it later.

Save via menu: **File → Save Session (Ctrl+S)**

Load from the command line:

```bash
cicsim wave --session mysession.cicwave.yaml
```

Export a session to PDF without opening the GUI:

```bash
cicsim wave --session mysession.cicwave.yaml --export plot.pdf
```

## Pivot

Reshape tabular data before viewing using a pivot spec file:

```bash
cicsim wave results.csv --pivot spec.yaml
```

Inspect the available pivot dimensions first:

```bash
cicsim wave results.csv --pivot spec.yaml --pivot-info
```
