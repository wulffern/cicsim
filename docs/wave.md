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

  Keyboard shortcuts (both backends):
    A              Set cursor A at mouse position
    B              Set cursor B at mouse position
    Escape         Clear cursors
    F              Auto scale (fit all)
    R              Reload all waveforms
    L              Toggle legend
    Shift+Z        Zoom in
    Ctrl+Z         Zoom out
    Ctrl+O         Open raw file
    Ctrl+S         Save session
    Ctrl+P         Export to PDF
    Ctrl+N         New plot tab (pg backend)
    Ctrl+L         Set axis labels
    Ctrl+T         Add annotation
    Ctrl+Q         Quit
    Ctrl+Up        Increase line width
    Ctrl+Down      Decrease line width
    Ctrl+=         Increase font size
    Ctrl+-         Decrease font size

  Mouse (pg backend):
    Scroll             Zoom x-axis
    Shift+Scroll       Zoom y-axis
    Shift+Right-drag   Zoom x-axis
    Ctrl+Right-drag    Zoom y-axis
    Left-drag          Pan

  Browser (pg backend):
    Double-click   Add to plot
    Right-click    Context menu (plot, remove, style, analysis)
    Flat checkbox  Toggle hierarchy / flat list

  Backends:
    tk   Default. Uses tkinter + matplotlib. No extra dependencies.
    pg   Uses PySide6 + pyqtgraph. Install: pip install cicsim[pg]
         Features: hierarchical wave browser, automatic dual Y-axes
         (left/right by unit), GPU-accelerated rendering.

  Pivot:
    --pivot spec.yaml     Reshape data using pivot spec before viewing
    --pivot-info          Print unique values per pivot dimension and exit

  Session:
    --session plot.cicwave.yaml         Load saved session
    --export plot.pdf                   Export to file and exit (no GUI)
    --session s.yaml --export out.pdf   Restore session and export

Options:
  --x TEXT           Specify x-axis
  --backend [tk|pg]  GUI backend: tk (tkinter+matplotlib) or pg
                     (PySide6+pyqtgraph)
  --sheet TEXT       Sheet name for Excel files (default: first sheet)
  --pivot TEXT       Pivot spec file (YAML/JSON)
  --pivot-info       Print pivot dimensions and exit
  --session TEXT     Load session file (.cicwave.yaml)
  --export TEXT      Export plot to file (PDF/PNG/SVG) and exit
  --help             Show this message and exit.

```


## Description

`wave` is an interactive waveform viewer for SPICE simulation results and
tabular data files. It supports ngspice raw files and any file format that
pandas can read.

Two GUI backends are available:

| Backend | Flag | Dependencies | Install |
|---------|------|-------------|---------|
| tkinter + matplotlib | `--backend tk` (default) | `tkinter` | `brew install python3-tk` / `apt install python3-tk` |
| PySide6 + pyqtgraph | `--backend pg` | `PySide6`, `pyqtgraph` | `pip install cicsim[pg]` |

The **pg** backend offers a hierarchical wave browser (collapsible by instance
path), automatic dual Y-axes (left/right by unit), closeable tabs, analysis
functions, and GPU-accelerated rendering.

## Supported file formats

| Format | Extensions | Notes |
|--------|-----------|-------|
| ngspice raw | `.raw` | Binary raw files (transient, AC, DC) |
| CSV | `.csv` | Comma-separated values |
| TSV | `.tsv`, `.txt` | Tab-separated values |
| Excel | `.xlsx`, `.xls`, `.ods` | Use `--sheet` to pick sheet |
| Pickle | `.pkl`, `.pickle` | Pickled pandas DataFrames |
| JSON | `.json` | pandas-compatible JSON |
| Parquet | `.parquet` | Requires `pyarrow` or `fastparquet` |
| Feather | `.feather` | Requires `pyarrow` |
| HDF5 | `.h5`, `.hdf5` | Requires `tables` |
| HTML | `.html` | Reads first table on page |
| XML | `.xml` | Requires `lxml` |
| Fixed-width | `.fwf` | Fixed-width formatted text |
| Stata | `.stata`, `.dta` | Stata data files |
| SAS | `.sas7bdat` | SAS data files |
| SPSS | `.sav` | Requires `pyreadstat` |

String-based columns are supported as categorical axes (labels rotated 90
degrees).

## Standalone command

A standalone `cicwave` command is available that defaults to the pyqtgraph
backend. It is equivalent to `cicsim wave --backend pg`.

```bash
cicwave output_tran/tran_SchTtVt.raw
```

## Usage

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

Use the pyqtgraph backend:

```bash
cicsim wave --backend pg output_tran/tran_SchTtVt.raw
```

Open a CSV file:

```bash
cicwave data.csv
```

Open an Excel file with a specific sheet:

```bash
cicwave data.xlsx --sheet "Sheet2"
```

## Examples

There is example test data in `tests/wave`. Navigate to that directory.

### Single wave

Plot a single voltage signal:

```bash
cicwave --session session_single.cicwave.yaml --export wave_single.svg
```

![](/cicsim/assets/wave_single.svg)
### Multiple waves

Plot multiple signals on the same axes:

```bash
cicwave --session session_multi.cicwave.yaml --export wave_multi.svg
```

![](/cicsim/assets/wave_multi.svg)
### Dual Y-axes

When voltage and current signals are plotted together, the pg backend
automatically assigns them to separate Y-axes based on their unit:

```bash
cicwave --session session_dual.cicwave.yaml --export wave_dual.svg
```

![](/cicsim/assets/wave_dual.svg)
## Keyboard shortcuts

### File

| Key | Action |
|-----|--------|
| Ctrl+O | Open file |
| Ctrl+S | Save session (pg) |
| Ctrl+P | Export to PDF/PNG/SVG |
| Ctrl+Q | Quit |

### Edit

| Key | Action |
|-----|--------|
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

| Key | Action |
|-----|--------|
| A | Set cursor A at mouse position |
| B | Set cursor B at mouse position |
| Escape | Clear cursors |

When two cursors are placed the readout panel shows ΔX, per-signal ΔY,
slope, and derivative values at both cursor positions.

### View

| Key | Action |
|-----|--------|
| L | Toggle legend |
| Ctrl+Up | Increase line width |
| Ctrl+Down | Decrease line width |
| Ctrl+= | Increase font size |
| Ctrl+- | Decrease font size |

## Mouse controls (pg backend)

| Action | Effect |
|--------|--------|
| Scroll | Zoom x-axis |
| Shift+Scroll | Zoom y-axis |
| Shift+Right-drag | Zoom x-axis |
| Ctrl+Right-drag | Zoom y-axis |
| Left-drag | Pan |
| Click cursor line | Drag to reposition |

## Wave browser (pg backend)

- **Double-click** a wave to add it to the plot
- **Right-click** a wave to open the context menu:
  - Plot / Remove from plot
  - Change plot style (Lines, Markers, Lines+Markers, Steps)
  - FFT / PSD (spectral density in dB)
  - Histogram (distribution with Gaussian fit, mean/sigma)
  - Differentiate (numerical dy/dx)
  - X vs Y (parametric plot with regex signal picker)
- Signal names with dotted hierarchy (e.g. `v(xdut.x1.out)`) are shown as a
  collapsible tree organized by instance path
- Use the **Flat** checkbox to switch to a flat list view
- Use the **regex filter** to search for signals
- Plotted waves are colored in the browser to match their plot line

## Sessions (pg backend)

Save the current viewer state (loaded files, plotted waves, axis labels,
annotations) to a YAML file and restore it later.

Save via menu: **File → Save Session (Ctrl+S)**

Load from the command line:

```bash
cicwave --session mysession.cicwave.yaml
```

Export a session to PDF without opening the GUI:

```bash
cicwave --session mysession.cicwave.yaml --export plot.pdf
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
