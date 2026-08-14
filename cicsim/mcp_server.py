#!/usr/bin/env python3
"""MCP server exposing cicsim's simulation bookkeeping as tools.

Lets an agent answer the questions that otherwise cost a viewer session
or a hexdump: what vectors does this .raw actually contain, did this node
ever move, which measurements are out of spec and in which corners, and
are these results still newer than the netlist they were run against.

The tools are read-only. Nothing here launches ngspice -- `cicsim run` is
long, corner-expanded and belongs in a Makefile where its output is
visible, not behind a tool call that blocks until it finishes.

Run directly:

    cicsim-mcp

Or point an MCP client's config at the `cicsim-mcp` console script.
Requires `pip install "mcp[cli]"` for the server framework itself.
"""

import os
import re
import glob
import time
import contextlib

#- The MCP Python SDK renamed FastMCP to MCPServer in 2.0 and moved it out of
#- mcp.server.fastmcp. The .tool() decorator and .run() are otherwise
#- source-compatible, so accept either generation rather than pinning users
#- to one. Same shim as cicwave's server.
try:
    from mcp.server.mcpserver import MCPServer as _Server  # SDK >= 2.0
except ImportError:  # pragma: no cover - depends on the installed SDK
    from mcp.server.fastmcp import FastMCP as _Server  # SDK 1.x

import inspect

try:
    from importlib.metadata import version as _pkg_version
    __version__ = _pkg_version("cicsim")
except Exception:  # pragma: no cover - source checkout without metadata
    __version__ = "0.0.0"

#- SDK 2.0 reports a version in the initialize handshake and defaults it to an
#- empty string; SDK 1.x has no such parameter, hence the signature check.
_server_kwargs = {}
if "version" in inspect.signature(_Server.__init__).parameters:
    _server_kwargs["version"] = __version__

mcp = _Server(
    "cicsim",
    instructions=(
        "Tools for inspecting cicsim/ngspice simulation results. "
        "'raw_info' lists the vectors actually present in a .raw file -- "
        "read it first when a measurement reports 'no such vector', since "
        "probe paths differ between schematic and extracted views. "
        "'raw_signals' summarizes chosen vectors numerically without "
        "opening a viewer. 'results' returns the measurements of a .run "
        "with their spec verdict, and 'sim_status' reports which runs "
        "exist in a simulation directory and whether they are stale "
        "against the netlists they include."
    ),
    **_server_kwargs,
)


@contextlib.contextmanager
def _in_dir(directory):
    """Run inside *directory*.

    cicsim's conventions are cwd-relative throughout -- Specification
    opens "<testbench>.yaml", a .run file names its outputs relative to
    the simulation directory -- so the tools take a directory rather
    than trying to rebase every path.
    """
    old = os.getcwd()
    if directory:
        os.chdir(os.path.expanduser(directory))
    try:
        yield
    finally:
        os.chdir(old)


def _fmt_eng(v):
    """Format a float compactly without losing small-signal detail."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    if f == 0:
        return "0"
    a = abs(f)
    if a < 1e-3 or a >= 1e5:
        return "%.4g" % f
    return "%.6g" % f


@mcp.tool()
def raw_info(file: str, pattern: str | None = None) -> str:
    """List the vectors present in an ngspice .raw file.

    Read this when a measurement fails with "no such vector as v(x.y)".
    A probe path is only valid for the view it was written for: an
    extracted (Lay) netlist is flat, so the layout's cell hierarchy ends
    up inside the node *name* (VC becomes xbias.VC), while the schematic
    keeps VC at the top. LVS passing does not imply the internal names
    match -- only the ports are compared.

    Args:
        file: Path to the .raw file.
        pattern: Optional case-insensitive regex to filter vector names.
            Use it to ask "is there anything resembling vc here" rather
            than reading a list of thousands.
    """
    from .ngraw import ngRawRead

    arrs, plots = ngRawRead(os.path.expanduser(file))
    if not plots:
        return "no plots found in %s" % file

    rx = re.compile(pattern, re.IGNORECASE) if pattern else None

    out = []
    for i, plot in enumerate(plots):
        def meta(key):
            v = plot.get(key.encode() if isinstance(key, str) else key)
            return v.decode("ascii", "replace") if isinstance(v, bytes) else v

        names = plot.get("varnames", [])
        units = plot.get("varunits", [])
        shown = [(n, u) for n, u in zip(names, units)
                 if rx is None or rx.search(n)]

        out.append("plot %d: %s" % (i, meta("plotname")))
        out.append("  date:      %s" % meta("date"))
        out.append("  points:    %s" % meta("no. points"))
        out.append("  variables: %d%s" % (
            len(names),
            "" if rx is None else " (%d matching %r)" % (len(shown), pattern),
        ))

        #- The x axis is the first vector; its span is what tells you
        #- whether the run actually reached the measurement time.
        if len(arrs) > i and len(names) and len(arrs[i]):
            col = arrs[i][names[0]]
            out.append("  %s span:  %s .. %s" % (
                names[0], _fmt_eng(col[0].real), _fmt_eng(col[-1].real)))

        if not shown:
            out.append("  (no vector names matched)")
        for n, u in shown:
            out.append("    %-40s %s" % (n, u))
        out.append("")

    return "\n".join(out).rstrip()


@mcp.tool()
def raw_signals(file: str, signals: list[str], at: float | None = None) -> str:
    """Summarize chosen vectors of a .raw file numerically.

    Answers "did this node ever move" and "what is it at t=x" without a
    waveform viewer. Reports min/max/mean plus the first and last value
    of each signal; a node whose min equals its max never switched.

    Args:
        file: Path to the .raw file.
        signals: Vector names as they appear in the file, e.g.
            "v(osc_temp_1v8)". Case-insensitive. Call `raw_info` first
            if unsure -- an unmatched name is reported, not guessed at.
        at: Optional x-axis value (a time, for a transient). Adds the
            value of each signal at the nearest sample to that point.
    """
    from .ngraw import toDataFrame

    df = toDataFrame(os.path.expanduser(file))
    if df is None or df.empty:
        return "no data in %s" % file

    lower = {c.lower(): c for c in df.columns}
    xname = df.columns[0]

    idx_at = None
    if at is not None:
        xs = df[xname].apply(lambda v: v.real if hasattr(v, "real") else v)
        idx_at = (xs - at).abs().idxmin()

    out = []
    if idx_at is not None:
        out.append("nearest sample to %s=%s is %s" % (
            xname, _fmt_eng(at), _fmt_eng(df[xname][idx_at].real)))
        out.append("")

    head = "%-38s %12s %12s %12s %12s %12s" % (
        "signal", "min", "max", "mean", "first", "last")
    if idx_at is not None:
        head += " %12s" % "at"
    out.append(head)

    for s in signals:
        col = lower.get(s.lower())
        if col is None:
            out.append("%-38s  NOT FOUND (see raw_info)" % s)
            continue
        ser = df[col].apply(lambda v: v.real if hasattr(v, "real") else v)
        line = "%-38s %12s %12s %12s %12s %12s" % (
            col, _fmt_eng(ser.min()), _fmt_eng(ser.max()),
            _fmt_eng(ser.mean()), _fmt_eng(ser.iloc[0]),
            _fmt_eng(ser.iloc[-1]))
        if idx_at is not None:
            line += " %12s" % _fmt_eng(ser[idx_at])
        out.append(line)

    return "\n".join(out)


@mcp.tool()
def results(runfile: str, directory: str = ".",
            only_fails: bool = False) -> str:
    """Report the measurements of a completed run with their spec verdict.

    A .run file lists the corners that ran; each has a .yaml of measured
    values beside it. The specs come from "<testbench>.yaml" in the same
    directory (min/typ/max/scale/unit), so the verdict here is the same
    one `cicsim summary` puts in the README.

    Args:
        runfile: The .run file, e.g. "tran_Sch_etc.run".
        directory: Simulation directory holding it. Defaults to cwd.
        only_fails: Report only measurements outside their min/max, with
            the corners they failed in. Use this on a wide corner sweep
            where the full table is mostly passing rows.
    """
    from .cmdresults import CmdResults
    from .spec import Specification

    with _in_dir(directory):
        if not os.path.exists(runfile):
            return "no such run file: %s (in %s)" % (
                runfile, os.path.abspath("."))

        c = CmdResults(runfile)
        df = c.readYaml()
        if df is None:
            return "%s produced no results (all corners failed?)" % runfile

        specs = Specification(c.testbench)

        import pandas as pd

        #- A post-processing script may store a whole sweep under one key
        #- (tran.py writes lists for "temperature" and "freq"), and those
        #- keys can collide with a spec name. Only scalar numeric columns
        #- can be scaled or compared against a min/max.
        numeric = [c_ for c_ in df.columns
                   if pd.api.types.is_numeric_dtype(df[c_])]

        #- Measured values are stored raw; the spec's scale is what turns
        #- amps into the uA the spec is written in. cmdresults applies it
        #- the same way before comparing.
        for col in numeric:
            if col in specs:
                df[col] = specs.scale(df[col])

        keys = [k for k in ("name", "type") if k in df.columns]
        data = [c_ for c_ in numeric if c_ not in keys and c_ != "time"]

        out = ["run:       %s" % runfile,
               "corners:   %d" % len(df),
               "specs:     %s" % (c.testbench + ".yaml")]

        unspecced = [d for d in data if d not in specs]
        if unspecced:
            out.append("unspecced: %s" % ", ".join(sorted(unspecced)[:12]))
        out.append("")

        rows = []
        for col in sorted(d for d in data if d in specs):
            spec = specs[col]
            ser = df[col].dropna()
            if ser.empty:
                continue
            bad = ser[~ser.apply(spec.OK)] if (
                spec.min is not None and spec.max is not None) else ser[[]]
            if only_fails and bad.empty:
                continue

            where = ""
            if not bad.empty and "name" in df.columns:
                names = df.loc[bad.index, "name"].astype(str).tolist()
                where = ",".join(names[:4]) + ("..." if len(names) > 4 else "")

            rows.append("%-16s %10s %10s %10s %10s %10s  %-4s %s" % (
                col,
                spec.stringNoUnit(spec.min), spec.stringNoUnit(spec.typ),
                spec.stringNoUnit(spec.max),
                _fmt_eng(ser.min()), _fmt_eng(ser.max()),
                "FAIL" if not bad.empty else "ok",
                where))

        if not rows:
            return "\n".join(out) + (
                "all specced measurements within min/max"
                if only_fails else "no specced measurements found")

        out.append("%-16s %10s %10s %10s %10s %10s  %-4s %s" % (
            "measurement", "spec_min", "spec_typ", "spec_max",
            "got_min", "got_max", "", "failing corners"))
        out.extend(rows)
        out.append("")
        out.append("units follow <testbench>.yaml; values are scaled to them.")
        return "\n".join(out)


def _sha256(path):
    import hashlib
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _stale_deps(rundir, corner):
    """Which recorded dependencies of *corner* no longer hash the same.

    cicsim writes a <corner>.sha beside each run holding the sha256 of
    every file that corner depended on -- netlists, .lib includes, the
    testbench, the .meas -- and re-simulates when one stops matching.
    Reusing that is the only honest staleness test here: `make netlist`
    rewrites the netlist on every invocation, so its mtime moves even
    when the circuit did not, and an mtime comparison calls everything
    stale.

    Returns (changed, missing). An empty .sha yields ([], []).
    """
    import yaml

    shafile = os.path.join(rundir, corner + ".sha")
    if not os.path.exists(shafile):
        return None, None
    try:
        with open(shafile) as fi:
            old = yaml.safe_load(fi.read()) or {}
    except (OSError, yaml.YAMLError):
        return None, None

    changed, missing = [], []
    for name, sha in old.items():
        #- Same resolution addSha uses: absolute as-is, else relative to
        #- the run directory (ngspice's cwd), not the sim directory.
        path = name if name.startswith("/") else os.path.join(rundir, name)
        if not os.path.exists(path):
            missing.append(name)
            continue
        try:
            if _sha256(path) != sha:
                changed.append(name)
        except OSError:
            missing.append(name)
    return changed, missing


@mcp.tool()
def sim_status(directory: str = ".") -> str:
    """Report the runs in a simulation directory and whether they are stale.

    For each .run, re-hashes the dependencies cicsim recorded for its
    corners and reports which have changed since. A stale run is
    reporting numbers for a circuit that has since been edited -- the
    usual reason a README disagrees with the design.

    This is the same sha comparison `cicsim run` uses to decide whether
    to re-simulate, so "stale" here means those corners would actually
    re-run rather than be skipped.

    One false positive to know about: a magic parasitic extraction
    (<cell>_lpe.spi) is not byte-stable. Re-extracting an unchanged
    layout emits the same capacitors with the same values and nodes in a
    different order, under different C<n> names, so the hash moves while
    the circuit does not. A Lay run reported stale only on a _lpe.spi is
    therefore usually still valid; compare the sorted device and
    capacitor lines before re-simulating.

    Args:
        directory: Simulation directory to inspect. Defaults to cwd.
    """
    with _in_dir(directory):
        runs = sorted(glob.glob("*.run"))
        if not runs:
            return "no .run files in %s" % os.path.abspath(".")

        out = ["directory: %s" % os.path.abspath(".")]
        out.append("")
        out.append("%-28s %-18s %5s %6s  %s" % (
            "run", "completed", "corn", "stale", "changed since the run"))

        for r in runs:
            tb = re.sub("_.*", "", r.replace(".run", ""))
            rundir = "output_" + tb
            mt = os.stat(r).st_mtime

            try:
                with open(r) as fi:
                    cnames = [l.strip() for l in fi if l.strip()]
            except OSError:
                cnames = []

            n_stale = 0
            culprits = []
            untracked = 0
            for c in cnames:
                #- The .run lines already carry the output_<tb>/ prefix.
                corner = os.path.basename(c)
                changed, missing = _stale_deps(rundir, corner)
                if changed is None:
                    untracked += 1
                    continue
                if changed or missing:
                    n_stale += 1
                    for f in changed + missing:
                        b = os.path.basename(f)
                        if b not in culprits:
                            culprits.append(b)

            if untracked == len(cnames) and cnames:
                state = "?"
                why = "no .sha recorded (run with sha enabled)"
            elif n_stale == 0:
                state = "0"
                why = "up to date"
            else:
                state = str(n_stale)
                why = ", ".join(culprits[:3]) + (
                    "..." if len(culprits) > 3 else "")

            out.append("%-28s %-18s %5d %6s  %s" % (
                r, time.strftime("%Y-%m-%d %H:%M", time.localtime(mt)),
                len(cnames), state, why))

        out.append("")
        out.append("stale = corners whose recorded dependency hashes no "
                   "longer match; those would re-simulate.")
        return "\n".join(out)


@mcp.tool()
def corners(directory: str = ".") -> str:
    """List the corner names defined for a simulation directory.

    Corners are the arguments `cicsim run` takes after the testbench
    name. They come from cicsim.yaml here, plus the one in the parent
    directory that holds the shared process/temperature/voltage set.

    Args:
        directory: Simulation directory to inspect. Defaults to cwd.
    """
    import yaml

    with _in_dir(directory):
        found = []
        for path in ("cicsim.yaml", "../cicsim.yaml"):
            if not os.path.exists(path):
                continue
            with open(path) as fi:
                obj = yaml.safe_load(fi) or {}
            names = list((obj.get("corner") or {}).keys())
            if names:
                found.append((os.path.abspath(path), names))

        if not found:
            return "no cicsim.yaml with a corner block found from %s" % (
                os.path.abspath("."))

        out = []
        for path, names in found:
            out.append("%s (%d corners)" % (path, len(names)))
            #- Group by leading letter: the naming convention is one
            #- letter per axis (K process, T temperature, V supply).
            groups = {}
            for n in names:
                groups.setdefault(n[0], []).append(n)
            for g in sorted(groups):
                out.append("  %s: %s" % (g, " ".join(sorted(groups[g]))))
            out.append("")

        return "\n".join(out).rstrip()


def main():
    mcp.run()


if __name__ == "__main__":
    main()
