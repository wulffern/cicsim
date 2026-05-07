#!/usr/bin/env python3
######################################################################
##        Copyright (c) 2020 Carsten Wulff Software, Norway
## ###################################################################
## Created       : wulff at 2020-10-23
## ###################################################################
##  The MIT License (MIT)
##
##  Permission is hereby granted, free of charge, to any person obtaining a copy
##  of this software and associated documentation files (the "Software"), to deal
##  in the Software without restriction, including without limitation the rights
##  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
##  copies of the Software, and to permit persons to whom the Software is
##  furnished to do so, subject to the following conditions:
##
##  The above copyright notice and this permission notice shall be included in all
##  copies or substantial portions of the Software.
##
##  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
##  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
##  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
##  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
##  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
##  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
##  SOFTWARE.
##
######################################################################

import yaml
import click
import sys
import os
import glob as _glob
import cicsim as cs
from cicsim.command import setup_logging
import importlib
import matplotlib.pyplot as plt


#- Few words on the coding in this file:
# 1. I use click, its really nice, just google "python click"
# 2. I try the design pattern "one command, one file in cmd* that inherits command.py".
#    That's why it's instanciating a class below and doing <obj>.run()


@click.group()
@click.option("--color/--no-color",default=True,help="Enable/Disable color output")
@click.pass_context
def cli(ctx,color):
    """Custom Integrated Circuit Simulation

    This package provides helper scripts for simulating integrated circuits

    Check website for more information : http://analogicus.com/cicsim/

    """
    setup_logging(color=color)
    ctx.obj = dict()

@cli.command()
@click.argument("testbench")
@click.argument("corner",nargs=-1)
@click.option("--run/--no-run", default=True, help="Run simulator")
@click.option("--count", default=1, help="Run each corner count times, useful for Monte-Carlo")
@click.option("--name", default=None, help="Control name of run file")
@click.option("--ignore/--no-ignore", default=False,is_flag=True, help="Ignore error checks")
@click.option("--sha/--no-sha", default=None, help="Check SHA of input files")
@click.option("--replace",default=None, help="YAML file with replacements for netlist")
@click.option("--threads", default=1, help="Number of parallel simulation threads")
@click.option("--progress/--no-progress", default=False, help="Show progress bar instead of interleaved logs")
@click.option("--timeout", default=None, type=int, help="Timeout in seconds per simulation (default: no limit)")
@click.pass_context
def run(ctx,testbench,run,corner,count,name,ignore,sha,replace,threads,progress,timeout):
    """Run a ngspice simulation of TESTBENCH
    """

    r = cs.CmdRunNg(testbench,run,corner,name,count,sha,threads=threads,progress=progress,timeout=timeout)
    r.loadReplacements(replace)

    r.run(ignore)

@cli.command()
@click.argument("name")
@click.argument("runfiles",nargs=-1)
@click.pass_context
def archive(ctx,name,runfiles):
    """Save a cicisim run output
    """

    r = cs.CmdArchive(name)

    r.archiveAll(runfiles)

@cli.command()
@click.argument("files",nargs=-1)
@click.option("--glob","globs",multiple=True,
              help="Glob pattern (repeatable). Supports ** for recursion. "
                   "Useful on shells like PowerShell that don't auto-expand.")
@click.option("--x", default=None,
              help="X-axis column; else CICWAVE_X / CICSIM_X_AXIS; else saved default (pg); else auto")
@click.option("--backend",default="tk",type=click.Choice(["tk","pg"]),
              help="GUI backend: tk (tkinter+matplotlib) or pg (PySide6+pyqtgraph)")
@click.option("--sheet",default=None,help="Sheet name for Excel files (default: first sheet)")
@click.option("--pivot",default=None,help="Pivot spec file (YAML/JSON)")
@click.option("--pivot-info",is_flag=True,default=False,help="Print pivot dimensions and exit")
@click.option("--session",default=None,help="Load session file (.cicwave.yaml)")
@click.option("--export",default=None,help="Export plot to file (PDF/PNG/SVG) and exit")
def wave(files,globs,x,backend,sheet,pivot,pivot_info,session,export):
    """Open waveform viewer.

    Interactive waveform viewer for SPICE simulation results (.raw files).

    \b
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

    \b
    Mouse (pg backend):
      Scroll             Zoom x-axis
      Shift+Scroll       Zoom y-axis
      Right-drag         Zoom to rubber-band rectangle
      Shift+Right-drag   Pan x-axis
      Ctrl+Right-drag    Pan y-axis
      Left-drag          Pan

    \b
    Browser (pg backend):
      Double-click   Add to plot
      Right-click    Context menu (plot, remove, style, analysis)
      Flat checkbox  Toggle hierarchy / flat list

    \b
    Backends:
      tk   Default. Uses tkinter + matplotlib. No extra dependencies.
      pg   Uses PySide6 + pyqtgraph. Install: pip install cicsim[pg]
           Features: hierarchical wave browser, automatic dual Y-axes
           (left/right by unit), GPU-accelerated rendering.

    \b
    Pivot:
      --pivot spec.yaml     Reshape data using pivot spec before viewing
      --pivot-info          Print unique values per pivot dimension and exit

    \b
    Session:
      --session plot.cicwave.yaml         Load saved session
      --export plot.pdf                   Export to file and exit (no GUI)
      --session s.yaml --export out.pdf   Restore session and export

    \b
    Globs:
      --glob 'data/*.csv'             Repeatable, supports ** for recursion
      --glob '**/*.raw'               Useful on PowerShell which doesn't
                                       auto-expand patterns
    """
    files = _expand_glob_patterns(files, globs)
    _run_wave(files, x, backend, sheet, pivot, pivot_info,
              session_path=session, export_path=export)


def _resolve_wave_x_from_cli_env(cli_x):
    """Apply --x, else CICWAVE_X / CICSIM_X_AXIS environment variables."""
    if cli_x:
        return cli_x
    v = os.environ.get("CICWAVE_X") or os.environ.get("CICSIM_X_AXIS")
    if v and str(v).strip():
        return str(v).strip()
    return None


def _expand_glob_patterns(files, patterns):
    """Merge positional ``files`` with files matched by --glob ``patterns``.

    Each pattern is expanded with ``glob.glob(..., recursive=True)`` so that
    ``**`` works. Order: positional first, then each pattern in order. Files
    are de-duplicated while preserving first-seen order. Patterns that match
    nothing are reported on stderr but not fatal.
    """
    out = []
    seen = set()
    for f in files:
        if f not in seen:
            seen.add(f)
            out.append(f)
    for pat in patterns or ():
        matches = sorted(_glob.glob(pat, recursive=True))
        if not matches:
            print("warning: --glob '%s' matched no files" % pat,
                  file=sys.stderr)
            continue
        for m in matches:
            if m not in seen:
                seen.add(m)
                out.append(m)
    return tuple(out)


def _run_wave(files, x, backend, sheet, pivot_spec=None,
              pivot_info_flag=False, session_path=None, export_path=None):
    x = _resolve_wave_x_from_cli_env(x)
    if pivot_spec:
        from cicsim.pivot import load_spec, pivot_info, apply_pivot
        from cicsim.wavefiles import WaveFile
        spec = load_spec(pivot_spec)

        if pivot_info_flag:
            for f in files:
                wf = WaveFile(f, x or "")
                print("--- %s ---" % f)
                print(pivot_info(wf.df, spec))
                print()
            return

        if not x and spec.get('columns'):
            x = spec['columns']

    if session_path or export_path:
        backend = "pg"

    if backend == "pg":
        try:
            # Delegate to standalone cicwave package for PyQtGraph backend
            import cicwave.cli
            # Convert arguments to match cicwave CLI expectations
            cicwave_args = []
            if files:
                cicwave_args.extend(files)
            if x:
                cicwave_args.extend(['--x', x])
            if sheet:
                cicwave_args.extend(['--sheet', sheet])
            if pivot_spec:
                cicwave_args.extend(['--pivot', pivot_spec])
            if pivot_info_flag:
                cicwave_args.append('--pivot-info')
            if session_path:
                cicwave_args.extend(['--session', session_path])
            if export_path:
                cicwave_args.extend(['--export', export_path])
            
            # Use cicwave's internal _run_wave_pg function directly
            from cicwave.cli import _run_wave_pg
            _run_wave_pg(files, x, sheet, pivot_spec, pivot_info_flag, session_path, export_path)
            return
        except ImportError as e:
            print("Error: PyQtGraph backend requires cicwave package")
            print("Install with: pip install cicwave")
            print(f"  ({e})")
            sys.exit(1)
    else:
        if not importlib.util.find_spec("tkinter"):
            print("Error: Could not find tkinter. Install python3-tk")
            print("On mac with brew: brew install python3-tk")
            print("On ubuntu: apt install python3-tk")
            sys.exit(1)
        c = cs.CmdWave(x)

    if session_path:
        c.win.applySession(session_path)

    if pivot_spec:
        for f in files:
            wf = WaveFile(f, x or "")
            pivoted = apply_pivot(wf.df, spec)
            name = "pivot(%s)" % os.path.basename(f)
            c.openDataFrame(pivoted, name,
                            pivot_spec_path=os.path.abspath(pivot_spec),
                            original_path=os.path.abspath(f))
    else:
        for f in files:
            c.openFile(f, sheet_name=sheet)

    if export_path:
        c.exportAndExit(export_path)
    else:
        c.run()


@click.command()
@click.argument("files", nargs=-1)
@click.option("--glob", "globs", multiple=True,
              help="Glob pattern (repeatable). Supports ** for recursion. "
                   "Useful on shells like PowerShell that don't auto-expand.")
@click.option("--x", default=None,
              help="X-axis column; else CICWAVE_X / CICSIM_X_AXIS; else saved default; else auto")
@click.option("--backend", default="pg", type=click.Choice(["tk", "pg"]),
              help="GUI backend (default: pg)")
@click.option("--sheet", default=None, help="Sheet name for Excel files (default: first sheet)")
@click.option("--pivot", default=None, help="Pivot spec file (YAML/JSON)")
@click.option("--pivot-info", is_flag=True, default=False, help="Print pivot dimensions and exit")
@click.option("--session", default=None, help="Load session file (.cicwave.yaml)")
@click.option("--export", default=None, help="Export plot to file (PDF/PNG/SVG) and exit")
def cicwave(files, globs, x, backend, sheet, pivot, pivot_info, session, export):
    """Waveform viewer (standalone).

    Now delegates to standalone cicwave package for PyQtGraph backend.
    For backward compatibility, this entry point is preserved in cicsim.

    Supports: .raw, .csv, .tsv, .xlsx, .json, .parquet, .feather, .h5,
    .pkl, and more.

    \b
    Pivot:
      --pivot spec.yaml     Reshape data using pivot spec before viewing
      --pivot-info          Print unique values per pivot dimension and exit

    \b
    Session:
      --session plot.cicwave.yaml         Load saved session
      --export plot.pdf                   Export to file and exit (no GUI)
      --session s.yaml --export out.pdf   Restore session and export

    \b
    Globs:
      --glob 'data/*.csv'             Repeatable, supports ** for recursion
      --glob '**/*.raw'               Useful on PowerShell which doesn't
                                       auto-expand patterns
    """
    try:
        # Delegate to standalone cicwave package
        from cicwave.cli import _run_wave_pg
        files_expanded = _expand_glob_patterns(files, globs)
        _run_wave_pg(files_expanded, x, sheet, pivot, pivot_info, session, export)
    except ImportError:
        print("Error: cicwave package not found")
        print("For PyQtGraph backend, install with: pip install cicwave")
        print("Alternatively, use: cicsim wave --backend tk")
        sys.exit(1)



@cli.command()
@click.argument("testbench")
@click.argument("corner",nargs=-1)
@click.option("--oformat",default="spectre",help="spectre")
@click.option("--run/--no-run", default=True, help="Run simulator")
@click.option("--ocn/--no-ocn", default=True, help="Run ocean")
#@click.option("--count", default=1, help="Run each corner count times, useful for Monte-Carlo")
#@click.option("--name", default=None, help="Control name of run file")
#@click.option("--ignore/--no-ignore", default=False,is_flag=True, help="Ignore error check")
#@click.option("--sha/--no-sha", default=False, help="Check SHA of input files")
def srun(testbench,corner,oformat,run,ocn):
    """Run a spectre simulation of TESTBENCH
    """

    r = cs.CmdRun(testbench,oformat,run,ocn,corner)
    r.run()


@cli.command()
@click.argument("filename")
@click.argument("xname")
@click.argument("yname")
@click.option("--ptype",default="", help="Plot options")
@click.option("--show/--no-show",default=True,help="Show plot or not")
@click.option("--fname",default="", help="Plot filename")
def plot(filename,xname,yname,ptype,show,fname):
    """Plot from rawfile

Example:\n
    Plot vp and vn versus time.\n
    $ cicsim plot test.raw time "v(vp),v(vn)"

    Plot vp and vn in the same plot\n
    $ cicsim plot test.raw time "v(vp),v(vn)" --ptype "same"


    """
    cs.rawplot(filename,xname,yname,ptype,fname=fname)
    if(show):
        plt.show()

@cli.command()
@click.argument("runfile")
def results(runfile):
    """Results of single runfile
    """
    r = cs.CmdResults(runfile)
    r.run()

@cli.command()
@click.option("--filename",default="summary.yaml",help="Input config file")
@click.option("--output",default="summary.md",help="Output summary file")
def summary(filename,output):
    """Generate simulation summary for results
    """
    r = cs.CmdSummary(filename,output)
    r.run()

@cli.command()
@click.argument("library",required=True)
@click.argument("cell",required=True)
@click.argument("template",required=True)
def simcell(library,cell,template):
    """Create a ngspice simulation directory for a Cell
    """
    c_ip = cs.CmdIp(library,template,cell=cell)
    c_ip.run()

@cli.command()
@click.argument("template",required=True)
@click.argument("options",required=True)
@click.option("--dname",default=None,help="Directory to generate")
def template(template,options,dname):
    """Run an IP template with <options> YAML file
    """

    if(not os.path.exists(options)):
        raise Exception(f"Could not find file {options}")

    with open(options) as fi:
        obj = yaml.safe_load(fi)

    if("library" not in obj):
        raise Exception("I must have 'library' defined in the options file")

    c_ip = cs.CmdIp(obj["library"],template,options=obj,dname=dname)
    c_ip.run()

@cli.command()
@click.argument("testbench",required=True)
@click.argument("source",required=True)
@click.argument("cell",required=True)
def portreplace(testbench,source,cell):
    """ Replace ${PORTS} and ${VPORTS} with the subcircuit ports of SOURCE CELL
    """
    stb = ""
    with open(testbench) as fi:
        for l in fi:
            stb += l

    sp = cs.SpiceParser()
    ports = sp.fastGetPortsFromFile(source,cell)
    stb = stb.replace("${PORTS}"," ".join(ports))

    stb = stb.replace("${VPORTS}"," ".join(map(lambda x: "v(%s)"%x,ports)))
    with open(testbench,"w") as fo:
        fo.write(stb)


if __name__ == "__main__":
    cli()
