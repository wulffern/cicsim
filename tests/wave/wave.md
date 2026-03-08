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

`wave` is an interactive waveform viewer for SPICE simulation results. It can
open ngspice raw files and display waveforms with cursors, measurements, and
engineering notation.

Two GUI backends are available:

| Backend | Flag | Dependencies | Install |
|---------|------|-------------|---------|
| tkinter + matplotlib | `--backend tk` (default) | `tkinter` | `brew install python3-tk` / `apt install python3-tk` |
| PySide6 + pyqtgraph | `--backend pg` | `PySide6`, `pyqtgraph` | `pip install cicsim[pg]` |

The **pg** backend offers a hierarchical wave browser (collapsible by instance
path), automatic dual Y-axes (left/right by unit), and GPU-accelerated
rendering.

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

## Keyboard shortcuts

| Key | Action |
|-----|--------|
| A | Set cursor A at mouse position |
| B | Set cursor B at mouse position |
| Escape | Clear cursors |
| F | Auto scale (fit all) |
| R | Reload all waveforms |
| L | Toggle legend |
| Ctrl+O | Open raw file |
| Ctrl+P | Export to PDF |
| Ctrl+N | New plot tab (pg) |
| Ctrl+Q | Quit |

## Mouse controls (pg backend)

| Action | Effect |
|--------|--------|
| Scroll | Zoom x-axis |
| Shift+Scroll | Zoom y-axis |
| Shift+Right-drag | Zoom x-axis |
| Ctrl+Right-drag | Zoom y-axis |
| Left-drag | Pan |
| Right-click | Context menu |

## Wave browser (pg backend)

- **Click** a wave to add it to the plot
- **Right-click** a wave to remove it from the plot
- Signal names with dotted hierarchy (e.g. `v(xdut.x1.out)`) are shown as a
  collapsible tree organized by instance path
- Use the **Flat** checkbox to switch to a flat list view
- Plotted waves are colored in the browser to match their plot line
