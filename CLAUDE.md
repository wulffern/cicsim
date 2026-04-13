# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

**cicsim** is a Python CLI toolkit for controlling ngspice simulations and managing analog IC design flows. It runs corner simulations (temperature/voltage variations), parses ngspice binary `.raw` files, displays waveforms, and generates markdown summary reports with spec checking.

## Commands

```bash
# Install in development mode
python3 -m pip install -e .

# Run unit tests only
make unit_test
# or directly:
python3 -m unittest discover -s tests/unittests/ -p 'test_*.py' -v

# Run all tests (unit + ngspice integration in tests/sim/ngspice/basic/)
make test

# Build wheel/sdist
make build

# Serve docs locally (requires Docker)
make jstart
```

## Architecture

The CLI uses **Click** (`cicsim/cicsim.py`) as the entry point, routing each subcommand to a handler class in a `cmd*.py` module. All command classes inherit from `Command` (`command.py`), which sets up logging and common utilities.

**Data flow**: ngspice `.raw` binary → `ngraw.py` → pandas DataFrame → waveform viewer or results processor

**Key modules:**
- `cmdrunng.py` — ngspice simulation runner; handles corner expansion (temperature/voltage), multi-threaded execution via `--threads`, progress display via `rich`/`tqdm`
- `cmdwave_pg.py` — PyQtGraph waveform viewer (PySide6 backend, GPU-accelerated); the large one at ~2200 lines
- `cmdwave.py` — tkinter waveform viewer (lighter, no extra deps)
- `cmdresults.py` — parse rawfiles and display results as tables
- `cmdsummary.py` — generate markdown summaries with min/max spec checking
- `pivot.py` — YAML/JSON-driven data reshaping for multi-dimensional plot configurations
- `spec.py` — `SpecMinMax` class for specification validation and formatted output
- `ngraw.py` — binary `.raw` file parser (ngspice output format)
- `wavefiles.py` — multi-format I/O (CSV, TSV, Excel, JSON, Parquet, Feather, HDF5, Pickle)

**Dual waveform backends:** `cicsim wave --backend tk` (tkinter, built-in) vs `--backend pg` (pyqtgraph/PySide6). The `cicwave` entry point defaults to `--backend pg`.

**Simulation corners** are defined by combining temperature (`Tt`/`Tl`/`Th`) and voltage (`Vt`/`Vh`/`Vl`) variants. The runner expands these and invokes ngspice in parallel.

**Pivot/reshape pattern:** Multi-corner results are stored as flat tables and reshaped via pivot YAML specs (index/columns/values/conditions) for plotting.

## Testing

Unit tests live in `tests/unittests/`. Integration tests live under `tests/sim/ngspice/basic/` and require ngspice installed. Feature tests (wave, plot, results, summary, etc.) live in `tests/<feature>/` and each has its own `Makefile` with `make test` and `make docs` targets.

The CI container is `wulffern/aicex:26.04_latest` which has ngspice, PDK_ROOT, and other EDA tools available.
