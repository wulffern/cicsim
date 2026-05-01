#!/usr/bin/env python3

import os
import re
import numpy as np
import pandas as pd
from matplotlib.ticker import EngFormatter

from .ngraw import toDataFrame as _ngraw_toDataFrame

# ---------------------------------------------------------------------------
# Unit auto-detection from column names.
# ---------------------------------------------------------------------------

# SI-prefix scale factors (lower-case) plus the case-sensitive ones we
# tolerate. ``u`` is accepted as an alias for ``µ`` (micro).
_SI_PREFIXES = {
    'y': 1e-24, 'z': 1e-21, 'a': 1e-18, 'f': 1e-15, 'p': 1e-12,
    'n': 1e-9, 'u': 1e-6, 'µ': 1e-6, 'm': 1e-3,
    'k': 1e3, 'K': 1e3,
    'M': 1e6, 'G': 1e9, 'T': 1e12, 'P': 1e15, 'E': 1e18,
}

# Plain-unit symbols (no prefix scaling) that we recognise as-is.
_PLAIN_UNITS = {
    's', 'Hz', 'V', 'A', 'W', 'F', 'H', 'Ω', 'ohm', 'rad', 'deg',
    '°C', 'C', 'K', 'J', 'N', 'Pa', 'T', 'lx', 'cd',
}

# Log-domain units. Always treated as the literal string and never
# rescaled (you don't say "kdBm").
_LOG_UNITS = {
    'dB', 'dBm', 'dBV', 'dBuV', 'dBµV', 'dBc', 'dBFS', 'dBi', 'dBA',
}

# Base units that accept SI prefixes for auto-rescaling.
_PREFIXABLE_BASES = {'Hz', 'V', 'A', 's', 'W', 'F', 'H', 'Ω', 'ohm'}

# Match a unit token at the end of a column name, possibly enclosed in
# brackets/parens/braces or separated by underscore / space / slash.
# Examples that match:
#   "Frequency_MHz"        -> "MHz"
#   "Amplitude [dBm]"      -> "dBm"
#   "Power (W)"            -> "W"
#   "phase / deg"          -> "deg"
# Examples that DON'T match (good — these are node names, not units):
#   "v(out)", "i(M1.d)", "v-out"
_UNIT_SUFFIX_RE = re.compile(
    r"""
    [\s_/]*
    (?:
        \[ \s* (?P<b>[^\[\]]+?) \s* \]      # [unit]
      | \( \s* (?P<p>[^()]+?)   \s* \)      # (unit)
      | \{ \s* (?P<c>[^{}]+?)   \s* \}      # {unit}
      |       (?P<n>[A-Za-zµΩ°]+)           # bare suffix
    )
    \s*$
    """,
    re.VERBOSE,
)


def _classify_unit_token(tok):
    """Return ``(scale, unit_str)`` if ``tok`` is a recognised unit token,
    otherwise ``None``. ``scale`` is the multiplicative factor to apply to
    the data so the data, after scaling, is in the returned base unit."""
    if not tok:
        return None
    t = tok.strip()
    if not t:
        return None
    # Log-domain units: literal, no scaling.
    if t in _LOG_UNITS:
        return (1.0, t)
    # Plain units: literal, no scaling.
    if t in _PLAIN_UNITS:
        return (1.0, t)
    # SI prefix + base unit -> rescale to base.
    if len(t) >= 2:
        prefix, rest = t[0], t[1:]
        if prefix in _SI_PREFIXES and rest in _PREFIXABLE_BASES:
            return (_SI_PREFIXES[prefix], rest)
    return None


def parse_unit_from_name(name):
    """Detect the unit encoded in a column name.

    Returns a tuple ``(scale, unit, stripped_label)`` or ``None`` if no
    unit could be identified.

    - ``scale`` is the multiplier to apply to the data so it ends up in
      the returned base unit (e.g. ``Frequency_MHz`` -> 1e6 + ``Hz``).
    - ``unit`` is the unit string suitable for ``EngFormatter`` /
      axis labels.
    - ``stripped_label`` is ``name`` with the trailing unit token removed,
      for use as a clean axis label.
    """
    if not name:
        return None
    s = str(name)
    m = _UNIT_SUFFIX_RE.search(s)
    if not m:
        return None
    tok = m.group('b') or m.group('p') or m.group('c') or m.group('n')
    cls = _classify_unit_token(tok)
    if cls is None:
        return None
    scale, unit = cls
    stripped = s[:m.start()].rstrip(" _/-:")
    return (scale, unit, stripped or s)


#- Model for wavefiles

class Wave():

    def __init__(self,wfile,key,xaxis):
        self.xaxis = xaxis
        self.wfile = wfile
        self.x = None
        self.y = None
        self.xlabel = "Samples"
        self.key = key
        self.ylabel = key + f" ({wfile.name})"
        self.logx = False
        self.logy = False
        self.xunit = ""
        self.yunit, self._yscale = self._infer_yunit_and_scale(key)
        self.tag = wfile.getTag(self.key)
        self.line = None
        self.reload()

    @staticmethod
    def _infer_yunit(key):
        unit, _scale = Wave._infer_yunit_and_scale(key)
        return unit

    @staticmethod
    def _infer_yunit_and_scale(key):
        parsed = parse_unit_from_name(key)
        if parsed is not None:
            scale, unit, _ = parsed
            return unit, scale
        kl = (key or "").lower()
        if kl.startswith("v(") or kl.startswith("v-"):
            return "V", 1.0
        if kl.startswith("i(") or kl.startswith("i-"):
            return "A", 1.0
        return "", 1.0

    def deleteLine(self):
        if(self.line):
            self.line.remove()
            self.line = None

    def plot(self,ax):
        x = np.real(self.x) if self.x is not None else None
        y = np.real(self.y) if self.y is not None else self.y
        if(x is not None):
            if(not self.logx and not self.logy):
                self.line, = ax.plot(x,y,label=self.ylabel)
            elif(self.logx and not self.logy):
                self.line, = ax.semilogx(x,y,label=self.ylabel)
            elif(not self.logx and self.logy):
                self.line, = ax.semilogy(x,y,label=self.ylabel)
            elif(self.logx and self.logy):
                self.line, = ax.loglog(x,y,label=self.ylabel)
        else:
            self.line, = ax.plot(y,label=self.ylabel)

        if self.xunit:
            ax.xaxis.set_major_formatter(EngFormatter(unit=self.xunit))
        if self.yunit:
            ax.yaxis.set_major_formatter(EngFormatter(unit=self.yunit))

    def _set_x_from_column(self, col, label, unit, logx=False):
        arr = self.wfile.df[col].to_numpy()
        parsed = parse_unit_from_name(col)
        if parsed is not None:
            scale, base_unit, clean = parsed
            if scale != 1.0:
                arr = arr * scale
            self.x = arr
            self.xlabel = clean or label
            self.xunit = base_unit
        else:
            self.x = arr
            self.xlabel = label
            self.xunit = unit
        self.logx = logx

    def reload(self):
        self.wfile.reload()
        keys = self.wfile.df.columns

        if "time" in keys:
            self._set_x_from_column("time", "Time", "s")
        elif "frequency" in keys:
            self._set_x_from_column("frequency", "Frequency", "Hz",
                                    logx=True)
        elif "v(v-sweep)" in keys:
            self._set_x_from_column("v(v-sweep)", "Voltage", "V")
        elif "i(i-sweep)" in keys:
            self._set_x_from_column("i(i-sweep)", "Current", "A")
        elif "temp-sweep" in keys:
            self._set_x_from_column("temp-sweep", "Temperature", "°C")
        elif self.xaxis and self.xaxis in keys:
            self._set_x_from_column(self.xaxis, " ", "")
        else:
            for col in keys:
                if col == self.key:
                    continue
                if parse_unit_from_name(col) is not None:
                    self._set_x_from_column(col, col, "")
                    break

        if self.key in keys:
            y = self.wfile.df[self.key].to_numpy()
            if self._yscale != 1.0:
                y = y * self._yscale
            self.y = y

        if self.line:
            if self.x is not None:
                self.line.set_xdata(self.x)
            self.line.set_ydata(self.y)


class WaveFile():

    # Extensions where reading the column list is much cheaper than reading
    # the full file. For everything else we fall back to a full load on open
    # (matching pre-lazy behavior).
    _HEADER_ONLY_EXTS = {
        '.csv', '.tsv', '.txt',
        '.xlsx', '.xls', '.ods',
        '.parquet', '.feather',
    }

    def __init__(self, fname, xaxis, sheet_name=0, df=None):
        self.xaxis = xaxis
        self.fname = fname
        self.sheet_name = sheet_name
        self.name = os.path.basename(fname)
        if isinstance(sheet_name, str):
            self.name += " [%s]" % sheet_name
        self.waves = dict()
        self._df = df
        self._columns = None
        self._virtual = df is not None
        if self._virtual and df is not None:
            self._columns = list(df.columns)
        self.modified = None
        self.reload()

    @property
    def df(self):
        if self._virtual:
            return self._df
        if self._df is None:
            self._df = self._read_file()
            self._columns = list(self._df.columns)
        return self._df

    @df.setter
    def df(self, value):
        self._df = value
        if value is not None:
            self._columns = list(value.columns)

    def reload(self):
        """Refresh metadata. Header-only on first open for cheap formats; the
        full DataFrame is loaded lazily on first ``df`` access. If the file
        on disk has changed since we last loaded it, drop any cached data so
        the next access re-reads."""
        if self._virtual:
            return

        if self.modified is None:
            self._read_header_or_full()
            self.modified = os.path.getmtime(self.fname)
            return

        newmodified = os.path.getmtime(self.fname)
        if newmodified > self.modified:
            had_full = self._df is not None
            self._df = None
            self._columns = None
            self._read_header_or_full()
            if had_full:
                # Trigger full reload right away to match pre-lazy semantics
                # for callers that expected fresh data after reload().
                _ = self.df
            self.modified = newmodified

    def _read_header_or_full(self):
        """Populate ``self._columns`` cheaply if possible; otherwise fall back
        to a full read (which also fills ``self._df``)."""
        ext = os.path.splitext(self.fname)[1].lower()
        if ext in self._HEADER_ONLY_EXTS:
            try:
                self._columns = list(self._read_header(ext))
                return
            except Exception:
                self._columns = None
        # Formats without a cheap header path (or header read failed):
        # do a full load now, matching pre-lazy behavior.
        self._df = self._read_file()
        self._columns = list(self._df.columns)

    def _read_header(self, ext):
        if ext in ('.csv',):
            return self._read_csv_header(',')
        if ext in ('.tsv', '.txt'):
            return self._read_csv_header('\t')
        if ext in ('.xlsx', '.xls', '.ods'):
            df = pd.read_excel(self.fname, sheet_name=self.sheet_name, nrows=0)
            return [c.strip() for c in df.columns]
        if ext == '.parquet':
            import pyarrow.parquet as pq
            return list(pq.read_schema(self.fname).names)
        if ext == '.feather':
            import pyarrow.feather as pf
            return list(pf.read_table(self.fname, columns=[]).schema.names)
        raise ValueError("no header reader for %s" % ext)

    def _read_csv_header(self, sep):
        try:
            df = pd.read_csv(self.fname, sep=sep, nrows=0,
                             engine='c', memory_map=True)
        except Exception:
            try:
                df = pd.read_csv(self.fname, sep=sep, nrows=0)
            except Exception:
                df = pd.read_csv(self.fname, sep=None, engine='python',
                                 nrows=0)
        return [c.strip() for c in df.columns]

    PANDAS_READERS = {
        '.prn':     lambda self: self._read_prn(),
        '.vcd':     lambda self: read_vcd(self.fname),
        '.csv':     lambda self: self._read_csv(','),
        '.tsv':     lambda self: self._read_csv('\t'),
        '.txt':     lambda self: self._read_csv('\t'),
        '.xlsx':    lambda self: self._read_excel(),
        '.xls':     lambda self: self._read_excel(),
        '.ods':     lambda self: self._read_excel(),
        '.pkl':     lambda self: pd.read_pickle(self.fname),
        '.pickle':  lambda self: pd.read_pickle(self.fname),
        '.json':    lambda self: pd.read_json(self.fname),
        '.parquet': lambda self: pd.read_parquet(self.fname),
        '.feather': lambda self: pd.read_feather(self.fname),
        '.h5':      lambda self: pd.read_hdf(self.fname),
        '.hdf5':    lambda self: pd.read_hdf(self.fname),
        '.html':    lambda self: pd.read_html(self.fname)[0],
        '.xml':     lambda self: pd.read_xml(self.fname),
        '.fwf':     lambda self: pd.read_fwf(self.fname),
        '.stata':   lambda self: pd.read_stata(self.fname),
        '.dta':     lambda self: pd.read_stata(self.fname),
        '.sas7bdat': lambda self: pd.read_sas(self.fname),
        '.sav':     lambda self: pd.read_spss(self.fname),
    }

    def _read_file(self):
        ext = os.path.splitext(self.fname)[1].lower()
        reader = self.PANDAS_READERS.get(ext)
        if reader:
            return reader(self)
        return _ngraw_toDataFrame(self.fname)

    def _read_csv(self, sep):
        # Prefer pyarrow (much faster on large numeric CSVs); fall back to
        # the C engine with memory_map, then the slow Python engine.
        try:
            df = pd.read_csv(self.fname, sep=sep, engine='pyarrow')
        except Exception:
            try:
                df = pd.read_csv(self.fname, sep=sep, engine='c',
                                 low_memory=False, memory_map=True)
            except Exception:
                df = pd.read_csv(self.fname, sep=None, engine='python')
        df.columns = [c.strip() for c in df.columns]
        return df

    def _read_excel(self):
        df = pd.read_excel(self.fname, sheet_name=self.sheet_name)
        df.columns = [c.strip() for c in df.columns]
        return df

    def _read_prn(self):
        """Parse Xyce .prn (print) waveform file into a DataFrame."""
        sweep_var = "time"
        var_names = []
        times = []
        data_rows = []

        with open(self.fname, 'r') as f:
            in_header = False
            in_nodes = False
            pending_time = None

            for line in f:
                line_s = line.strip()

                if line_s.startswith('#H'):
                    in_header = True
                    in_nodes = False
                    continue

                if line_s.startswith('#N'):
                    in_header = False
                    in_nodes = True
                    continue

                if line_s.startswith('#C'):
                    in_nodes = False
                    in_header = False
                    parts = line_s.split()
                    pending_time = float(parts[1])
                    continue

                if line_s.startswith('#'):
                    in_header = False
                    in_nodes = False
                    pending_time = None
                    continue

                if in_header:
                    m = re.search(r"SWEEPVAR='([^']+)'", line_s)
                    if m:
                        sweep_var = m.group(1).lower()
                    continue

                if in_nodes:
                    var_names.extend(re.findall(r"'([^']+)'", line_s))
                    continue

                if pending_time is not None and line_s:
                    vals = [float(v.split(':')[0]) for v in line_s.split()]
                    if vals:
                        times.append(pending_time)
                        data_rows.append(vals)
                    pending_time = None

        n_vars = len(var_names)
        cols = [sweep_var] + [v.lower() for v in var_names]
        rows = [[t] + d[:n_vars] for t, d in zip(times, data_rows)]
        return pd.DataFrame(rows, columns=cols)

    @staticmethod
    def excel_sheet_names(fname):
        xl = pd.ExcelFile(fname)
        return xl.sheet_names

    def getWaveNames(self):
        if self._columns is not None:
            return self._columns
        return list(self.df.columns)

    def getWave(self,yname):

        if(yname not in self.waves):
            wave = Wave(self,yname,self.xaxis)
            self.waves[yname] = wave

        wave = self.waves[yname]
        wave.reload()

        return wave

    def getTag(self,yname):
        return self.fname + "/" + yname


class WaveFiles(dict):

    def __init__(self):
        self.current = None
        pass

    def open(self,fname,xaxis,sheet_name=0):
        key = fname if sheet_name == 0 else "%s::%s" % (fname, sheet_name)
        self[key] = WaveFile(fname,xaxis,sheet_name)
        self.current = key
        return self[key]

    def openDataFrame(self, df, name, xaxis):
        key = "::virtual::" + name
        self[key] = WaveFile(name, xaxis, df=df)
        self.current = key
        return self[key]

    def select(self,fname):
        if(fname in self):
            self.current = fname

    def remove(self, key):
        """Remove a loaded file by dict key. Updates current if needed."""
        if key not in self:
            return
        del self[key]
        if self.current == key:
            self.current = next(iter(self.keys()), None)

    def clear_all(self):
        """Remove every loaded file."""
        dict.clear(self)
        self.current = None

    def getSelected(self):
        if(self.current is not None):
            return self[self.current]


# ---------------------------------------------------------------------------
# VCD parser
# ---------------------------------------------------------------------------

#- VCD timescale unit -> seconds. The standard set per IEEE 1364.
_VCD_TIMESCALE_UNITS = {
    's': 1.0, 'ms': 1e-3, 'us': 1e-6, 'µs': 1e-6, 'ns': 1e-9,
    'ps': 1e-12, 'fs': 1e-15,
}


def _vcd_parse_timescale(text):
    """Parse a ``$timescale`` body like ``"1 ps"`` / ``"10ns"`` -> seconds.

    Returns the multiplier that converts a raw ``#<n>`` tick into seconds.
    Falls back to 1.0 if the body is missing or unrecognised.
    """
    s = (text or "").strip().lower().replace('\n', ' ')
    if not s:
        return 1.0
    m = re.match(r"\s*([0-9.eE+\-]+)\s*([a-zµ]+)\s*$", s)
    if m is None:
        #- Sometimes the number and unit are on separate tokens with extra
        #- whitespace; do a looser split.
        toks = s.split()
        if len(toks) >= 2:
            num_s, unit_s = toks[0], toks[1]
        else:
            return 1.0
    else:
        num_s, unit_s = m.group(1), m.group(2)
    try:
        num = float(num_s)
    except ValueError:
        return 1.0
    return num * _VCD_TIMESCALE_UNITS.get(unit_s, 1.0)


def read_vcd(fname, max_signals=None):
    """Parse a VCD (Value Change Dump) file into a pandas DataFrame.

    The result has a ``time`` column (in seconds, after applying
    ``$timescale``) plus one column per signal. Single-bit signals are
    stored as object arrays of ``"0" / "1" / "x" / "z"``; vector
    signals are stored as Python ints (or ``None`` for x/z); real
    signals are stored as floats.

    The DataFrame attaches metadata in ``df.attrs['cicsim_vcd']``:
        ``{'kinds': {col: 'bit'|'vector'|'real'},
           'widths': {col: int},
           'scope':  {col: scoped_name}}``

    Parameters
    ----------
    fname : str
        Path to the VCD file.
    max_signals : int or None
        If set, only the first N declared signals are kept (used to
        bound memory on huge dumps). ``None`` keeps everything.

    Notes
    -----
    Only the subset of VCD actually emitted by Icarus / Verilator /
    ngspice is supported. We follow the structure but don't try to
    enforce strict compliance.
    """
    timescale = 1.0
    #- id_code -> {'name': scoped_name, 'kind': 'bit'/'vector'/'real',
    #-             'width': int}
    sig_info = {}
    scope_stack = []

    def _parse_decls(fh):
        nonlocal timescale
        cur = []
        in_timescale = False
        for line in fh:
            ls = line.strip()
            if not ls:
                continue
            if ls.startswith('$timescale'):
                in_timescale = True
                cur = [ls[len('$timescale'):]]
                if '$end' in ls:
                    timescale = _vcd_parse_timescale(
                        ' '.join(cur).replace('$end', ''))
                    in_timescale = False
                continue
            if in_timescale:
                if '$end' in ls:
                    cur.append(ls.replace('$end', ''))
                    timescale = _vcd_parse_timescale(' '.join(cur))
                    in_timescale = False
                else:
                    cur.append(ls)
                continue
            if ls.startswith('$scope'):
                toks = ls.split()
                #- $scope <type> <name> $end
                if len(toks) >= 3:
                    scope_stack.append(toks[2])
                continue
            if ls.startswith('$upscope'):
                if scope_stack:
                    scope_stack.pop()
                continue
            if ls.startswith('$var'):
                #- $var <type> <width> <id> <name> [<bit-select>] $end
                toks = ls.split()
                if len(toks) < 6:
                    continue
                vtype = toks[1]
                try:
                    width = int(toks[2])
                except ValueError:
                    continue
                idc = toks[3]
                name = toks[4]
                if width == 1 and vtype != 'real':
                    kind = 'bit'
                elif vtype == 'real':
                    kind = 'real'
                else:
                    kind = 'vector'
                #- Multiple $var lines can share the same id (alias). Keep
                #- the first; remember every alias name in ``aliases``.
                full = '.'.join(scope_stack + [name]) if scope_stack else name
                if idc in sig_info:
                    sig_info[idc].setdefault('aliases', []).append(full)
                else:
                    sig_info[idc] = {
                        'name': full, 'kind': kind, 'width': width,
                        'aliases': [],
                    }
                continue
            if ls.startswith('$enddefinitions'):
                return

    with open(fname, 'r', errors='replace') as fh:
        _parse_decls(fh)

        if max_signals is not None and len(sig_info) > max_signals:
            #- Keep only the first ``max_signals`` declared ids by
            #- insertion order.
            keep = set(list(sig_info.keys())[:max_signals])
            sig_info = {k: v for k, v in sig_info.items() if k in keep}

        ids = list(sig_info.keys())
        col_names = [sig_info[i]['name'] for i in ids]
        kind_by_id = {i: sig_info[i]['kind'] for i in ids}
        width_by_id = {i: sig_info[i]['width'] for i in ids}

        #- Pre-allocate per-signal change lists: list of (time_idx, value).
        changes = {i: [] for i in ids}
        times = []
        cur_t = 0
        in_dump = False  # inside $dumpvars / $dumpall block

        def _ensure_t0():
            #- Some VCDs (e.g. our compact unit-test fixtures) emit
            #- ``$dumpvars`` initial values before any ``#0`` time tick.
            #- Inject t=0 so those initial values are anchored properly.
            if not times:
                times.append(0)

        for line in fh:
            ls = line.strip()
            if not ls:
                continue
            c0 = ls[0]
            if c0 == '#':
                #- Time tick.
                try:
                    cur_t = int(ls[1:])
                except ValueError:
                    continue
                if not times or times[-1] != cur_t:
                    times.append(cur_t)
                continue
            if c0 == '$':
                if ls.startswith('$dumpvars') or ls.startswith('$dumpall'):
                    in_dump = True
                    _ensure_t0()
                elif ls.startswith('$end'):
                    in_dump = False
                #- Other directives ($comment etc.) ignored.
                continue
            if c0 in ('0', '1', 'x', 'X', 'z', 'Z', 'h', 'H', 'l', 'L'):
                #- Single-bit change: value char + id (no space).
                idc = ls[1:].strip()
                if idc in changes:
                    changes[idc].append(
                        (len(times) - 1 if times else 0, c0.lower()))
                continue
            if c0 == 'b' or c0 == 'B':
                #- Vector: b<bits> <id>
                try:
                    bits, idc = ls.split(None, 1)
                except ValueError:
                    continue
                idc = idc.strip()
                bits = bits[1:]  # drop leading 'b'
                if idc in changes:
                    if any(c in 'xXzZ' for c in bits):
                        val = None  # unknown -> store as None
                        raw = bits.lower()
                    else:
                        try:
                            val = int(bits, 2)
                            raw = val
                        except ValueError:
                            val = None
                            raw = bits.lower()
                    changes[idc].append(
                        (len(times) - 1 if times else 0, raw))
                continue
            if c0 == 'r' or c0 == 'R':
                #- Real: r<float> <id>
                try:
                    fval, idc = ls.split(None, 1)
                except ValueError:
                    continue
                idc = idc.strip()
                try:
                    rv = float(fval[1:])
                except ValueError:
                    continue
                if idc in changes:
                    changes[idc].append(
                        (len(times) - 1 if times else 0, rv))
                continue

    if not times:
        #- Pathological: no time markers. Return empty frame with the
        #- declared column list so the UI still shows the signal names.
        df = pd.DataFrame({c: [] for c in ['time'] + col_names})
        df.attrs['cicsim_vcd'] = {
            'kinds': {sig_info[i]['name']: sig_info[i]['kind'] for i in ids},
            'widths': {sig_info[i]['name']: sig_info[i]['width'] for i in ids},
            'scope': {sig_info[i]['name']: sig_info[i]['name'] for i in ids},
            'timescale_s': timescale,
        }
        return df

    #- Build forward-filled per-signal columns.
    n = len(times)
    data = {'time': np.asarray(times, dtype=np.float64) * timescale}
    for idc in ids:
        kind = kind_by_id[idc]
        if kind == 'real':
            col = np.full(n, np.nan, dtype=np.float64)
            cur = np.nan
            j = 0
            ch = changes[idc]
            for t_idx in range(n):
                while j < len(ch) and ch[j][0] <= t_idx:
                    cur = ch[j][1]
                    j += 1
                col[t_idx] = cur
        elif kind == 'bit':
            col = np.empty(n, dtype=object)
            cur = 'x'
            j = 0
            ch = changes[idc]
            for t_idx in range(n):
                while j < len(ch) and ch[j][0] <= t_idx:
                    cur = ch[j][1]
                    j += 1
                col[t_idx] = cur
        else:  # vector
            col = np.empty(n, dtype=object)
            cur = None
            j = 0
            ch = changes[idc]
            for t_idx in range(n):
                while j < len(ch) and ch[j][0] <= t_idx:
                    cur = ch[j][1]
                    j += 1
                col[t_idx] = cur
        name = sig_info[idc]['name']
        data[name] = col
        for alias in sig_info[idc].get('aliases', []):
            #- Aliases share data but get their own column for selection.
            data[alias] = col

    df = pd.DataFrame(data)
    kinds = {sig_info[i]['name']: sig_info[i]['kind'] for i in ids}
    widths = {sig_info[i]['name']: sig_info[i]['width'] for i in ids}
    for i in ids:
        for alias in sig_info[i].get('aliases', []):
            kinds[alias] = sig_info[i]['kind']
            widths[alias] = sig_info[i]['width']
    df.attrs['cicsim_vcd'] = {
        'kinds': kinds,
        'widths': widths,
        'timescale_s': timescale,
    }
    return df
