#!/usr/bin/env python3

import cicsim as cs
import os
import re
import numpy as np
import pandas as pd
from matplotlib.ticker import EngFormatter

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
        return cs.toDataFrame(self.fname)

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
