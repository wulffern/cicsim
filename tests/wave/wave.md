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

## Keyboard shortcuts

| Key | Action |
|-----|--------|
| A | Set cursor A at mouse position |
| B | Set cursor B at mouse position |
| Escape | Clear cursors |
| F | Auto scale (fit all) |
| R | Reload all waveforms |
| L | Toggle legend |
| Ctrl+O | Open file |
| Ctrl+P | Export to PDF |
| Ctrl+N | New plot tab (pg) |
| Ctrl+W | Close current tab (pg) |
| Ctrl+Q | Quit |

## Mouse controls (pg backend)

| Action | Effect |
|--------|--------|
| Scroll | Zoom x-axis |
| Shift+Scroll | Zoom y-axis |
| Shift+Right-drag | Zoom x-axis |
| Ctrl+Right-drag | Zoom y-axis |
| Left-drag | Pan |

## Wave browser (pg backend)

- **Double-click** a wave to add it to the plot
- **Right-click** a wave to open the context menu:
  - Plot / Remove from plot
  - FFT / PSD (spectral density in dB)
  - Histogram (distribution with Gaussian fit, mean/sigma)
  - Differentiate (numerical dy/dx)
  - X vs Y (parametric plot with regex signal picker)
- Signal names with dotted hierarchy (e.g. `v(xdut.x1.out)`) are shown as a
  collapsible tree organized by instance path
- Use the **Flat** checkbox to switch to a flat list view
- Plotted waves are colored in the browser to match their plot line

## Cursor readout (pg backend)

When cursors A and/or B are placed, the readout panel shows:

- X position of each cursor
- Delta X and 1/Delta X (frequency)
- Y value at each cursor per wave
- Delta Y between cursors per wave
- Slope between cursors (Delta Y / Delta X) per wave
- Gradient (dy/dx) at each cursor per wave

## Closeable tabs (pg backend)

Each plot or analysis tab has a close button. Use Ctrl+W to close the current
tab. If all tabs are closed, a fresh plot tab is created automatically.
