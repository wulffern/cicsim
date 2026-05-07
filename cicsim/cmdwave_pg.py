#!/usr/bin/env python3

"""
Waveform viewer using PySide6 + pyqtgraph.

Install:  pip install PySide6 pyqtgraph
"""

import os
import sys
import re
import numpy as np
import pandas as pd
from importlib.metadata import version as _pkg_version

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTreeWidget, QTreeWidgetItem, QLineEdit, QTabWidget,
    QPushButton, QLabel, QCheckBox, QTextEdit, QFileDialog, QDialog,
    QInputDialog, QMenu, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMessageBox)
from PySide6 import QtCore
from PySide6.QtCore import Qt, Signal, QEvent, QSettings, QTimer
from PySide6.QtGui import (QKeySequence, QFont, QFontDatabase, QShortcut,
                           QPainter, QColor, QPalette)

import pyqtgraph as pg

from .wavefiles import WaveFile, WaveFiles, parse_unit_from_name
from .theme import THEMES, _get_theme, _set_active_theme
from matplotlib.ticker import EngFormatter


def _mono_font(size):
    """Return the system fixed-width font at the given point size."""
    f = QFontDatabase.systemFont(QFontDatabase.FixedFont)
    f.setPointSize(size)
    return f


ZOOM_FACTOR = 1.3

PLOT_STYLES = ['Lines', 'Markers', 'Lines+Markers', 'Steps']


def _read_saved_default_xaxis():
    """Column name persisted via Edit → Default X Axis (empty = auto)."""
    s = QSettings("cicsim", "cicwave")
    v = s.value("default_x_axis", "")
    if not v:
        return None
    t = str(v).strip()
    return t or None


def _write_saved_default_xaxis(name):
    s = QSettings("cicsim", "cicwave")
    s.setValue("default_x_axis", name or "")


def _apply_grid(plot_item):
    """Apply theme-aware grid to a PlotItem."""
    theme = _get_theme()
    r, g, b, a = theme['grid_pen']
    pen = pg.mkPen(QColor(r, g, b, a), width=1)
    for axis_name in ('bottom', 'left'):
        ax = plot_item.getAxis(axis_name)
        ax.setGrid(a)
        ax.setPen(pen)
        ax.setTextPen(pg.mkPen(theme['pg_foreground']))
    plot_item.update()


def _style_kwargs(color, style, width=2):
    """Return PlotDataItem keyword args for the given plot style."""
    pen = pg.mkPen(color, width=width)
    if style == 'Markers':
        return dict(pen=None, symbol='o', symbolSize=6,
                    symbolPen=pg.mkPen(color, width=width), symbolBrush=color)
    if style == 'Lines+Markers':
        return dict(pen=pen, symbol='o', symbolSize=5,
                    symbolPen=pg.mkPen(color, width=width), symbolBrush=color)
    if style == 'Steps':
        return dict(pen=pen, stepMode='left')
    return dict(pen=pen)


_eng_cache = {}


def _eng(value, unit=""):
    fmt = _eng_cache.get(unit)
    if fmt is None:
        fmt = EngFormatter(unit=unit)
        _eng_cache[unit] = fmt
    return fmt(value)


def _to_numeric(arr):
    """Convert array to float. For string data, return (indices, labels)."""
    try:
        return np.real(np.array(arr, dtype=float)), None
    except (ValueError, TypeError):
        labels = [str(v) for v in arr]
        return np.arange(len(labels), dtype=float), labels


class _RotatedAxisItem(pg.AxisItem):
    """AxisItem that draws tick labels rotated 90 degrees."""

    def drawPicture(self, p, axisSpec, tickSpecs, textSpecs):
        super().drawPicture(p, axisSpec, tickSpecs, [])
        for rect, flags, text in textSpecs:
            p.save()
            p.translate(rect.center())
            p.rotate(-90)
            p.drawText(
                QtCore.QRectF(-rect.height() / 2, -rect.width() / 2,
                              rect.height(), rect.width()),
                Qt.AlignCenter, text)
            p.restore()


def _apply_rotated_ticks(plot_item, axis_name, ticks):
    """Replace an axis on a PlotItem with a rotated-label version."""
    old_ax = plot_item.getAxis(axis_name)
    new_ax = _RotatedAxisItem(axis_name)
    new_ax.setTicks([ticks])
    max_len = max((len(t[1]) for t in ticks), default=5)
    new_ax.setHeight(max(60, 7 * max_len))
    new_ax.linkToView(plot_item.vb)
    if old_ax.scene():
        old_ax.scene().removeItem(old_ax)
    plot_item.layout.removeItem(old_ax)
    plot_item.axes[axis_name]['item'] = new_ax
    plot_item.layout.addItem(new_ax, 3 if axis_name == 'bottom' else 1, 1)
    new_ax.setZValue(-1000)


class _SignalPickerDialog(QDialog):
    """Modal dialog with regex-filtered signal list (Signal + File columns)."""

    def __init__(self, parent, title, names, file_label=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(640, 500)
        self._names = list(names)
        if file_label is None:
            self._file_labels = [''] * len(self._names)
        elif isinstance(file_label, (list, tuple)):
            self._file_labels = list(file_label)
            if len(self._file_labels) < len(self._names):
                self._file_labels.extend(
                    [''] * (len(self._names) - len(self._file_labels)))
        else:
            self._file_labels = [str(file_label)] * len(self._names)

        layout = QVBoxLayout(self)
        self._search = QLineEdit()
        self._search.setPlaceholderText("Regex filter…")
        self._search.textChanged.connect(self._filter)
        layout.addWidget(self._search)

        self._table = QTableWidget(len(self._names), 2)
        self._table.setHorizontalHeaderLabels(["Signal", "File"])
        hdr = self._table.horizontalHeader()
        hdr.setStretchLastSection(True)
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setAlternatingRowColors(True)
        for i, n in enumerate(self._names):
            self._table.setItem(i, 0, QTableWidgetItem(n))
            self._table.setItem(i, 1, QTableWidgetItem(self._file_labels[i]))
        self._table.itemDoubleClicked.connect(lambda _: self.accept())
        layout.addWidget(self._table)

        row = QHBoxLayout()
        ok = QPushButton("OK")
        ok.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        row.addWidget(ok)
        row.addWidget(cancel)
        layout.addLayout(row)

    def _filter(self, text):
        try:
            pat = re.compile(text, re.IGNORECASE)
        except re.error:
            pat = None
        for i in range(self._table.rowCount()):
            sig = self._table.item(i, 0)
            fil = self._table.item(i, 1)
            s1 = sig.text() if sig else ""
            s2 = fil.text() if fil else ""
            ok = not pat or pat.search(s1) or pat.search(s2)
            self._table.setRowHidden(i, not ok)

    def selected(self):
        cr = self._table.currentRow()
        if cr >= 0 and not self._table.isRowHidden(cr):
            it = self._table.item(cr, 0)
            if it:
                return it.text()
        for i in range(self._table.rowCount()):
            if not self._table.isRowHidden(i):
                it = self._table.item(i, 0)
                if it:
                    return it.text()
        return None


class PgWave:
    """Associates a WaveFile column with a pyqtgraph PlotDataItem."""

    #- Display formats for vector digital signals.
    DIGITAL_FORMATS = ('hex', 'dec', 'bin')

    def __init__(self, wfile, key, xaxis):
        self.wfile = wfile
        self.key = key
        self.xaxis = xaxis
        self.x = None
        self.y = None
        self.xlabel = "Samples"
        self.xunit = ""
        #- Digital metadata, populated from df.attrs['cicsim_vcd'] when
        #- the source is a VCD file. ``digital_kind`` is one of
        #- 'bit' / 'vector' / None; ``digital_width`` is the bit width
        #- (1 for bits); ``digital_format`` selects how vector samples
        #- are displayed in tooltips/labels ('hex' / 'dec' / 'bin').
        self.digital_kind = None
        self.digital_width = 1
        self.digital_format = 'hex'
        #- Whether to render this wave in the dedicated digital pane
        #- (one row per signal, gtkwave/surfer-style). Off by default;
        #- the user opts in via the wave-tree right-click menu.
        self.show_as_digital = False
        #- Original (string/int) values for digital signals, kept so we
        #- can re-render labels when the format changes.
        self._digital_raw = None
        self.yunit, self._yscale, self._yclean = self._infer_unit(
            key, default="V" if self._is_v(key)
            else "A" if self._is_i(key) else "")
        self.ylabel = "%s (%s)" % (self._yclean or key, wfile.name)
        self.logx = False
        self.tag = wfile.getTag(key)
        self.curve = None
        self.color = None
        self._xlabels = None
        self._ylabels = None
        self.reload()

    @staticmethod
    def _is_v(key):
        kl = (key or "").lower()
        return kl.startswith("v(") or kl.startswith("v-")

    @staticmethod
    def _is_i(key):
        kl = (key or "").lower()
        return kl.startswith("i(") or kl.startswith("i-")

    @staticmethod
    def _infer_unit(key, default=""):
        """Return ``(unit, scale, clean_label)`` for ``key``.

        Tries the suffix parser first (handles ``Foo_dBm``, ``Bar [MHz]``,
        ``Baz (V)`` etc); falls back to ``default`` when no suffix is
        recognised.
        """
        parsed = parse_unit_from_name(key)
        if parsed is not None:
            scale, unit, clean = parsed
            return unit, scale, clean
        return default, 1.0, key

    @staticmethod
    def _infer_yunit(key):
        # Kept for backwards compatibility (used by older code paths /
        # tests). Prefer ``_infer_unit``.
        unit, _scale, _clean = PgWave._infer_unit(
            key, default="V" if PgWave._is_v(key)
            else "A" if PgWave._is_i(key) else "")
        return unit

    def _set_x_from_column(self, col, label, unit, logx=False):
        arr = self.wfile.df[col].to_numpy()
        # Auto-rescale prefixed-SI columns so EngFormatter shows nice
        # prefixes regardless of the unit the data was stored in.
        parsed = parse_unit_from_name(col)
        if parsed is not None:
            scale, base_unit, clean = parsed
            arr = arr * scale if scale != 1.0 else arr
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
            self._set_x_from_column(self.xaxis, self.xaxis, "")
        else:
            # No known x-axis name; pick the first column that carries a
            # parseable unit suffix and isn't the y-key itself.
            for col in keys:
                if col == self.key:
                    continue
                if parse_unit_from_name(col) is not None:
                    self._set_x_from_column(col, col, "")
                    break

        if self.key in keys:
            y = self.wfile.df[self.key].to_numpy()
            if self._yscale != 1.0 and self._yscale != 1:
                try:
                    y = y * self._yscale
                except TypeError:
                    pass  # non-numeric (digital) data; ignore scale
            self.y = y

        self._maybe_apply_digital_kind()

        if self.curve and self.x is not None and self.y is not None:
            x, _ = _to_numeric(self.x)
            y, _ = _to_numeric(self.y)
            self.curve.setData(x, y)

    def _maybe_apply_digital_kind(self):
        """If this signal comes from a digital source (VCD), record the
        kind/width and convert ``self.y`` into a numeric step trace.

        The original strings/ints are kept on ``self._digital_raw`` so
        we can re-render labels when the user switches hex/dec/bin.
        """
        attrs = getattr(self.wfile.df, 'attrs', {}) or {}
        meta = attrs.get('cicsim_vcd')
        if not meta:
            return
        kinds = meta.get('kinds', {}) or {}
        widths = meta.get('widths', {}) or {}
        kind = kinds.get(self.key)
        if kind not in ('bit', 'vector'):
            return

        self.digital_kind = kind
        self.digital_width = int(widths.get(self.key, 1) or 1)
        self._digital_raw = self.y

        if kind == 'bit':
            #- Map '0' -> 0.0, '1' -> 1.0, anything else (x/z/h/l) -> NaN
            #- so the curve has visible breaks for unknown states.
            yn = np.full(len(self.y), np.nan, dtype=np.float64)
            for i, v in enumerate(self.y):
                if v == '1' or v == 1:
                    yn[i] = 1.0
                elif v == '0' or v == 0:
                    yn[i] = 0.0
            self.y = yn
            self.yunit = "bit"
            self._yclean = self.key
            self.ylabel = "%s (bit, %s)" % (self.key, self.wfile.name)
        else:
            #- Vector: numeric value (or NaN for unknown).
            yn = np.full(len(self.y), np.nan, dtype=np.float64)
            for i, v in enumerate(self.y):
                if isinstance(v, (int, np.integer)):
                    yn[i] = float(v)
                elif isinstance(v, float) and not np.isnan(v):
                    yn[i] = v
            self.y = yn
            unit = "u%d" % self.digital_width  # e.g. "u8"
            self.yunit = unit
            self._yclean = self.key
            self.ylabel = "%s [%s, %s]" % (
                self.key, unit, self.wfile.name)

    def setDigitalFormat(self, fmt):
        """Switch how vector samples are displayed (hex/dec/bin)."""
        if fmt not in self.DIGITAL_FORMATS:
            return
        self.digital_format = fmt

    def synthesizeDigitalBits(self, hysteresis_frac=0.05):
        """Return a ``"0"/"1"/"x"`` array derived from analog ``self.y``.

        The mid-amplitude threshold ``(min+max)/2`` decides high vs low.
        A small hysteresis band (default 5% of the peak-to-peak swing)
        on either side of the threshold prevents repeated false
        transitions from noise crossing the line. Samples that fall
        inside the hysteresis band hold the previous state. NaN /
        non-finite samples become ``"x"``.

        Caches the result on ``self._digital_raw`` so the digital pane
        doesn't recompute on every redraw.
        """
        y = self.y
        if y is None or len(y) == 0:
            return np.array([], dtype=object)
        try:
            yf = np.asarray(y, dtype=float)
        except (TypeError, ValueError):
            return np.array(['x'] * len(y), dtype=object)
        finite_mask = np.isfinite(yf)
        if not finite_mask.any():
            return np.array(['x'] * len(yf), dtype=object)
        ymin = float(np.min(yf[finite_mask]))
        ymax = float(np.max(yf[finite_mask]))
        span = ymax - ymin
        if span <= 0:
            #- Constant signal: report a single state.
            out = np.array(['1' if ymax > 0 else '0'] * len(yf),
                           dtype=object)
            return out
        mid = (ymin + ymax) / 2.0
        hyst = max(span * float(hysteresis_frac), 0.0)
        hi_th = mid + hyst
        lo_th = mid - hyst

        out = np.empty(len(yf), dtype=object)
        state = 'x'  # before the first finite sample
        for i, v in enumerate(yf):
            if not np.isfinite(v):
                out[i] = 'x'
                continue
            if state == 'x':
                state = '1' if v >= mid else '0'
            elif state == '0' and v >= hi_th:
                state = '1'
            elif state == '1' and v <= lo_th:
                state = '0'
            #- else: inside the hysteresis band -> hold state.
            out[i] = state
        return out

    def formatDigitalValue(self, raw):
        """Render a raw vector sample with the current format.

        ``raw`` may be the original VCD string ('x', 'z', '0', '1') or
        the numeric value we put in ``self.y`` (0.0 / 1.0 / NaN / int).
        """
        if raw is None or (isinstance(raw, float) and np.isnan(raw)):
            return "x"
        if isinstance(raw, str):
            return raw  # 'x' / 'z' / lowercase bits
        if self.digital_kind == 'bit':
            try:
                return "1" if int(round(float(raw))) else "0"
            except (TypeError, ValueError):
                return str(raw)
        try:
            iv = int(round(float(raw)))
        except (TypeError, ValueError):
            return str(raw)
        w = max(1, int(self.digital_width or 1))
        if self.digital_format == 'hex':
            digits = max(1, (w + 3) // 4)
            return ("%0*x" % (digits, iv & ((1 << w) - 1))).lower() + "h"
        if self.digital_format == 'bin':
            return ("{:0%db}" % w).format(iv & ((1 << w) - 1)) + "b"
        return str(iv)

    @staticmethod
    def _apply_render_opts(curve):
        """Per-curve options safe to apply at construction time.

        ``autoDownsample`` and ``clipToView`` are NOT set here -- they
        slice the data array using the ViewBox's current rect, but at
        construction the ViewBox still holds its default
        ``(-0.5, -0.5, 1, 1)`` rect (autoRange has not run yet because
        the first curve is still being added). With a 7e-6 s data span
        and a 1.0 unit view rect, autoDownsample picks a downsample
        factor of ~300 000, collapsing the curve to a single point;
        clipToView then keeps it that way. The resulting empty plot is
        what users saw on macOS. Those options are applied by
        :meth:`_enable_view_dependent_opts` after ``autoRange()``.

        ``setDynamicRangeLimit`` IS safe at construction: it clamps
        y-values relative to the view rect at draw time (not at
        ``setData`` time), so it never collapses the data. Setting it
        here suppresses Qt's "Painter path exceeds +/-32767 pixels"
        warnings that fire when a curve has tall spikes (e.g. a power
        rail transient) and the user zooms in: without dynamic range
        limiting the painter receives y-coords millions of pixels
        outside the viewport, which exceeds Qt's int16 path range.
        """
        if curve is None:
            return
        try:
            #- 1e6 is pyqtgraph's own default; we set it explicitly so
            #- the limiter is active even on PlotDataItem subclasses
            #- that may have it disabled, and to make the intent
            #- visible. Tightening below 1e6 risks visible clipping
            #- on legitimate large-dynamic-range signals.
            curve.setDynamicRangeLimit(1e6)
        except Exception:
            pass
        return

    @staticmethod
    def _enable_view_dependent_opts(curve):
        """Enable ``setDownsampling(auto=True)`` and ``clipToView`` once
        the ViewBox has a real view rect.

        Must be invoked after ``autoRange()`` so the visible-range slice
        actually contains data; otherwise the curve renders empty.
        Silently no-ops on items that don't support these options
        (e.g. ``InfiniteLine``, ``PlotCurveItem``).
        """
        if curve is None:
            return
        try:
            curve.setDownsampling(auto=True, method='subsample')
        except Exception:
            pass
        try:
            curve.setClipToView(True)
        except Exception:
            opts = getattr(curve, 'opts', None)
            if isinstance(opts, dict):
                opts['clipToView'] = True
        #- Dynamic range limit: see ``_apply_render_opts``. Also set
        #- here so digital-pane PlotDataItems (which skip the
        #- ``Wave.plot`` path) get the same Qt 16-bit-painter
        #- protection.
        try:
            curve.setDynamicRangeLimit(1e6)
        except Exception:
            pass

    def plot(self, target, color='w', style='Lines', width=2):
        """Plot on a PlotItem or ViewBox. Returns the curve or None."""
        if self.y is None:
            return None
        y, self._ylabels = _to_numeric(self.y)
        x, self._xlabels = _to_numeric(self.x) if self.x is not None else (np.arange(len(y)), None)
        self.color = color
        self.style = style
        self._width = width
        kw = _style_kwargs(color, style, width=width)
        if self.digital_kind is not None:
            #- Digital signals look right only as left-step plots; we
            #- also disable antialiasing so transitions stay sharp.
            kw['stepMode'] = 'left'
            kw['connect'] = 'finite'
        self.curve = pg.PlotDataItem(x, y, name=self.ylabel, **kw)
        target.addItem(self.curve)
        self._apply_render_opts(self.curve)
        return self.curve

    def setStyle(self, style):
        if self.curve is None:
            return
        self.style = style
        vb = self.curve.getViewBox()
        vb.removeItem(self.curve)
        y, _ = _to_numeric(self.y)
        x, _ = _to_numeric(self.x) if self.x is not None else (np.arange(len(y)), None)
        kw = _style_kwargs(self.color, style, width=self._width)
        self.curve = pg.PlotDataItem(x, y, name=self.ylabel, **kw)
        vb.addItem(self.curve)
        self._apply_render_opts(self.curve)

    def setWidth(self, width):
        if self.curve is None:
            return
        self._width = width
        vb = self.curve.getViewBox()
        vb.removeItem(self.curve)
        y, _ = _to_numeric(self.y)
        x, _ = _to_numeric(self.x) if self.x is not None else (np.arange(len(y)), None)
        kw = _style_kwargs(self.color, self.style, width=width)
        self.curve = pg.PlotDataItem(x, y, name=self.ylabel, **kw)
        vb.addItem(self.curve)
        self._apply_render_opts(self.curve)

    def remove(self):
        if self.curve:
            self.curve.getViewBox().removeItem(self.curve)
            self.curve = None
        self.color = None


class _DropUrlTree(QTreeWidget):
    """File / wave lists: accept external file drops (viewport-safe)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                p = url.toLocalFile()
                if p and os.path.isfile(p):
                    event.acceptProposedAction()
                    return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                p = url.toLocalFile()
                if p and os.path.isfile(p):
                    event.acceptProposedAction()
                    return
        super().dragMoveEvent(event)

    def dropEvent(self, event):
        win = self.window()
        if hasattr(win, '_handle_file_drop'):
            win._handle_file_drop(event)
        else:
            event.ignore()


class PgWaveBrowser(QWidget):
    waveSelected = Signal(object)
    waveRemoveRequested = Signal(object)
    analysisRequested = Signal(str, object)  # (analysis_type, wave)
    styleChanged = Signal(str)
    fileRemoveRequested = Signal(str)
    wavePlotAllRequested = Signal(str)
    wavePlotAllVisibleRequested = Signal()

    def __init__(self, xaxis, parent=None):
        super().__init__(parent)
        self.xaxis = xaxis
        self.files = WaveFiles()
        self._wave_cache = {}
        self._tag_to_item = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)

        self.file_tree = _DropUrlTree()
        self.file_tree.setHeaderLabel("Files")
        self.file_tree.currentItemChanged.connect(self._file_selected)
        #- Allow shift/ctrl/cmd-click multi-select so the user can close
        #- many files at once via the context menu.
        self.file_tree.setSelectionMode(
            QAbstractItemView.ExtendedSelection)
        self.file_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_tree.customContextMenuRequested.connect(
            self._file_context_menu)

        style_row = QHBoxLayout()
        style_row.addWidget(QLabel("Style:"))
        self.style_cb = QComboBox()
        self.style_cb.addItems(PLOT_STYLES)
        self.style_cb.setToolTip("Plot style for all waves")
        self.style_cb.currentTextChanged.connect(self.styleChanged.emit)
        style_row.addWidget(self.style_cb)
        style_row.addStretch()

        search_row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Regex filter...")
        self.search.setToolTip(
            "Regex search filter\n"
            "───────────────────\n"
            ".        any character\n"
            ".*       match anything\n"
            "^abc     starts with abc\n"
            "abc$     ends with abc\n"
            "[abc]    a, b, or c\n"
            "a|b      a or b\n"
            "\\(       literal (\n"
            "Examples:\n"
            "  v\\(.*out   match v(...out\n"
            "  ^i\\(       current signals"
        )
        self.search.textChanged.connect(self._fill_waves)
        self._flat_mode = False
        self.flat_cb = QCheckBox("Flat")
        self.flat_cb.setToolTip("Show flat list instead of hierarchy")
        self.flat_cb.toggled.connect(self._toggle_flat)
        search_row.addWidget(self.search)
        search_row.addWidget(self.flat_cb)

        self.wave_tree = _DropUrlTree()
        self.wave_tree.setHeaderLabel("Waves")
        self.wave_tree.itemDoubleClicked.connect(self._wave_clicked)
        self.wave_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.wave_tree.customContextMenuRequested.connect(self._wave_context)

        layout.addWidget(self.file_tree, 1)
        layout.addLayout(style_row)
        layout.addLayout(search_row)
        layout.addWidget(self.wave_tree, 3)

    @property
    def plotStyle(self):
        return self.style_cb.currentText()

    def openFile(self, fname, sheet_name=None):
        sheet = sheet_name if sheet_name is not None else 0
        f = self.files.open(fname, self.xaxis, sheet_name=sheet)
        key = self.files.current
        item = QTreeWidgetItem([f.name])
        item.setData(0, Qt.UserRole, key)
        self.file_tree.addTopLevelItem(item)
        self.file_tree.setCurrentItem(item)
        self._fill_waves()

    def openDataFrame(self, df, name, pivot_spec_path=None,
                       original_path=None):
        f = self.files.openDataFrame(df, name, self.xaxis)
        if pivot_spec_path:
            f._pivot_spec_path = pivot_spec_path
        if original_path:
            f._original_path = original_path
        key = self.files.current
        item = QTreeWidgetItem([f.name])
        item.setData(0, Qt.UserRole, key)
        self.file_tree.addTopLevelItem(item)
        self.file_tree.setCurrentItem(item)
        self._fill_waves()

    def setWaveColor(self, tag, color):
        """Color a wave tree item to match its plot line."""
        item = self._tag_to_item.get(tag)
        if item:
            from PySide6.QtGui import QColor
            item.setForeground(0, QColor(color))

    def clearWaveColor(self, tag):
        """Reset a wave tree item color back to default."""
        item = self._tag_to_item.get(tag)
        if item:
            from PySide6.QtGui import QColor
            item.setForeground(0, QColor(_get_theme()['tree_default_fg']))

    def _file_selected(self, current, previous):
        if current:
            fname = current.data(0, Qt.UserRole)
            self.files.select(fname)
            self._fill_waves()

    def _file_context_menu(self, pos):
        item = self.file_tree.itemAt(pos)
        if not item:
            return
        #- If the user right-clicks on an unselected item, treat it as
        #- a single-item action (don't carry over a stale selection).
        #- If they right-click on one of several already-selected items,
        #- act on the whole selection.
        selected = self.file_tree.selectedItems()
        if item not in selected:
            self.file_tree.clearSelection()
            item.setSelected(True)
            selected = [item]

        keys = [it.data(0, Qt.UserRole) for it in selected
                if it.data(0, Qt.UserRole)]
        if not keys:
            return

        menu = QMenu(self)
        label = ("Close" if len(keys) == 1
                 else "Close %d files" % len(keys))
        menu.addAction(
            label,
            lambda ks=tuple(keys): [
                self.fileRemoveRequested.emit(k) for k in ks])
        menu.exec(self.file_tree.viewport().mapToGlobal(pos))

    def _purge_wave_cache_for_wfile(self, wf):
        for yname in wf.getWaveNames():
            self._wave_cache.pop(wf.getTag(yname), None)

    def remove_file_entry(self, key):
        """Remove a file from the model and file tree (plots/cache cleared elsewhere)."""
        self.files.remove(key)
        for i in range(self.file_tree.topLevelItemCount()):
            it = self.file_tree.topLevelItem(i)
            if it.data(0, Qt.UserRole) == key:
                self.file_tree.takeTopLevelItem(i)
                break
        self._sync_file_selection_after_remove()

    def _sync_file_selection_after_remove(self):
        cur = self.files.current
        if cur is None:
            self.wave_tree.clear()
            self._tag_to_item = {}
            return
        for i in range(self.file_tree.topLevelItemCount()):
            it = self.file_tree.topLevelItem(i)
            if it.data(0, Qt.UserRole) == cur:
                self.file_tree.setCurrentItem(it)
                break
        self._fill_waves()

    def _toggle_flat(self, checked):
        self._flat_mode = checked
        self._fill_waves()

    @staticmethod
    def _parse_hierarchy(name):
        """Split a hierarchical signal name into its scope path.

        Examples:
            ``v(xdut.x1.node)``       -> ``['xdut', 'x1', 'v(node)']``
            ``i(M1.d)``               -> ``['M1', 'i(d)']``
            ``test.dut_ana.PWRUP_1V8`` -> ``['test', 'dut_ana', 'PWRUP_1V8']``
            ``count``                 -> ``['count']``

        Plain dot-separated names (VCD-style scoped signals) are split
        the same way. Names with no dots stay at the top level.
        """
        m = re.match(r'^([vi])\((.+)\)$', name)
        if m:
            prefix = m.group(1)
            inner = m.group(2)
            parts = inner.split('.')
            if len(parts) > 1:
                leaf = "%s(%s)" % (prefix, parts[-1])
                return parts[:-1] + [leaf]
            return [name]
        if '.' in name and not any(c in name for c in '()/[] '):
            #- Plain dotted path (VCD/Verilog-style hierarchy). We only
            #- treat it as hierarchy when there are no parens/brackets/
            #- spaces, so SPICE-style names like ``v(net.node)`` aren't
            #- accidentally split a second time.
            parts = name.split('.')
            return parts
        return [name]

    def _visible_wave_names(self):
        """Wave names that match the regex filter (shown in the browser tree)."""
        f = self.files.getSelected()
        if f is None:
            return []
        pattern = self.search.text()
        return [n for n in f.getWaveNames()
                if not pattern or re.search(pattern, n, re.IGNORECASE)]

    def _fill_waves(self):
        self.wave_tree.clear()
        self._tag_to_item = {}
        f = self.files.getSelected()
        if f is None:
            return

        names = self._visible_wave_names()

        if self._flat_mode:
            for name in sorted(names):
                item = QTreeWidgetItem([name])
                item.setData(0, Qt.UserRole, name)
                self.wave_tree.addTopLevelItem(item)
                self._color_if_plotted(item, f, name)
            return

        root = {}
        for name in names:
            parts = self._parse_hierarchy(name)
            node = root
            for part in parts[:-1]:
                if part not in node:
                    node[part] = {}
                elif isinstance(node[part], str):
                    node[part] = {None: node[part]}
                node = node[part]
            leaf_key = parts[-1]
            if leaf_key in node and isinstance(node[leaf_key], dict):
                node[leaf_key][None] = name
            else:
                node[leaf_key] = name

        self._build_tree(self.wave_tree, root, f)

    def _build_tree(self, parent, node, wfile):
        for key in sorted(node.keys()):
            if key is None:
                continue
            value = node[key]
            if isinstance(value, str):
                item = QTreeWidgetItem([key])
                item.setData(0, Qt.UserRole, value)
                self._attach(parent, item)
                self._color_if_plotted(item, wfile, value)
            else:
                item = QTreeWidgetItem([key])
                if None in value:
                    item.setData(0, Qt.UserRole, value[None])
                    self._color_if_plotted(item, wfile, value[None])
                self._attach(parent, item)
                self._build_tree(item, value, wfile)

    @staticmethod
    def _attach(parent, item):
        if isinstance(parent, QTreeWidget):
            parent.addTopLevelItem(item)
        else:
            parent.addChild(item)

    def _color_if_plotted(self, item, wfile, name):
        tag = wfile.getTag(name)
        self._tag_to_item[tag] = item
        if tag in self._wave_cache:
            wave = self._wave_cache[tag]
            if wave.color:
                from PySide6.QtGui import QColor
                item.setForeground(0, QColor(wave.color))

    def _wave_clicked(self, item, column):
        yname = item.data(0, Qt.UserRole)
        if not yname:
            item.setExpanded(not item.isExpanded())
            return
        f = self.files.getSelected()
        tag = f.getTag(yname)
        if tag not in self._wave_cache:
            self._wave_cache[tag] = PgWave(f, yname, self.xaxis)
        wave = self._wave_cache[tag]
        if wave.curve is not None:
            self.waveRemoveRequested.emit(wave)
            return
        wave.reload()
        self.waveSelected.emit(wave)

    def currentWave(self):
        """Return the wave currently focused in the wave tree, or
        ``None`` if no signal row is selected."""
        item = self.wave_tree.currentItem()
        if item is None:
            return None
        yname = item.data(0, Qt.UserRole)
        if not yname:
            return None
        f = self.files.getSelected()
        if f is None:
            return None
        tag = f.getTag(yname)
        if tag not in self._wave_cache:
            self._wave_cache[tag] = PgWave(f, yname, self.xaxis)
        return self._wave_cache[tag]

    def togglePlotAsDigital(self):
        """Toggle ``show_as_digital`` on the focused wave and request
        a re-plot. Triggered by the ``D`` keyboard shortcut."""
        wave = self.currentWave()
        if wave is None:
            return
        wave.show_as_digital = not wave.show_as_digital
        #- Bounce off the current pane (no-op if it wasn't plotted)
        #- and re-add: routing is decided by show_as_digital.
        self.waveRemoveRequested.emit(wave)
        self.waveSelected.emit(wave)

    def _wave_context(self, pos):
        item = self.wave_tree.itemAt(pos)
        f = self.files.getSelected()
        if f is None:
            return
        visible = self._visible_wave_names()
        if not visible:
            return

        def _plot_all_visible():
            self.wavePlotAllVisibleRequested.emit()

        if not item:
            menu = QMenu(self)
            menu.addAction("Plot all visible waves", _plot_all_visible)
            menu.exec(self.wave_tree.viewport().mapToGlobal(pos))
            return

        yname = item.data(0, Qt.UserRole)
        if not yname:
            menu = QMenu(self)
            menu.addAction("Plot all visible waves", _plot_all_visible)
            menu.exec(self.wave_tree.viewport().mapToGlobal(pos))
            return

        tag = f.getTag(yname)

        if tag not in self._wave_cache:
            self._wave_cache[tag] = PgWave(f, yname, self.xaxis)

        wave = self._wave_cache[tag]
        wave.reload()

        menu = QMenu(self)
        menu.addAction("Plot", lambda: self.waveSelected.emit(wave))
        menu.addAction(
            "Plot for all files",
            lambda n=yname: self.wavePlotAllRequested.emit(n))
        menu.addAction("Plot all visible waves", _plot_all_visible)
        if wave.curve:
            menu.addAction("Remove from plot",
                           lambda: self.waveRemoveRequested.emit(wave))
        style_menu = menu.addMenu("Style")
        for s in PLOT_STYLES:
            def _set_style(st=s):
                if wave.curve:
                    wave.setStyle(st)
                else:
                    self.style_cb.setCurrentText(st)
                    self.waveSelected.emit(wave)
            style_menu.addAction(s, _set_style)
        #- "Show as digital" toggles routing to the dedicated digital
        #- pane. Always offered: VCD bit/vector signals plot with their
        #- true sampled values; analog signals (e.g. SPICE .raw) get a
        #- synthesized bit trace based on a (min+max)/2 threshold +
        #- small hysteresis to suppress noise around the cross point.
        digi_label = ("✓ Show as digital" if wave.show_as_digital
                      else "Show as digital")

        def _toggle_digital(w=wave):
            w.show_as_digital = not w.show_as_digital
            #- If the wave is already on a plot, re-route it to the
            #- other pane by removing then re-adding it. The plot
            #- knows whether it has the wave via ``wave_data`` so
            #- both analog and digital removals are handled.
            self.waveRemoveRequested.emit(w)
            self.waveSelected.emit(w)
        menu.addAction(digi_label, _toggle_digital)
        if wave.digital_kind == 'vector':
            #- Hex / Dec / Bin only matter for multi-bit digital signals.
            digital_menu = menu.addMenu("Digital format")
            for fmt in PgWave.DIGITAL_FORMATS:
                fmt_label = fmt.capitalize()
                if wave.digital_format == fmt:
                    fmt_label = "● " + fmt_label

                def _set_fmt(w=wave, f=fmt):
                    w.setDigitalFormat(f)
                    self.waveSelected.emit(w)
                digital_menu.addAction(fmt_label, _set_fmt)
        menu.addSeparator()
        for label, atype in [("FFT / PSD", "fft"),
                             ("Histogram", "histogram"),
                             ("Differentiate (dy/dx)", "differentiate"),
                             ("X vs Y...", "xvy")]:
            menu.addAction(label, lambda t=atype: self.analysisRequested.emit(
                t, wave))
        menu.exec(self.wave_tree.viewport().mapToGlobal(pos))


class PgWavePlot(QWidget):
    """A single plot tab with automatic dual Y-axes, cursors, and readout."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)

        self.gw = pg.GraphicsLayoutWidget()
        layout.addWidget(self.gw, 1)

        font = _mono_font(9)
        self.readout = QTextEdit()
        self.readout.setReadOnly(True)
        self.readout.setMaximumHeight(120)
        self.readout.setFont(font)
        layout.addWidget(self.readout)

        self.status = QLabel("")
        self.status.setFont(font)
        layout.addWidget(self.status)

        self._apply_panel_style()

        self.plot = self.gw.addPlot(row=0, col=0)
        self.plot.showGrid(x=True, y=True)
        _apply_grid(self.plot)
        self.plot.vb.wheelEvent = lambda ev: self._on_wheel(ev)
        self._orig_mouseDragEvent = self.plot.vb.mouseDragEvent
        self.plot.vb.mouseDragEvent = self._on_mouse_drag

        #- Digital pane below the analog plot. One row per digital
        #- signal, fixed pixel height per row, x-axis linked to the
        #- analog plot. Hidden when no digital signals are plotted.
        self._digital_row_height = 28          # pixels per signal row
        self._digital_row_spacing = 4          # pixels between rows
        self._digital_padding = 8              # top/bottom padding
        self.digital_plot = self.gw.addPlot(row=1, col=0)
        self._init_digital_plot()
        #- One entry per visible digital wave: (wave, items_dict)
        #- where items_dict has the curve / labels / row index.
        self._digital_waves = {}

        self._unit_vb = {}
        #- Per-unit bookkeeping so we can demote the descriptive part of
        #- an axis label when a second curve with a different name is
        #- added to the same axis (only the unit is meaningful then).
        self._unit_axis_side = {}
        self._unit_axis_label = {}
        self._right_vb = None
        self._logx = False
        self._has_rotated_x = False

        self.wave_data = {}
        self._color_index = 0
        self._line_width = 2
        self._font_size = 9
        self._legend_visible = False
        self._legend = None

        self.cursor_a = None
        self.cursor_b = None
        self._cursor_a_lines = []
        self._cursor_b_lines = []
        self._delta_texts = []
        self._last_x = None
        self._annotations = []

        self.custom_xlabel = None
        self.custom_ylabel = None
        self.custom_title = None

        # Wheel-zoom coalescing: rapid wheel ticks (touchpad / high-rate
        # mice) are accumulated into a single deferred range update so we
        # don't trigger per-curve downsampling re-computation on every tick.
        self._wheel_pending_x_scale = 1.0
        self._wheel_pending_y_scale = 1.0
        self._wheel_pending_pos = None
        self._wheel_timer = QTimer(self)
        self._wheel_timer.setSingleShot(True)
        self._wheel_timer.setInterval(16)  # ~one frame at 60 Hz
        self._wheel_timer.timeout.connect(self._apply_pending_wheel_zoom)

        self.gw.scene().sigMouseMoved.connect(self._on_mouse_moved)

    def _apply_panel_style(self):
        theme = _get_theme()
        ss = "background-color: %s; color: %s;" % (
            theme['panel_bg'], theme['panel_fg'])
        self.readout.setStyleSheet(ss)
        self.status.setStyleSheet(ss + " padding: 2px;")

    # ------------------------------------------------------------------
    # Dual Y-axis management
    # ------------------------------------------------------------------

    def _all_viewboxes(self):
        vbs = [self.plot.vb]
        if self._right_vb is not None:
            vbs.append(self._right_vb)
        return vbs

    def _get_or_create_vb(self, yunit, ylabel_text=""):
        """Return the ViewBox for a given yunit, creating axes as needed.

        ``ylabel_text`` is the descriptive name used as the axis title text
        (e.g. ``"Amplitude"`` cleaned from ``"Amplitude_dBm"``). If empty
        the axis shows only the unit, as before.

        When a second wave with a *different* descriptive name lands on
        an existing axis, the descriptive part of the label is dropped
        so the axis only shows the unit (it would otherwise look like
        the axis only describes the first curve, which is misleading).
        """
        if yunit in self._unit_vb:
            self._maybe_demote_axis_label(yunit, ylabel_text)
            return self._unit_vb[yunit]

        if not self._unit_vb:
            self._unit_vb[yunit] = self.plot.vb
            self._unit_axis_side[yunit] = 'left'
            self._unit_axis_label[yunit] = ylabel_text or ""
            if yunit or ylabel_text:
                self.plot.setLabel('left', ylabel_text, units=yunit)
            return self.plot.vb

        if self._right_vb is None:
            self._right_vb = pg.ViewBox()
            self.plot.showAxis('right')
            self.plot.scene().addItem(self._right_vb)
            self.plot.getAxis('right').linkToView(self._right_vb)
            self._right_vb.setXLink(self.plot)
            self.plot.vb.sigResized.connect(self._sync_right_vb)
            self._sync_right_vb()
            self._right_vb.wheelEvent = lambda ev: self._on_wheel(ev)
            self._right_vb.mouseDragEvent = self._on_mouse_drag

        self._unit_vb[yunit] = self._right_vb
        self._unit_axis_side[yunit] = 'right'
        self._unit_axis_label[yunit] = ylabel_text or ""
        if yunit or ylabel_text:
            self.plot.setLabel('right', ylabel_text, units=yunit)

        self._ensure_cursors_on_right_vb()
        return self._right_vb

    def _maybe_demote_axis_label(self, yunit, new_label):
        """If a second curve on the same axis has a different name, drop
        the descriptive label so the axis only shows the unit."""
        side = self._unit_axis_side.get(yunit)
        if side is None:
            return
        existing = self._unit_axis_label.get(yunit, "")
        new_label = new_label or ""
        if not existing or existing == "<unit-only>":
            return
        if new_label and new_label != existing:
            self.plot.setLabel(side, "", units=yunit)
            self._unit_axis_label[yunit] = "<unit-only>"

    def _sync_right_vb(self):
        if self._right_vb:
            self._right_vb.setGeometry(self.plot.vb.sceneBoundingRect())

    def _ensure_cursors_on_right_vb(self):
        if self._right_vb is None:
            return
        theme = _get_theme()
        vbs = self._all_viewboxes()
        for i, vb in enumerate(vbs):
            if self.cursor_a is not None and i >= len(self._cursor_a_lines):
                line = self._make_cursor_line(
                    self.cursor_a, theme['cursor_a'], 'a')
                vb.addItem(line)
                self._cursor_a_lines.append(line)
            if self.cursor_b is not None and i >= len(self._cursor_b_lines):
                line = self._make_cursor_line(
                    self.cursor_b, theme['cursor_b'], 'b')
                vb.addItem(line)
                self._cursor_b_lines.append(line)

    # ------------------------------------------------------------------
    # Digital pane (under the analog x-axis)
    # ------------------------------------------------------------------

    def _init_digital_plot(self):
        """Set up the digital pane: link x to the analog plot, hide most
        chrome, and start hidden until a digital signal is added."""
        dp = self.digital_plot
        dp.hideButtons()
        dp.showAxis('left')
        dp.showAxis('bottom', False)
        dp.getAxis('left').setStyle(showValues=False)
        dp.getAxis('left').setTicks([])
        dp.getAxis('left').setWidth(self.plot.getAxis('left').width())
        dp.setMouseEnabled(x=True, y=False)
        dp.setMenuEnabled(False)
        dp.setXLink(self.plot)
        dp.vb.setLimits(yMin=0)  # rows live in [0, n_rows]
        dp.setVisible(False)
        #- Forward our wheel/drag handlers so the digital pane behaves
        #- like the analog plot for x-axis interaction.
        dp.vb.wheelEvent = lambda ev: self._on_wheel(ev)
        dp.vb.mouseDragEvent = self._on_mouse_drag
        #- Throttled label refresh on x-range changes: a wide view of
        #- a 16k-transition vector would otherwise create 16k TextItems
        #- and freeze the UI. We render at most ``_DIGITAL_MAX_LABELS``
        #- labels per signal, only for transitions inside the current
        #- view rect, and refresh on demand.
        from PySide6.QtCore import QTimer as _QT
        self._digital_label_timer = _QT()
        self._digital_label_timer.setSingleShot(True)
        self._digital_label_timer.setInterval(60)
        self._digital_label_timer.timeout.connect(
            self._update_visible_digital_labels)
        dp.vb.sigXRangeChanged.connect(
            lambda *_: self._digital_label_timer.start())

    #- Maximum number of value labels to draw per vector signal. A
    #- handful is plenty at any zoom level; more would only overlap.
    _DIGITAL_MAX_LABELS = 80

    def _digital_total_rows(self):
        return len(self._digital_waves)

    def _digital_row_pixel_height(self):
        n = self._digital_total_rows()
        if n == 0:
            return 0
        return (n * self._digital_row_height
                + max(0, n - 1) * self._digital_row_spacing
                + 2 * self._digital_padding)

    def _refresh_digital_pane_geometry(self):
        """Resize the digital pane to ``rows * row_height`` (pixels)."""
        n = self._digital_total_rows()
        dp = self.digital_plot
        if n == 0:
            dp.setVisible(False)
            return
        dp.setVisible(True)
        h = self._digital_row_pixel_height()
        dp.setMaximumHeight(h)
        dp.setMinimumHeight(h)
        dp.setYRange(0, n, padding=0)

    def _add_digital_wave(self, wave, color):
        """Place a digital signal in its own row in the digital pane."""
        row_idx = self._digital_total_rows()  # bottom-up new row
        slot_top = row_idx + 1
        slot_bot = row_idx
        items = self._build_digital_items(wave, slot_bot, slot_top, color)
        self._digital_waves[wave.tag] = {
            'wave': wave, 'row': row_idx, 'items': items,
            'color': color, 'slot': (slot_bot, slot_top),
        }
        self._refresh_digital_pane_geometry()
        self._refresh_digital_left_axis()
        #- Re-apply view-dependent rendering opts now that the digital
        #- pane has a real y-range; otherwise auto-downsample would
        #- have computed a bogus factor against the default unit rect.
        for it in items.get('lines', []):
            PgWave._enable_view_dependent_opts(it)
        #- Render initial labels for the current view immediately so the
        #- user doesn't have to wait for the throttle timer.
        self._update_visible_digital_labels()

    _DIGITAL_AXIS_MAX_CHARS = 14

    def _refresh_digital_left_axis(self):
        """Show signal names on the left axis of the digital pane,
        one tick per row, centered vertically in the row.

        Names longer than ``_DIGITAL_AXIS_MAX_CHARS`` are truncated
        with an ellipsis ("…") so the axis stays narrow but every
        signal still gets *some* label. The axis width grows enough
        to comfortably fit the longest (truncated) label."""
        ax = self.digital_plot.getAxis('left')
        ticks = []
        max_len = 0
        for info in self._digital_waves.values():
            row = info['row']
            wave = info['wave']
            short = self._short_signal_name(wave.key)
            short = self._truncate_axis_label(short)
            max_len = max(max_len, len(short))
            ticks.append(((row + 0.5), short))
        ax.setTicks([ticks])
        ax.setStyle(showValues=True)
        #- ~7 px per char for the default axis font + padding.
        wanted = 12 + 7 * max_len
        ax.setWidth(max(80, wanted, self.plot.getAxis('left').width()))

    @classmethod
    def _truncate_axis_label(cls, name):
        """Truncate ``name`` to ``_DIGITAL_AXIS_MAX_CHARS`` keeping the
        leading and trailing characters. ``osc_temp_1v8`` (12 chars)
        passes through; ``a_very_long_signal_name`` becomes
        ``a_very_…name``. The trailing chars are usually the most
        identifying part (numeric suffix, leaf name)."""
        n = cls._DIGITAL_AXIS_MAX_CHARS
        if len(name) <= n:
            return name
        head = (n - 1) // 2
        tail = n - 1 - head
        return name[:head] + "…" + name[-tail:]

    @staticmethod
    def _short_signal_name(name):
        """Compact label for the digital pane left axis.

        ``test.dut_ana.osc`` -> ``osc``
        ``v(xdut.done)``     -> ``done``
        ``v(out)``           -> ``out``
        ``i(vdd)``           -> ``i(vdd)``  (current probes keep prefix)

        For digital rows we strip the ``v(...)`` wrapper entirely --
        the analog/voltage distinction is meaningless when we're
        showing 0/1 transitions, and the bare leaf name reads better
        next to gtkwave-style traces. Current probes (``i(...)``)
        keep their prefix because the ``i`` carries information.
        """
        m = re.match(r'^([vi])\((.+)\)$', name)
        if m:
            inner = m.group(2)
            leaf = inner.rsplit('.', 1)[-1]
            if m.group(1) == 'v':
                return leaf
            return "%s(%s)" % (m.group(1), leaf)
        if '.' in name:
            return name.rsplit('.', 1)[-1]
        return name

    def _build_digital_items(self, wave, y_lo, y_hi, color):
        """Construct the GraphicsItems for a digital wave row.

        Returns a dict with the items (so they can be removed later).

        Three cases:
        - true bit signal (VCD): use ``wave._digital_raw`` directly.
        - true vector signal (VCD): bus shape with on-demand labels.
        - any other waveform: synthesize a 0/1 trace from the analog
          data via :meth:`PgWave.synthesizeDigitalBits` and treat it
          as a bit signal.

        The ``color`` argument is ignored for the digital pane: traces
        are drawn in the theme's foreground color (white on dark,
        black on light) so the gtkwave/surfer-style waveforms read at
        a glance and don't compete with the analog rainbow above.
        """
        synth_kind = wave.digital_kind
        raw = wave._digital_raw
        if synth_kind not in ('bit', 'vector'):
            #- Analog wave: synthesize a bit trace.
            raw = wave.synthesizeDigitalBits()
            wave._digital_raw = raw  # cache for label refreshes
            synth_kind = 'bit'

        x_arr, _ = _to_numeric(wave.x) if wave.x is not None else (
            np.arange(len(raw or [])), None)
        items = {'lines': [], 'labels': []}
        if x_arr is None or len(x_arr) == 0 or raw is None:
            return items

        theme = _get_theme()
        mono = theme.get('pg_foreground', 'w')

        if synth_kind == 'bit':
            #- Bit row: standard step trace from y_lo (=0) to y_lo+0.8
            #- of the slot, with NaN for x/z so the line breaks.
            yvals = np.full(len(raw), np.nan, dtype=np.float64)
            mid = y_lo + 0.5
            top = y_lo + 0.85
            bot = y_lo + 0.15
            for i, v in enumerate(raw):
                if v == '1' or v == 1:
                    yvals[i] = top
                elif v == '0' or v == 0:
                    yvals[i] = bot
                #- x/z/h/l left as NaN -> draws a gap.
            curve = pg.PlotDataItem(
                x_arr, yvals,
                pen=pg.mkPen(mono, width=1.0),
                stepMode='left', connect='finite')
            self.digital_plot.addItem(curve)
            PgWave._enable_view_dependent_opts(curve)
            items['lines'].append(curve)
            #- Mid baseline so the row is visible even if all-x.
            base = pg.InfiniteLine(
                pos=mid, angle=0,
                pen=pg.mkPen(mono, width=0.5,
                             style=Qt.DotLine))
            self.digital_plot.addItem(base)
            items['lines'].append(base)
        else:
            #- Vector row: bus shape (two parallel lines forming a
            #- hexagon-like outline). Labels and vertical ticks are
            #- NOT drawn here; they are created on demand by
            #- :meth:`_update_visible_digital_labels` so we never
            #- materialise more than _DIGITAL_MAX_LABELS items per
            #- signal regardless of the underlying transition count.
            top = y_lo + 0.85
            bot = y_lo + 0.15
            top_y = np.full(len(raw), top, dtype=np.float64)
            bot_y = np.full(len(raw), bot, dtype=np.float64)
            #- Mark unknown ranges with NaN so the outline breaks.
            for i, v in enumerate(raw):
                if v is None or isinstance(v, str):
                    top_y[i] = np.nan
                    bot_y[i] = np.nan
            top_curve = pg.PlotDataItem(
                x_arr, top_y, pen=pg.mkPen(mono, width=1.0),
                stepMode='left', connect='finite')
            bot_curve = pg.PlotDataItem(
                x_arr, bot_y, pen=pg.mkPen(mono, width=1.0),
                stepMode='left', connect='finite')
            self.digital_plot.addItem(top_curve)
            self.digital_plot.addItem(bot_curve)
            PgWave._enable_view_dependent_opts(top_curve)
            PgWave._enable_view_dependent_opts(bot_curve)
            items['lines'].append(top_curve)
            items['lines'].append(bot_curve)
            #- Single curve carrying ALL transition ticks via
            #- ``connect='pairs'``: x = [t0_lo, t0_hi, t1_lo, t1_hi,...]
            #- with the y-array alternating bot/top. This replaces N
            #- per-tick PlotDataItems (which made pan/zoom slow when
            #- there are tens of thousands of transitions).
            ticks_curve = pg.PlotCurveItem(
                x=np.array([], dtype=np.float64),
                y=np.array([], dtype=np.float64),
                pen=pg.mkPen(mono, width=0.6),
                connect='pairs')
            self.digital_plot.addItem(ticks_curve)
            items['lines'].append(ticks_curve)
            items['ticks_curve'] = ticks_curve
            #- Pre-compute the transition index list so label refresh
            #- is just a binary search per refresh.
            items['transitions'] = self._vector_transitions(raw)
            items['x_arr'] = x_arr
            items['raw'] = raw
            items['y_mid'] = (top + bot) / 2.0
            items['y_lo'] = bot
            items['y_hi'] = top
            items['color'] = mono
            items['label_pool'] = []  # reused TextItems

        return items

    @staticmethod
    def _vector_transitions(raw):
        """Indices in ``raw`` where the vector value changes (incl. 0)."""
        out = [0]
        prev = raw[0] if len(raw) else None
        for i in range(1, len(raw)):
            v = raw[i]
            if v != prev:
                out.append(i)
                prev = v
        return out

    def _remove_digital_wave(self, tag):
        info = self._digital_waves.pop(tag, None)
        if info is None:
            return
        self._destroy_digital_items(info)
        #- Re-pack remaining rows so there are no gaps.
        remaining = list(self._digital_waves.values())
        self._digital_waves = {}
        for old in remaining:
            self._destroy_digital_items(old)
            self._add_digital_wave(old['wave'], old['color'])
        if not self._digital_waves:
            self._refresh_digital_pane_geometry()
        else:
            self._update_visible_digital_labels()

    def _destroy_digital_items(self, info):
        d = info.get('items') or {}
        for it in d.get('lines', []):
            self.digital_plot.removeItem(it)
        for lbl in d.get('label_pool', []):
            self.digital_plot.removeItem(lbl)

    def _refresh_digital_labels(self, wave):
        """Re-render value labels for a digital vector wave (after a
        format change). Just retriggers the on-demand label updater so
        every visible label gets rebuilt with the new format."""
        info = self._digital_waves.get(wave.tag)
        if info is None or wave.digital_kind != 'vector':
            return
        self._update_visible_digital_labels()

    def _update_visible_digital_labels(self):
        """Render value labels and transition ticks for the transitions
        currently inside the digital pane's view rect.

        - Vertical ticks for ALL visible transitions are drawn as a
          single ``PlotCurveItem`` with ``connect='pairs'`` (one buffer
          update vs N item creations -- much faster on pan/zoom).
        - Value labels are pooled and capped at
          ``_DIGITAL_MAX_LABELS`` per signal; pool entries past the
          visible count are hidden, never destroyed.
        """
        if not self._digital_waves:
            return
        try:
            xlo, xhi = self.digital_plot.vb.viewRange()[0]
        except Exception:
            return
        theme = _get_theme()
        label_color = theme.get('text_color', 'w')
        for tag, info in self._digital_waves.items():
            wave = info['wave']
            if wave.digital_kind != 'vector':
                continue
            d = info['items']
            transitions = d.get('transitions') or []
            x_arr = d.get('x_arr')
            raw = d.get('raw')
            ticks_curve = d.get('ticks_curve')
            if (x_arr is None or raw is None or not transitions
                    or ticks_curve is None):
                continue

            #- Find transitions inside [xlo, xhi]. Each transition is
            #- an index into x_arr; transitions are sorted, so use a
            #- numpy search rather than scanning.
            t_x = x_arr[np.asarray(transitions, dtype=np.int64)]
            lo_i = int(np.searchsorted(t_x, xlo, side='left'))
            hi_i = int(np.searchsorted(t_x, xhi, side='right'))
            visible_full = transitions[lo_i:hi_i]

            y_mid = d['y_mid']
            y_lo = d['y_lo']
            y_hi = d['y_hi']

            #- Update the vertical-ticks curve: 2 points per transition,
            #- alternating (x, y_lo) / (x, y_hi). This handles thousands
            #- of ticks in a single draw call.
            if visible_full:
                vis_x = x_arr[np.asarray(visible_full, dtype=np.int64)]
                xs = np.repeat(vis_x, 2)
                ys = np.tile([y_lo, y_hi], len(visible_full))
                ticks_curve.setData(xs, ys, connect='pairs')
            else:
                ticks_curve.setData([], [])

            #- Always render up to _DIGITAL_MAX_LABELS visible
            #- transitions in order. We deliberately do NOT filter by
            #- segment-vs-text width: a too-aggressive width filter
            #- silently dropped every long label (e.g. multi-digit
            #- hex), which was the user-visible "long text doesn't
            #- show" bug. Letting wide labels overhang into the next
            #- cell matches gtkwave/surfer behaviour and is what users
            #- expect.
            pool = d.setdefault('label_pool', [])
            font = _mono_font(self._font_size - 1)

            visible_lbl = []
            for ti in visible_full[:self._DIGITAL_MAX_LABELS]:
                visible_lbl.append((ti, wave.formatDigitalValue(raw[ti])))

            #- Grow the pool lazily.
            while len(pool) < len(visible_lbl):
                lbl = pg.TextItem(text="", color=label_color,
                                  anchor=(0, 0.5))
                lbl.setFont(font)
                self.digital_plot.addItem(lbl)
                pool.append(lbl)

            for i, (ti, txt) in enumerate(visible_lbl):
                xv = float(x_arr[ti])
                lbl = pool[i]
                lbl.setText(txt)
                lbl.setPos(xv, y_mid)
                lbl.show()
            for i in range(len(visible_lbl), len(pool)):
                pool[i].hide()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show_wave(self, wave, style='Lines'):
        """Plot a wave. Returns (tag, color) on success, else None.

        Digital signals (bit / vector, detected from VCD metadata) are
        placed in the dedicated digital pane below the analog x-axis
        rather than on the analog Y axes; everything else uses the
        usual axis-per-unit logic.
        """
        if wave.tag in self.wave_data:
            return None

        yunit = wave.yunit or ""
        # Cleaned-up name (e.g. "Amplitude" from "Amplitude_dBm"); falls
        # back to the raw key.
        yname = getattr(wave, "_yclean", None) or wave.key

        if not self.wave_data:
            xlabel = wave.xlabel or ""
            if wave.xunit or xlabel:
                self.plot.setLabel('bottom', xlabel, units=wave.xunit or "")
            if wave.logx:
                self.plot.setLogMode(x=True)
                self._logx = True

        theme = _get_theme()
        wcolors = theme['wave_colors']
        color = wcolors[self._color_index % len(wcolors)]
        self._color_index += 1

        if wave.show_as_digital:
            #- Route to the digital pane when the user has explicitly
            #- requested it (right-click "Show as digital"). Works for
            #- both true digital signals (VCD bit/vector) and analog
            #- waveforms (a synthesized bit trace is computed via a
            #- mid-amplitude threshold + small hysteresis to suppress
            #- noise around the cross point).
            self._add_digital_wave(wave, color)
            self.wave_data[wave.tag] = (wave, yunit)
            try:
                xr = self.plot.vb.viewRange()[0]
                self.digital_plot.vb.setXRange(*xr, padding=0)
            except Exception:
                pass
            self._update_readout()
            return (wave.tag, color)

        vb = self._get_or_create_vb(yunit, ylabel_text=yname)

        if vb is self.plot.vb:
            curve = wave.plot(self.plot, color=color, style=style,
                              width=self._line_width)
        else:
            curve = wave.plot(vb, color=color, style=style,
                              width=self._line_width)
            if self._logx and curve:
                curve.setLogMode(True, False)

        if curve is None:
            return None

        self.wave_data[wave.tag] = (wave, yunit)

        if wave._xlabels and not self._has_rotated_x:
            ticks = list(zip(range(len(wave._xlabels)), wave._xlabels))
            _apply_rotated_ticks(self.plot, 'bottom', ticks)
            self._has_rotated_x = True

        if vb is self.plot.vb:
            self.plot.vb.enableAutoRange()
            self.plot.vb.autoRange()
        else:
            vb.enableAutoRange()
            vb.autoRange()

        #- Enable autoDownsample and clipToView only AFTER autoRange so
        #- the curve has a valid view rect; otherwise the first display
        #- would clip / over-downsample against the empty default rect
        #- (~300 000x downsample for transient data) and render no
        #- points -- the bug that made macOS plots appear blank.
        PgWave._enable_view_dependent_opts(curve)

        self._update_readout()
        return (wave.tag, color)

    def removeLine(self, wave):
        """Remove a single wave from the plot. Returns the tag if removed."""
        tag = wave.tag
        if tag in self.wave_data:
            self._remove_wave(tag)
            self._update_readout()
            return tag
        return None

    def removeAll(self):
        tags = list(self.wave_data.keys())
        for tag in tags:
            self._remove_wave(tag)
        self._reset_axes()
        self._update_readout()
        return tags

    def remove_waves_for_wfile(self, wf):
        """Remove all traces that belong to WaveFile *wf* (same object identity)."""
        tags = [tag for tag, (wave, _) in self.wave_data.items()
                if wave.wfile is wf]
        for tag in tags:
            self._remove_wave(tag)
        if not self.wave_data:
            self._reset_axes()
        self._update_readout()
        return tags

    def autoSize(self):
        """Fit every axis to its full data extent.

        ``clipToView`` and ``autoDownsample`` both make
        :meth:`PlotCurveItem.dataBounds` report only the *currently
        displayed* slice, so a naive ``autoRange()`` after a zoom-in
        would just refit to that slice (looking like a one-step undo).
        Temporarily disable both options on every curve, refit, then
        restore them so the next viewport change still gets the
        rendering optimisations.
        """
        curves = []
        for tag, (wave, _) in self.wave_data.items():
            if wave.curve is not None:
                curves.append(wave.curve)

        saved = []
        for c in curves:
            saved.append((c,
                          c.opts.get('clipToView', False),
                          c.opts.get('autoDownsample', False)))
            try:
                c.setClipToView(False)
            except Exception:
                c.opts['clipToView'] = False
            try:
                c.setDownsampling(auto=False)
            except Exception:
                pass

        try:
            for vb in self._all_viewboxes():
                vb.enableAutoRange()
                vb.autoRange()
        finally:
            for c, clip, ads in saved:
                if ads:
                    try:
                        c.setDownsampling(auto=True, method='subsample')
                    except Exception:
                        pass
                if clip:
                    try:
                        c.setClipToView(True)
                    except Exception:
                        c.opts['clipToView'] = True

    def zoomIn(self):
        self._keyboard_zoom(1.0 / ZOOM_FACTOR)

    def zoomOut(self):
        self._keyboard_zoom(ZOOM_FACTOR)

    def _keyboard_zoom(self, scale):
        vr = self.plot.vb.viewRange()
        xlo, xhi = vr[0]
        xmid = (xlo + xhi) / 2.0
        self.plot.vb.setXRange(
            xmid - (xmid - xlo) * scale,
            xmid + (xhi - xmid) * scale, padding=0)
        for vb in self._all_viewboxes():
            vr = vb.viewRange()
            ylo, yhi = vr[1]
            ymid = (ylo + yhi) / 2.0
            vb.setYRange(
                ymid - (ymid - ylo) * scale,
                ymid + (yhi - ymid) * scale, padding=0)

    def reloadAll(self):
        for tag, (wave, _) in self.wave_data.items():
            wave.reload()
        self.autoSize()

    def setAllStyles(self, style):
        for tag, (wave, _) in self.wave_data.items():
            wave.setStyle(style)

    def setLineWidth(self, width):
        self._line_width = width
        for tag, (wave, _) in self.wave_data.items():
            wave.setWidth(width)

    def setFontSize(self, size):
        self._font_size = size
        font = _mono_font(size)
        self.readout.setFont(font)
        self.status.setFont(font)
        for axis_name in ['bottom', 'left', 'right']:
            ax = self.plot.getAxis(axis_name)
            ax.setTickFont(font)
            ax.setStyle(tickFont=font)

    def toggleLegend(self):
        self._legend_visible = not self._legend_visible
        if self._legend:
            self._legend.scene().removeItem(self._legend)
            self._legend = None
        if self._legend_visible:
            self._legend = pg.LegendItem(offset=(30, 10))
            self._legend.setParentItem(self.plot.vb)
            for tag, (wave, _) in self.wave_data.items():
                if wave.curve:
                    self._legend.addItem(wave.curve, wave.ylabel)

    def exportPdf(self):
        fname, _ = QFileDialog.getSaveFileName(
            self, "Export PDF", os.getcwd(),
            "PDF files (*.pdf);;PNG files (*.png);;SVG files (*.svg)")
        if not fname:
            return
        self._export_matplotlib(fname)

    def _export_matplotlib(self, fname):
        import matplotlib.pyplot as plt
        from matplotlib.ticker import EngFormatter
        from matplotlib.gridspec import GridSpec

        if not self.wave_data:
            return

        #- Two-pane layout: analog on top, digital strip below (only
        #- if there are digital waves). Height ratio mirrors the live
        #- viewer where each digital row is a thin strip.
        n_digital = len(self._digital_waves)
        if n_digital > 0:
            digital_h = 0.35 * n_digital  # inches per row
            fig = plt.figure(figsize=(10, 5 + digital_h))
            gs = GridSpec(2, 1, height_ratios=[5, digital_h], figure=fig,
                          hspace=0.05)
            ax = fig.add_subplot(gs[0, 0])
            ax_dig = fig.add_subplot(gs[1, 0], sharex=ax)
        else:
            fig, ax = plt.subplots(figsize=(10, 5))
            ax_dig = None

        units_left = set()
        units_right = set()
        ax_right = None
        tags = [t for t in self.wave_data.keys()
                if t not in self._digital_waves]

        theme = _get_theme()
        ecolors = theme['export_colors']

        for i, tag in enumerate(tags):
            wave, yunit = self.wave_data[tag]
            if wave.x is None or wave.y is None:
                continue
            x, xlabels = _to_numeric(wave.x)
            y, _ = _to_numeric(wave.y)
            color = ecolors[i % len(ecolors)]
            style = getattr(wave, 'style', 'Lines')

            is_right = (self._right_vb is not None
                        and yunit in self._unit_vb
                        and self._unit_vb[yunit] is self._right_vb)

            target = ax
            if is_right:
                if ax_right is None:
                    ax_right = ax.twinx()
                target = ax_right
                units_right.add(yunit)
            else:
                units_left.add(yunit)

            kw = dict(color=color, linewidth=1.5, label=wave.key)
            if style == 'Markers':
                kw.update(linestyle='none', marker='o', markersize=4)
            elif style == 'Lines+Markers':
                kw.update(marker='o', markersize=3)
            elif style == 'Steps':
                kw.update(drawstyle='steps-mid')

            if self._logx:
                target.semilogx(x, y, **kw)
            else:
                target.plot(x, y, **kw)

            if xlabels:
                ax.set_xticks(x)
                ax.set_xticklabels(xlabels, rotation=45, ha='right')

        if self.custom_xlabel:
            ax.set_xlabel(self.custom_xlabel)
        else:
            xunit = self._get_xunit()
            xlabel = ""
            for wave, _ in self.wave_data.values():
                if wave.xlabel:
                    xlabel = wave.xlabel
                    break
            if xunit:
                ax.set_xlabel("%s [%s]" % (xlabel, xunit) if xlabel else xunit)
                ax.xaxis.set_major_formatter(EngFormatter(unit=xunit))
            elif xlabel:
                ax.set_xlabel(xlabel)

        if self.custom_ylabel:
            ax.set_ylabel(self.custom_ylabel)
        else:
            for yu in units_left:
                if yu:
                    ax.set_ylabel("[%s]" % yu)
                    ax.yaxis.set_major_formatter(EngFormatter(unit=yu))
        if ax_right:
            for yu in units_right:
                if yu:
                    ax_right.set_ylabel("[%s]" % yu)
                    ax_right.yaxis.set_major_formatter(EngFormatter(unit=yu))

        if self.custom_title:
            ax.set_title(self.custom_title)

        for ann in self._annotations:
            ax.annotate(
                ann['text'], xy=(ann['x'], ann['y']),
                fontsize=8, color=theme['export_annotation_color'],
                bbox=dict(boxstyle='round,pad=0.3',
                          fc=theme['export_annotation_bg'],
                          ec=theme['export_annotation_ec'], alpha=0.9),
                arrowprops=dict(arrowstyle='->', color='#555555'))

        stats = self.getStats()
        if stats:
            stat_lines = []
            for s in stats:
                u = s['unit']
                stat_lines.append("%s: μ=%s σ=%s" % (
                    s['key'], _eng(s['mean'], u), _eng(s['std'], u)))
            fig.text(0.01, 0.01, "  |  ".join(stat_lines),
                     fontsize=6, color=theme['export_stats_color'],
                     va='bottom')

        lines, labels = ax.get_legend_handles_labels()
        if ax_right:
            r_lines, r_labels = ax_right.get_legend_handles_labels()
            lines += r_lines
            labels += r_labels
        if labels:
            ax.legend(lines, labels, fontsize=7, loc='best')

        ax.grid(True, alpha=0.3)

        #- Mirror the live viewer's zoom: read the X (and Y) ranges
        #- from the analog ViewBox and apply them to the matplotlib
        #- axes. Without this, matplotlib auto-ranges to the full
        #- data extent and the export ignores whatever the user had
        #- panned/zoomed to.
        try:
            xr = self.plot.vb.viewRange()[0]
            yr = self.plot.vb.viewRange()[1]
            ax.set_xlim(xr[0], xr[1])
            ax.set_ylim(yr[0], yr[1])
        except Exception:
            pass
        if ax_right is not None and self._right_vb is not None:
            try:
                yrr = self._right_vb.viewRange()[1]
                ax_right.set_ylim(yrr[0], yrr[1])
            except Exception:
                pass

        if ax_dig is not None:
            self._export_digital_pane(ax_dig, ax)
            #- Hide the analog x-tick labels because they're shown on
            #- the digital pane (which sits below and shares the axis).
            plt.setp(ax.get_xticklabels(), visible=False)
            ax.set_xlabel("")

        fig.tight_layout()
        fig.subplots_adjust(bottom=max(0.15, fig.subplotpars.bottom))
        dpi = 150 if fname.lower().endswith('.png') else None
        fig.savefig(fname, dpi=dpi, facecolor='white')
        plt.close(fig)

    # ------------------------------------------------------------------
    # Data export (plotted waveforms -> CSV/TSV/Parquet/Feather/HDF5)
    # ------------------------------------------------------------------

    #- Extension -> (pandas writer attribute, kwargs, format label)
    #- HDF5 needs a key; Feather/Parquet are columnar and lossless.
    _EXPORT_DATA_WRITERS = {
        '.csv':     ('to_csv',     {'index': False}),
        '.tsv':     ('to_csv',     {'index': False, 'sep': '\t'}),
        '.txt':     ('to_csv',     {'index': False, 'sep': '\t'}),
        '.parquet': ('to_parquet', {'index': False}),
        '.feather': ('to_feather', {}),
        '.h5':      ('to_hdf',     {'key': 'cicwave', 'mode': 'w'}),
        '.hdf5':    ('to_hdf',     {'key': 'cicwave', 'mode': 'w'}),
    }

    def exportData(self):
        """Save the currently plotted analog waves to a data file.

        Writes one column per (X, Y) pair side-by-side so heterogeneous
        x-grids are preserved without resampling. The current x-view
        range is honoured (zoom in to export a region). Digital pane
        traces are skipped — those are better viewed than tabulated.
        """
        exts = ";;".join([
            "CSV (*.csv)",
            "TSV (*.tsv)",
            "Parquet (*.parquet)",
            "Feather (*.feather)",
            "HDF5 (*.h5)",
        ])
        fname, _ = QFileDialog.getSaveFileName(
            self, "Export Plotted Data", os.getcwd(),
            exts + ";;All Files (*)")
        if not fname:
            return
        try:
            n_traces, n_rows = self._export_data_to(fname)
        except Exception as e:
            QMessageBox.critical(
                self, "Export failed",
                "Could not write %s:\n%s" % (fname, e))
            return
        QMessageBox.information(
            self, "Export complete",
            "Wrote %d trace(s), %d row(s) to:\n%s"
            % (n_traces, n_rows, fname))

    def _export_data_to(self, fname):
        """Write plotted-wave data to ``fname``. Returns (n_traces, n_rows).

        ``n_rows`` is the longest column length (others are NaN-padded
        to fit a rectangular DataFrame; the original arrays are
        preserved exactly within their length).
        """
        ext = os.path.splitext(fname)[1].lower()
        spec = self._EXPORT_DATA_WRITERS.get(ext)
        if spec is None:
            raise ValueError(
                "Unsupported export extension %r. Use one of: %s"
                % (ext, ", ".join(sorted(self._EXPORT_DATA_WRITERS))))
        writer_attr, kwargs = spec

        #- Skip the digital pane: it has its own representation
        #- (string '0'/'1'/'x' or vector ints) that doesn't round-trip
        #- cleanly into a numeric data file.
        tags = [t for t in self.wave_data.keys()
                if t not in self._digital_waves]
        if not tags:
            raise ValueError("No analog waves to export.")

        #- Honour the current x-zoom so "zoom in, export" gives the
        #- region of interest rather than the whole capture. Wrap in
        #- try/except: viewRange may raise on freshly-built plots in
        #- headless tests.
        try:
            xlo, xhi = self.plot.vb.viewRange()[0]
        except Exception:
            xlo, xhi = (None, None)

        columns = {}  # ordered insertion = preserved column order
        used_names = set()
        max_len = 0
        for tag in tags:
            wave, _yunit = self.wave_data[tag]
            if wave.x is None or wave.y is None:
                continue
            x = np.asarray(wave.x)
            y = np.asarray(wave.y)
            n = min(len(x), len(y))
            if n == 0:
                continue
            x = x[:n]
            y = y[:n]
            if xlo is not None and np.issubdtype(x.dtype, np.number):
                mask = (x >= xlo) & (x <= xhi)
                if mask.any():
                    x = x[mask]
                    y = y[mask]

            #- Make column names unique even if two waves share a key.
            xname = self._unique_col(
                wave.xlabel or "x", wave.xunit, used_names)
            yname = self._unique_col(
                wave.key or wave.ylabel or "y", wave.yunit, used_names)
            columns[xname] = x
            columns[yname] = y
            max_len = max(max_len, len(x))

        if not columns:
            raise ValueError("No exportable samples in current view.")

        #- Pad to a rectangular shape. NaN in unused tail rows is the
        #- least-surprising filler for numeric columns.
        padded = {}
        for name, arr in columns.items():
            if len(arr) < max_len:
                pad = np.full(max_len - len(arr), np.nan, dtype=float)
                padded[name] = np.concatenate([arr.astype(float), pad])
            else:
                padded[name] = arr
        df = pd.DataFrame(padded)

        getattr(df, writer_attr)(fname, **kwargs)
        return len(columns) // 2, max_len

    @staticmethod
    def _unique_col(base, unit, used):
        """Build a column name like ``time (s)`` and disambiguate
        collisions with ``__1``, ``__2``, ... suffixes."""
        name = base
        if unit:
            name = "%s (%s)" % (base, unit)
        candidate = name
        i = 1
        while candidate in used:
            candidate = "%s__%d" % (name, i)
            i += 1
        used.add(candidate)
        return candidate

    def _export_digital_pane(self, ax, ax_main):
        """Render the digital pane into ``ax`` for export.

        Mirrors the live viewer: bit signals as 0/1 step traces,
        vectors as bus outlines with value labels at every transition
        inside the current x-view.
        """
        if not self._digital_waves:
            return
        theme = _get_theme()
        mono = 'black'  # export background is white -> use black ink

        #- Use the analog axis x-range so the two panes align even if
        #- the user had zoomed the live view. matplotlib will sync via
        #- sharex once we set it on the main axis below.
        try:
            xlo, xhi = ax_main.get_xlim()
            if xhi <= xlo:
                xlo, xhi = self.plot.vb.viewRange()[0]
        except Exception:
            xlo, xhi = self.plot.vb.viewRange()[0]

        ax.set_xlim(xlo, xhi)
        n_rows = len(self._digital_waves)
        ax.set_ylim(0, n_rows)
        ax.set_yticks([])
        ax.grid(True, axis='x', alpha=0.2)
        for spine in ('top', 'right'):
            ax.spines[spine].set_visible(False)

        yticks = []
        yticklabels = []
        for info in self._digital_waves.values():
            wave = info['wave']
            row = info['row']
            slot_bot = row
            slot_top = row + 1
            yticks.append(row + 0.5)
            yticklabels.append(self._truncate_axis_label(
                self._short_signal_name(wave.key)))
            self._export_one_digital(ax, wave, slot_bot, slot_top, mono,
                                     xlo, xhi)

        ax.set_yticks(yticks)
        ax.set_yticklabels(yticklabels, fontsize=8)

        #- Forward x-axis formatting from the analog axis so units
        #- (e.g. seconds) show up the same way on the bottom strip.
        try:
            xfmt = ax_main.xaxis.get_major_formatter()
            ax.xaxis.set_major_formatter(xfmt)
        except Exception:
            pass

    def _export_one_digital(self, ax, wave, y_lo, y_hi, color, xlo, xhi):
        """Draw a single digital row into ``ax``."""
        synth_kind = wave.digital_kind
        raw = wave._digital_raw
        if synth_kind not in ('bit', 'vector'):
            raw = wave.synthesizeDigitalBits()
            synth_kind = 'bit'
        if raw is None or wave.x is None:
            return
        x_arr, _ = _to_numeric(wave.x)
        if x_arr is None or len(x_arr) == 0:
            return

        if synth_kind == 'bit':
            top = y_lo + 0.85
            bot = y_lo + 0.15
            yvals = np.full(len(raw), np.nan, dtype=np.float64)
            for i, v in enumerate(raw):
                if v == '1' or v == 1:
                    yvals[i] = top
                elif v == '0' or v == 0:
                    yvals[i] = bot
            ax.step(x_arr, yvals, where='post', color=color, linewidth=1.0)
            ax.axhline((top + bot) / 2.0, xmin=0, xmax=1,
                       color=color, linewidth=0.4, linestyle=':')
            return

        #- Vector: draw bus outline + transition ticks + labels.
        top = y_lo + 0.85
        bot = y_lo + 0.15
        mid = (top + bot) / 2.0
        top_y = np.full(len(raw), top, dtype=np.float64)
        bot_y = np.full(len(raw), bot, dtype=np.float64)
        for i, v in enumerate(raw):
            if v is None or isinstance(v, str):
                top_y[i] = np.nan
                bot_y[i] = np.nan
        ax.step(x_arr, top_y, where='post', color=color, linewidth=1.0)
        ax.step(x_arr, bot_y, where='post', color=color, linewidth=1.0)

        transitions = self._vector_transitions(raw)
        if not transitions:
            return
        t_x = x_arr[np.asarray(transitions, dtype=np.int64)]
        lo_i = int(np.searchsorted(t_x, xlo, side='left'))
        hi_i = int(np.searchsorted(t_x, xhi, side='right'))
        visible = list(range(max(0, lo_i - 1), min(len(transitions), hi_i)))

        fontsize = 6
        for vi in visible[:self._DIGITAL_MAX_LABELS]:
            idx = transitions[vi]
            tx = float(x_arr[idx])
            ax.plot([tx, tx], [bot, top], color=color, linewidth=0.5)
            txt = wave.formatDigitalValue(raw[idx])
            #- Anchor at the left edge of the segment (matches the
            #- live viewer's ``anchor=(0, 0.5)``). ``clip_on=False`` so
            #- a wide label can overhang the cell and still render.
            ax.text(tx, mid, " " + txt, fontsize=fontsize, color=color,
                    ha='left', va='center', clip_on=False)

    def clearCursors(self):
        for line in self._cursor_a_lines:
            line.getViewBox().removeItem(line)
        for line in self._cursor_b_lines:
            line.getViewBox().removeItem(line)
        self._cursor_a_lines.clear()
        self._cursor_b_lines.clear()
        self.cursor_a = None
        self.cursor_b = None
        self._clear_delta_texts()
        self._update_readout()

    def placeCursorA(self):
        if self._last_x is not None:
            self._set_cursor('a', self._last_x)

    def placeCursorB(self):
        if self._last_x is not None:
            self._set_cursor('b', self._last_x)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _remove_wave(self, tag):
        if tag in self.wave_data:
            wave, _ = self.wave_data[tag]
            #- Dispatch on actual placement, not digital_kind: a
            #- synthesized digital trace (analog source, show_as_digital
            #- on) lives in the digital pane but has digital_kind=None.
            if tag in self._digital_waves:
                self._remove_digital_wave(tag)
            else:
                wave.remove()
            del self.wave_data[tag]

    def _reset_axes(self):
        self._unit_vb.clear()
        self._unit_axis_side.clear()
        self._unit_axis_label.clear()
        if self._right_vb is not None:
            self.plot.scene().removeItem(self._right_vb)
            self._right_vb = None
            self.plot.hideAxis('right')
        self.plot.setLabel('left', '')
        self.plot.setLabel('right', '')
        self._logx = False
        self._has_rotated_x = False

    # --- Cursors ---

    def _make_cursor_line(self, x, color, which):
        line = pg.InfiniteLine(
            pos=x, angle=90, movable=True,
            pen=pg.mkPen(color, width=1, style=Qt.DashLine))
        line.sigPositionChanged.connect(
            lambda l, w=which: self._cursor_dragged(w, l))
        return line

    def _set_cursor(self, which, x):
        theme = _get_theme()
        color = theme['cursor_a'] if which == 'a' else theme['cursor_b']
        lines = self._cursor_a_lines if which == 'a' else self._cursor_b_lines

        if not lines:
            for vb in self._all_viewboxes():
                line = self._make_cursor_line(x, color, which)
                vb.addItem(line)
                lines.append(line)
        else:
            for line in lines:
                line.blockSignals(True)
                line.setValue(x)
                line.blockSignals(False)

        if which == 'a':
            self.cursor_a = x
        else:
            self.cursor_b = x
        self._update_readout()
        self._update_delta_texts()

    def _cursor_dragged(self, which, line):
        x = line.value()
        lines = self._cursor_a_lines if which == 'a' else self._cursor_b_lines
        for l in lines:
            if l is not line:
                l.blockSignals(True)
                l.setValue(x)
                l.blockSignals(False)
        if which == 'a':
            self.cursor_a = x
        else:
            self.cursor_b = x
        self._update_readout()
        self._update_delta_texts()

    # --- Scroll zoom (coalesced; matches tk implementation) ---

    def _on_wheel(self, event, axis=None):
        delta = event.delta()
        if delta == 0:
            return

        scale = 1.0 / ZOOM_FACTOR if delta > 0 else ZOOM_FACTOR
        modifiers = event.modifiers()

        # Anchor the zoom on the position of the FIRST event in a burst so
        # accumulated scaling happens around a stable point.
        if not self._wheel_timer.isActive():
            self._wheel_pending_pos = event.pos()
            self._wheel_pending_x_scale = 1.0
            self._wheel_pending_y_scale = 1.0

        if modifiers & Qt.ShiftModifier:
            self._wheel_pending_y_scale *= scale
        else:
            self._wheel_pending_x_scale *= scale

        self._wheel_timer.start()
        event.accept()

    def _apply_pending_wheel_zoom(self):
        pos = self._wheel_pending_pos
        if pos is None:
            return
        sx = self._wheel_pending_x_scale
        sy = self._wheel_pending_y_scale
        self._wheel_pending_x_scale = 1.0
        self._wheel_pending_y_scale = 1.0

        if sy != 1.0:
            for vb in self._all_viewboxes():
                vr = vb.viewRange()
                ylo, yhi = vr[1]
                pt = vb.mapSceneToView(pos)
                ydata = pt.y()
                new_lo = ydata - (ydata - ylo) * sy
                new_hi = ydata + (yhi - ydata) * sy
                vb.setYRange(new_lo, new_hi, padding=0)

        if sx != 1.0:
            mouse_point = self.plot.vb.mapSceneToView(pos)
            vr = self.plot.vb.viewRange()
            xlo, xhi = vr[0]
            xdata = mouse_point.x()
            new_lo = xdata - (xdata - xlo) * sx
            new_hi = xdata + (xhi - xdata) * sx
            self.plot.vb.setXRange(new_lo, new_hi, padding=0)

    def _on_mouse_drag(self, ev, axis=None):
        mods = ev.modifiers()
        if ev.button() == Qt.RightButton:
            #- Right-drag always draws a rubber band. Modifiers constrain
            #- the resulting zoom to a single axis:
            #-   plain                -> rectangle, zoom both x and y
            #-   Shift                -> band spans full plot height, zoom x only
            #-   Ctrl (or Cmd on Mac) -> band spans full plot width,  zoom y only
            #- On macOS Qt swaps the physical Ctrl and Meta keys by
            #- default, so accept either modifier to mean "y-only".
            ctrl_like = (Qt.ControlModifier | Qt.MetaModifier)
            if mods & Qt.ShiftModifier:
                self._right_drag_rubber_band(ev, constrain='x')
            elif mods & ctrl_like:
                self._right_drag_rubber_band(ev, constrain='y')
            else:
                self._right_drag_rubber_band(ev, constrain=None)
        else:
            self._orig_mouseDragEvent(ev, axis)

    def _right_drag_rubber_band(self, ev, constrain=None):
        """Right-drag draws a rubber-band rectangle and zooms to it on
        release. Reuses pyqtgraph's built-in scale-box machinery so the
        rectangle styling and zoom history match RectMode.

        ``constrain`` restricts the zoom (and the visible band) to one
        axis: ``'x'`` extends the band over the full plot height and
        only zooms x; ``'y'`` extends it over the full width and only
        zooms y; ``None`` is the original two-axis behaviour.
        """
        ev.accept()
        vb = self.plot.vb
        from PySide6.QtCore import QRectF, QPointF
        from pyqtgraph import Point

        down_pos = ev.buttonDownPos(Qt.RightButton)
        cur_pos = ev.pos()

        #- Build the on-screen (parent-coords) rectangle with the chosen
        #- constraint applied. We extend the band to the full vb extent
        #- on the locked axis so the user sees what's being kept.
        vb_rect = vb.rect()  # in vb's parent coords (item-local origin)
        if constrain == 'x':
            top = vb_rect.top()
            bot = vb_rect.bottom()
            screen_rect = QRectF(QPointF(down_pos.x(), top),
                                 QPointF(cur_pos.x(), bot))
        elif constrain == 'y':
            left = vb_rect.left()
            right = vb_rect.right()
            screen_rect = QRectF(QPointF(left, down_pos.y()),
                                 QPointF(right, cur_pos.y()))
        else:
            screen_rect = QRectF(Point(down_pos), Point(cur_pos))

        if ev.isFinish():
            try:
                vb.rbScaleBox.hide()
            except Exception:
                pass
            #- Ignore tiny rectangles (treat as a click, not a drag).
            min_extent = 3
            if constrain == 'x':
                if abs(screen_rect.width()) < min_extent:
                    return
            elif constrain == 'y':
                if abs(screen_rect.height()) < min_extent:
                    return
            else:
                if (abs(screen_rect.width()) < min_extent or
                        abs(screen_rect.height()) < min_extent):
                    return

            data_rect = vb.childGroup.mapRectFromParent(screen_rect)

            if constrain == 'x':
                #- Keep current y range, zoom only x.
                vb.setXRange(data_rect.left(), data_rect.right(), padding=0)
                #- Apply the same x-zoom to any linked viewbox so a
                #- right-axis curve stays in sync.
                for vbox in self._all_viewboxes():
                    if vbox is vb:
                        continue
                    vbox.setXRange(data_rect.left(), data_rect.right(),
                                   padding=0)
            elif constrain == 'y':
                #- Map y-range through every viewbox individually so each
                #- axis (left/right) zooms to its own data coordinates.
                for vbox in self._all_viewboxes():
                    dr = vbox.childGroup.mapRectFromParent(screen_rect)
                    vbox.setYRange(dr.top(), dr.bottom(), padding=0)
            else:
                vb.showAxRect(data_rect)
                #- Push onto the built-in axis history so the View menu's
                #- axis-history navigation still works as expected.
                try:
                    vb.axHistoryPointer += 1
                    vb.axHistory = (vb.axHistory[:vb.axHistoryPointer]
                                    + [data_rect])
                except Exception:
                    pass
        else:
            #- pyqtgraph's updateScaleBox takes two scene/parent points
            #- and draws a rectangle between them; pass the constrained
            #- corners so the user sees an axis-aligned band.
            vb.updateScaleBox(screen_rect.topLeft(),
                              screen_rect.bottomRight())

    # --- Delta text on plot ---

    def _clear_delta_texts(self):
        for item in self._delta_texts:
            item.getViewBox().removeItem(item)
        self._delta_texts.clear()

    def _update_delta_texts(self):
        self._clear_delta_texts()
        if self.cursor_a is None or self.cursor_b is None:
            return

        xunit = self._get_xunit()
        xa = self._view_to_data_x(self.cursor_a)
        xb = self._view_to_data_x(self.cursor_b)
        dx = xb - xa
        mid_x = (self.cursor_a + self.cursor_b) / 2.0

        parts = ["ΔX: %s" % _eng(dx, xunit)]
        if dx != 0 and xunit == 's':
            parts[0] += "  (1/ΔX: %s)" % _eng(1.0 / abs(dx), 'Hz')
        for tag, (wave, _) in self.wave_data.items():
            ya = self._interp_y(wave, self.cursor_a)
            yb = self._interp_y(wave, self.cursor_b)
            if ya is not None and yb is not None:
                parts.append("Δ%s: %s" % (wave.key, _eng(yb - ya, wave.yunit)))

        theme = _get_theme()
        text_item = pg.TextItem(
            text="\n".join(parts), color=theme['text_color'], anchor=(0.5, 0),
            fill=pg.mkBrush(*theme['overlay_fill']))
        text_item.setFont(_mono_font(8))
        self.plot.addItem(text_item)
        vr = self.plot.viewRange()
        text_item.setPos(mid_x, vr[1][1])
        self._delta_texts.append(text_item)

    # --- Mouse / readout ---

    def _on_mouse_moved(self, pos):
        vb = self.plot.vb
        if vb.sceneBoundingRect().contains(pos):
            pt = vb.mapSceneToView(pos)
            self._last_x = pt.x()
            xu = self._get_xunit()
            data_x = self._view_to_data_x(pt.x())
            self.status.setText("x: %s   y: %.6g" % (_eng(data_x, xu), pt.y()))
        else:
            self.status.setText("")

    def _interp_gradient(self, wave, view_x):
        if wave.x is None or wave.y is None or view_x is None:
            return None
        try:
            xd = np.real(wave.x)
            yd = np.real(wave.y)
            data_x = self._view_to_data_x(view_x)
            grad = np.gradient(yd, xd)
            return float(np.interp(data_x, xd, grad))
        except Exception:
            return None

    def _get_xunit(self):
        for wave, _ in self.wave_data.values():
            if wave.xunit:
                return wave.xunit
        return ""

    def _is_logx(self):
        for wave, _ in self.wave_data.values():
            if wave.logx:
                return True
        return False

    def _view_to_data_x(self, x):
        """Convert x from view coordinates to data coordinates (undo log10)."""
        if x is None:
            return None
        return 10.0 ** x if self._is_logx() else x

    def _interp_y(self, wave, x):
        if wave.x is None or x is None:
            return None
        try:
            data_x = self._view_to_data_x(x)
            return float(np.interp(data_x, np.real(wave.x), np.real(wave.y)))
        except Exception:
            return None

    def getStats(self):
        """Return per-wave statistics as a list of dicts."""
        stats = []
        for tag, (wave, _) in self.wave_data.items():
            if wave.y is None:
                continue
            y = np.real(wave.y)
            y = y[np.isfinite(y)]
            if len(y) == 0:
                continue
            stats.append({
                'key': wave.key, 'unit': wave.yunit,
                'file': wave.wfile.name,
                'min': float(np.min(y)), 'max': float(np.max(y)),
                'mean': float(np.mean(y)), 'std': float(np.std(y)),
                'pp': float(np.max(y) - np.min(y)),
            })
        return stats

    def _show_stats(self):
        stats = self.getStats()
        if not stats:
            self.readout.clear()
            return
        lines = []
        for s in stats:
            u = s['unit']
            lines.append(
                "  %-22s  min: %-12s  max: %-12s  μ: %-12s  σ: %-12s  pp: %-12s  %s"
                % (s['key'], _eng(s['min'], u), _eng(s['max'], u),
                   _eng(s['mean'], u), _eng(s['std'], u), _eng(s['pp'], u),
                   s.get('file', '')))
        self.readout.setPlainText("\n".join(lines))

    def addAnnotation(self, x, y, text):
        theme = _get_theme()
        item = pg.TextItem(text=text, color=theme['text_color'], anchor=(0, 1),
                           fill=pg.mkBrush(*theme['annotation_fill']),
                           border=theme['annotation_border'])
        item.setFont(_mono_font(9))
        item.setPos(x, y)
        self.plot.addItem(item)
        self._annotations.append({'text': text, 'x': x, 'y': y, 'item': item})

    def removeAnnotations(self):
        for ann in self._annotations:
            if ann.get('item'):
                self.plot.removeItem(ann['item'])
        self._annotations.clear()

    def _update_readout(self):
        if self.cursor_a is None and self.cursor_b is None:
            self._show_stats()
            return

        xunit = self._get_xunit()
        xa = self._view_to_data_x(self.cursor_a)
        xb = self._view_to_data_x(self.cursor_b)
        lines = []
        parts = []
        if xa is not None:
            parts.append("A: %s" % _eng(xa, xunit))
        if xb is not None:
            parts.append("B: %s" % _eng(xb, xunit))
        if xa is not None and xb is not None:
            dx = xb - xa
            parts.append("ΔX: %s" % _eng(dx, xunit))
            if dx != 0:
                if xunit == 's':
                    parts.append("(1/ΔX: %s)" % _eng(1.0 / abs(dx), 'Hz'))
                else:
                    parts.append("(1/ΔX: %s)" % _eng(1.0 / abs(dx)))
        lines.append("  ".join(parts))

        for tag, (wave, _) in self.wave_data.items():
            yu = wave.yunit
            du = "%s/%s" % (yu, wave.xunit) if yu and wave.xunit else ""
            wparts = ["  %-22s" % wave.key]
            ya = self._interp_y(wave, self.cursor_a)
            yb = self._interp_y(wave, self.cursor_b)
            ga = self._interp_gradient(wave, self.cursor_a)
            gb = self._interp_gradient(wave, self.cursor_b)
            if wave.digital_kind == 'vector':
                #- Show formatted vector samples (hex/dec/bin) instead
                #- of engineering-notation floats.
                if ya is not None:
                    wparts.append("A: %-14s" % wave.formatDigitalValue(ya))
                if yb is not None:
                    wparts.append("B: %-14s" % wave.formatDigitalValue(yb))
                if ya is not None and yb is not None:
                    try:
                        d = int(round(yb - ya))
                        wparts.append("Δ: %-14d" % d)
                    except (TypeError, ValueError):
                        pass
            elif wave.digital_kind == 'bit':
                if ya is not None:
                    wparts.append("A: %-14s" % wave.formatDigitalValue(ya))
                if yb is not None:
                    wparts.append("B: %-14s" % wave.formatDigitalValue(yb))
            else:
                if ya is not None:
                    wparts.append("A: %-14s" % _eng(ya, yu))
                if yb is not None:
                    wparts.append("B: %-14s" % _eng(yb, yu))
                if ya is not None and yb is not None:
                    wparts.append("Δ: %-14s" % _eng(yb - ya, yu))
                    if xa is not None and xb is not None and (xb - xa) != 0:
                        slope = (yb - ya) / (xb - xa)
                        wparts.append("Δ/ΔX: %-14s" % _eng(slope, du))
                if ga is not None:
                    wparts.append("dA: %-14s" % _eng(ga, du))
                if gb is not None:
                    wparts.append("dB: %-14s" % _eng(gb, du))
            lines.append("%s  %s" % ("".join(wparts), wave.wfile.name))

        self.readout.setPlainText("\n".join(lines))


class PgAnalysisPlot(QWidget):
    """Lightweight analysis tab with basic A/B cursors and readout."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)

        self.pw = pg.PlotWidget()
        self.pw.showGrid(x=True, y=True)
        _apply_grid(self.pw.plotItem)
        vb = self.pw.plotItem.vb
        vb.wheelEvent = self._on_wheel
        self._orig_drag = vb.mouseDragEvent
        vb.mouseDragEvent = self._on_mouse_drag
        layout.addWidget(self.pw, 1)

        font = _mono_font(9)
        self.readout = QTextEdit()
        self.readout.setReadOnly(True)
        self.readout.setMaximumHeight(80)
        self.readout.setFont(font)
        layout.addWidget(self.readout)

        self.status = QLabel("")
        self.status.setFont(font)
        layout.addWidget(self.status)

        self._apply_panel_style()

        self.cursor_a = None
        self.cursor_b = None
        self._cursor_a_line = None
        self._cursor_b_line = None
        self._last_x = None
        self._curves = []
        self._logx = False
        self._xunit = ""
        self._yunit = ""

        self.pw.scene().sigMouseMoved.connect(self._on_mouse_moved)

    def _apply_panel_style(self):
        theme = _get_theme()
        ss = "background-color: %s; color: %s;" % (
            theme['panel_bg'], theme['panel_fg'])
        self.readout.setStyleSheet(ss)
        self.status.setStyleSheet(ss + " padding: 2px;")

    def plot(self, x, y, **kwargs):
        curve = self.pw.plot(x, y, **kwargs)
        self._curves.append((x, y))
        return curve

    def addItem(self, item, **kwargs):
        self.pw.addItem(item, **kwargs)

    def setLabel(self, axis, text='', units=''):
        self.pw.setLabel(axis, text, units=units)
        if axis == 'bottom':
            self._xunit = units or text
        elif axis == 'left':
            self._yunit = units or text

    def setLogMode(self, x=False, y=False):
        self.pw.setLogMode(x=x, y=y)
        self._logx = x

    @property
    def sigRangeChanged(self):
        return self.pw.sigRangeChanged

    def viewRange(self):
        return self.pw.viewRange()

    def _view_to_data_x(self, x):
        return 10 ** x if self._logx else x

    def placeCursorA(self):
        if self._last_x is not None:
            self._set_cursor('a', self._last_x)

    def placeCursorB(self):
        if self._last_x is not None:
            self._set_cursor('b', self._last_x)

    def clearCursors(self):
        for line in [self._cursor_a_line, self._cursor_b_line]:
            if line:
                self.pw.removeItem(line)
        self._cursor_a_line = self._cursor_b_line = None
        self.cursor_a = self.cursor_b = None
        self.readout.clear()

    def autoSize(self):
        self.pw.enableAutoRange()

    def zoomIn(self):
        self._keyboard_zoom(1.0 / ZOOM_FACTOR)

    def zoomOut(self):
        self._keyboard_zoom(ZOOM_FACTOR)

    def _keyboard_zoom(self, scale):
        vb = self.pw.plotItem.vb
        vr = vb.viewRange()
        xlo, xhi = vr[0]
        xmid = (xlo + xhi) / 2.0
        vb.setXRange(xmid - (xmid - xlo) * scale,
                     xmid + (xhi - xmid) * scale, padding=0)
        ylo, yhi = vr[1]
        ymid = (ylo + yhi) / 2.0
        vb.setYRange(ymid - (ymid - ylo) * scale,
                     ymid + (yhi - ymid) * scale, padding=0)

    def setFontSize(self, size):
        font = _mono_font(size)
        self.readout.setFont(font)
        self.status.setFont(font)
        for axis_name in ['bottom', 'left']:
            ax = self.pw.plotItem.getAxis(axis_name)
            ax.setTickFont(font)
            ax.setStyle(tickFont=font)

    def _set_cursor(self, which, x):
        pen = pg.mkPen('y' if which == 'a' else 'g',
                        width=1, style=Qt.DashLine)
        attr_line = '_cursor_%s_line' % which
        old = getattr(self, attr_line)
        if old:
            self.pw.removeItem(old)
        line = pg.InfiniteLine(pos=x, angle=90, pen=pen, movable=True)
        self.pw.addItem(line)
        setattr(self, attr_line, line)
        setattr(self, 'cursor_%s' % which, x)
        line.sigPositionChanged.connect(
            lambda l, w=which: self._on_cursor_moved(w, l))
        self._update_readout()

    def _on_cursor_moved(self, which, line):
        setattr(self, 'cursor_%s' % which, line.value())
        self._update_readout()

    def _on_wheel(self, event, axis=None):
        delta = event.delta()
        if delta == 0:
            return
        scale = 1.0 / ZOOM_FACTOR if delta > 0 else ZOOM_FACTOR
        vb = self.pw.plotItem.vb
        pos = event.pos()
        mouse_point = vb.mapSceneToView(pos)
        modifiers = event.modifiers()
        if modifiers & Qt.ShiftModifier:
            vr = vb.viewRange()
            ylo, yhi = vr[1]
            yd = mouse_point.y()
            vb.setYRange(yd - (yd - ylo) * scale,
                         yd + (yhi - yd) * scale, padding=0)
        else:
            vr = vb.viewRange()
            xlo, xhi = vr[0]
            xd = mouse_point.x()
            vb.setXRange(xd - (xd - xlo) * scale,
                         xd + (xhi - xd) * scale, padding=0)
        event.accept()

    def _on_mouse_drag(self, ev, axis=None):
        mods = ev.modifiers()
        if ev.button() == Qt.RightButton and (
                mods & Qt.ShiftModifier or mods & Qt.ControlModifier):
            ev.accept()
            if ev.isFinish():
                return
            delta = ev.pos() - ev.lastPos()
            vb = self.pw.plotItem.vb
            vr = vb.viewRange()
            w = vb.width()
            h = vb.height()
            if mods & Qt.ShiftModifier:
                dx = delta.x() / w
                xlo, xhi = vr[0]
                xspan = xhi - xlo
                vb.setXRange(xlo + dx * xspan, xhi - dx * xspan, padding=0)
            elif mods & Qt.ControlModifier:
                dy = delta.y() / h
                ylo, yhi = vr[1]
                yspan = yhi - ylo
                vb.setYRange(ylo - dy * yspan, yhi + dy * yspan, padding=0)
        else:
            self._orig_drag(ev, axis)

    def _on_mouse_moved(self, pos):
        vb = self.pw.plotItem.vb
        if not vb.sceneBoundingRect().contains(pos):
            return
        mp = vb.mapSceneToView(pos)
        self._last_x = mp.x()
        data_x = self._view_to_data_x(mp.x())
        self.status.setText("x: %s" % _eng(data_x, self._xunit))

    def _update_readout(self):
        xa_raw = self.cursor_a
        xb_raw = self.cursor_b
        xa = self._view_to_data_x(xa_raw) if xa_raw is not None else None
        xb = self._view_to_data_x(xb_raw) if xb_raw is not None else None
        parts = []
        if xa is not None:
            parts.append("A: %s" % _eng(xa, self._xunit))
        if xb is not None:
            parts.append("B: %s" % _eng(xb, self._xunit))
        if xa is not None and xb is not None:
            dx = xb - xa
            parts.append("ΔX: %s" % _eng(dx, self._xunit))

        lines = ["  ".join(parts)]
        for xd, yd in self._curves:
            grad = np.gradient(yd, xd)
            wparts = []
            if xa is not None:
                ya = np.interp(self._view_to_data_x(xa_raw), xd, yd)
                ga = np.interp(self._view_to_data_x(xa_raw), xd, grad)
                wparts.append("A: %-14s  dA: %-14s" % (
                    _eng(ya, self._yunit), _eng(ga)))
            if xb is not None:
                yb = np.interp(self._view_to_data_x(xb_raw), xd, yd)
                gb = np.interp(self._view_to_data_x(xb_raw), xd, grad)
                wparts.append("B: %-14s  dB: %-14s" % (
                    _eng(yb, self._yunit), _eng(gb)))
            if xa is not None and xb is not None:
                wparts.append("Δ: %s" % _eng(yb - ya, self._yunit))
                if (xb - xa) != 0:
                    slope = (yb - ya) / (xb - xa)
                    wparts.append("Δ/ΔX: %s" % _eng(slope))
            lines.append("  ".join(wparts))
        self.readout.setPlainText("\n".join(lines))


class PgWaveWindow(QMainWindow):
    def __init__(self, xaxis):
        super().__init__()
        try:
            ver = _pkg_version("cicsim")
        except Exception:
            ver = "?"
        self.setWindowTitle("cIcWave v%s: %s" % (ver, os.getcwd()))
        self.resize(1200, 700)

        splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(splitter)

        self.browser = PgWaveBrowser(xaxis)
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self._close_tab)

        splitter.addWidget(self.browser)
        splitter.addWidget(self.tab_widget)
        splitter.setSizes([250, 950])

        self._line_width = 2
        self._font_size = 9
        self.plot_index = 0
        self._add_plot_tab()

        self.browser.waveSelected.connect(self._on_wave_selected)
        self.browser.waveRemoveRequested.connect(self._on_wave_remove)
        self.browser.analysisRequested.connect(self._on_analysis)
        self.browser.styleChanged.connect(self._on_style_changed)
        self.browser.fileRemoveRequested.connect(self._on_file_remove)
        self.browser.wavePlotAllRequested.connect(self._plot_wave_all_files)
        self.browser.wavePlotAllVisibleRequested.connect(
            self._plot_all_visible_waves)

        self._drops_delegate_trees = (
            self.browser.file_tree,
            self.browser.wave_tree,
            self.browser.file_tree.viewport(),
            self.browser.wave_tree.viewport(),
        )

        self._setup_menus()
        self._setup_shortcuts()
        self._install_drop_filters()

    def _install_drop_filters(self):
        """Accept file drops on any child (plots, browser, etc.)."""
        self._attach_drop_filter_subtree(self.centralWidget())

    def _attach_drop_filter_subtree(self, root):
        if root is None:
            return
        root.installEventFilter(self)
        for w in root.findChildren(QWidget):
            w.installEventFilter(self)

    def eventFilter(self, obj, event):
        et = event.type()
        if et in (QEvent.DragEnter, QEvent.DragMove, QEvent.Drop):
            if obj in self._drops_delegate_trees:
                return False
        if et == QEvent.DragEnter or et == QEvent.DragMove:
            if self._drop_mime_has_files(event.mimeData()):
                event.acceptProposedAction()
                return True
        elif et == QEvent.Drop:
            self._handle_file_drop(event)
            return True
        return super().eventFilter(obj, event)

    @staticmethod
    def _drop_mime_has_files(mime_data):
        if not mime_data.hasUrls():
            return False
        for url in mime_data.urls():
            p = url.toLocalFile()
            if p and os.path.isfile(p):
                return True
        return False

    def _handle_file_drop(self, event):
        paths = []
        for url in event.mimeData().urls():
            p = url.toLocalFile()
            if p and os.path.isfile(p):
                paths.append(os.path.normpath(p))
        if not paths:
            event.ignore()
            return
        event.acceptProposedAction()
        for path in paths:
            if path.lower().endswith('.cicwave.yaml'):
                self.applySession(path)
            else:
                self.browser.openFile(path)

    def _setup_menus(self):
        mb = self.menuBar()

        m = mb.addMenu("File")
        m.addAction("Open File         Ctrl+O", self._open_file)
        m.addAction("Remove All Files", self._remove_all_files)
        m.addAction("Save Session      Ctrl+S", self._save_session)
        m.addAction("Load Session", self._load_session)
        m.addSeparator()
        m.addAction("Export PDF        Ctrl+P", self._export_pdf)
        m.addAction("Export Data...    Ctrl+E", self._export_data)
        m.addSeparator()
        m.addAction("Quit              Ctrl+Q", self.close)

        m = mb.addMenu("Edit")
        m.addAction("New Plot          Ctrl+N", self._add_plot_tab)
        m.addAction("Close Tab         Ctrl+W", self._close_current_tab)
        m.addSeparator()
        m.addAction("Set Axis Labels   Ctrl+L", self._set_axis_labels)
        m.addAction("Default X Axis...", self._edit_default_xaxis)
        m.addAction("Add Annotation    Ctrl+T", self._add_annotation)
        m.addAction("Clear Annotations", self._clear_annotations)
        m.addSeparator()
        m.addAction("Reload All        R", self._reload)
        m.addAction("Auto Scale        F", self._auto_size)
        m.addAction("Zoom In           Shift+Z", self._zoom_in)
        m.addAction("Zoom Out          Ctrl+Z", self._zoom_out)
        m.addSeparator()
        m.addAction("Remove All", self._remove_all)

        m = mb.addMenu("View")
        m.addAction("Set Cursor A      A", self._cursor_a)
        m.addAction("Set Cursor B      B", self._cursor_b)
        m.addAction("Clear Cursors     Escape", self._clear_cursors)
        m.addSeparator()
        m.addAction("Toggle Legend      L", self._toggle_legend)
        m.addSeparator()
        m.addAction("Increase Line Width   Ctrl+Up", self._inc_line_width)
        m.addAction("Decrease Line Width   Ctrl+Down", self._dec_line_width)
        m.addSeparator()
        m.addAction("Increase Font Size    Ctrl+=", self._inc_font_size)
        m.addAction("Decrease Font Size    Ctrl+-", self._dec_font_size)
        m.addSeparator()
        m.addAction("Dark Theme", lambda: self._set_theme('dark'))
        m.addAction("Light Theme", lambda: self._set_theme('light'))

        m = mb.addMenu("Help")
        m.addAction("Keyboard Shortcuts", self._show_help)

    def _setup_shortcuts(self):
        for seq, func in [
            ("Ctrl+O", self._open_file),
            ("Ctrl+S", self._save_session),
            ("Ctrl+P", self._export_pdf),
            ("Ctrl+E", self._export_data),
            ("Ctrl+Q", self.close),
            ("Ctrl+N", self._add_plot_tab),
            ("Ctrl+W", self._close_current_tab),
            ("Ctrl+L", self._set_axis_labels),
            ("Ctrl+T", self._add_annotation),
            ("Ctrl+Up", self._inc_line_width),
            ("Ctrl+Down", self._dec_line_width),
            ("Ctrl+=", self._inc_font_size),
            ("Ctrl+-", self._dec_font_size),
            ("Escape", self._clear_cursors),
        ]:
            QShortcut(QKeySequence(seq), self, func)
        #- Single-letter shortcuts that should fire even while the
        #- wave/file tree has focus. ``ApplicationShortcut`` context
        #- bypasses the QTreeWidget's keyboard-search swallowing.
        from PySide6.QtCore import Qt as _Qt
        d_sc = QShortcut(QKeySequence("D"), self,
                         self.browser.togglePlotAsDigital)
        d_sc.setContext(_Qt.ApplicationShortcut)

    def keyPressEvent(self, event):
        if isinstance(self.focusWidget(), QLineEdit):
            super().keyPressEvent(event)
            return
        p = self._current()
        key = event.text()
        mods = event.modifiers()
        ctrl_like = (Qt.ControlModifier | Qt.MetaModifier)
        if p and key == 'z' and not (mods & ctrl_like) and hasattr(p, 'zoomIn'):
            p.zoomIn()
        elif p and key == 'Z' and hasattr(p, 'zoomOut'):
            #- Shift+z (uppercase Z) zooms out. Ctrl+z still works as a
            #- secondary binding for muscle-memory parity with Shift+Z.
            p.zoomOut()
        elif p and key.lower() == 'z' and mods & ctrl_like and hasattr(p, 'zoomOut'):
            p.zoomOut()
        elif p and key.lower() == 'a' and hasattr(p, 'placeCursorA'):
            p.placeCursorA()
        elif p and key.lower() == 'b' and hasattr(p, 'placeCursorB'):
            p.placeCursorB()
        elif p and key.lower() == 'f' and hasattr(p, 'autoSize'):
            p.autoSize()
        elif p and key.lower() == 'r' and hasattr(p, 'reloadAll'):
            p.reloadAll()
        elif p and key.lower() == 'l' and hasattr(p, 'toggleLegend'):
            p.toggleLegend()
        else:
            super().keyPressEvent(event)

    def _current(self):
        return self.tab_widget.currentWidget()

    def _add_plot_tab(self):
        plot = PgWavePlot()
        plot.setLineWidth(self._line_width)
        plot.setFontSize(self._font_size)
        self.tab_widget.addTab(plot, "Plot %d" % self.plot_index)
        self.plot_index += 1
        self.tab_widget.setCurrentWidget(plot)
        self._attach_drop_filter_subtree(plot)

    def _on_wave_selected(self, wave):
        p = self._current()
        if p:
            result = p.show_wave(wave, style=self.browser.plotStyle)
            if result:
                tag, color = result
                self.browser.setWaveColor(tag, color)
            else:
                #- Already plotted: still poke the readout so a digital
                #- format change (or other wave-side option) shows up
                #- without requiring a cursor move.
                if hasattr(p, '_refresh_digital_labels'):
                    p._refresh_digital_labels(wave)
                if hasattr(p, '_update_readout'):
                    p._update_readout()

    def _on_wave_remove(self, wave):
        p = self._current()
        if p:
            tag = p.removeLine(wave)
            if tag:
                self.browser.clearWaveColor(tag)

    def _on_file_remove(self, key):
        if key not in self.browser.files:
            return
        wf = self.browser.files[key]
        for ti in range(self.tab_widget.count()):
            w = self.tab_widget.widget(ti)
            if isinstance(w, PgWavePlot):
                tags = w.remove_waves_for_wfile(wf)
                for tag in tags:
                    self.browser.clearWaveColor(tag)
        self.browser._purge_wave_cache_for_wfile(wf)
        self.browser.remove_file_entry(key)

    def _remove_all_files(self):
        if not self.browser.files:
            return
        for ti in range(self.tab_widget.count()):
            w = self.tab_widget.widget(ti)
            if isinstance(w, PgWavePlot):
                tags = w.removeAll()
                for tag in tags:
                    self.browser.clearWaveColor(tag)
        self.browser._wave_cache.clear()
        self.browser.file_tree.clear()
        self.browser.wave_tree.clear()
        self.browser._tag_to_item = {}
        self.browser.files.clear_all()

    def _plot_wave_all_files(self, yname):
        p = self._current()
        if not isinstance(p, PgWavePlot):
            return
        style = self.browser.plotStyle
        for wf in self.browser.files.values():
            if yname not in wf.getWaveNames():
                continue
            tag = wf.getTag(yname)
            if tag not in self.browser._wave_cache:
                self.browser._wave_cache[tag] = PgWave(wf, yname, self.browser.xaxis)
            wave = self.browser._wave_cache[tag]
            wave.reload()
            result = p.show_wave(wave, style=style)
            if result:
                tag2, color = result
                self.browser.setWaveColor(tag2, color)

    def _plot_all_visible_waves(self):
        p = self._current()
        if not isinstance(p, PgWavePlot):
            return
        f = self.browser.files.getSelected()
        if f is None:
            return
        style = self.browser.plotStyle
        for yname in sorted(self.browser._visible_wave_names()):
            tag = f.getTag(yname)
            if tag not in self.browser._wave_cache:
                self.browser._wave_cache[tag] = PgWave(f, yname, self.browser.xaxis)
            wave = self.browser._wave_cache[tag]
            wave.reload()
            result = p.show_wave(wave, style=style)
            if result:
                tag2, color = result
                self.browser.setWaveColor(tag2, color)

    def _on_style_changed(self, style):
        p = self._current()
        if p and hasattr(p, 'setAllStyles'):
            p.setAllStyles(style)

    def _open_file(self):
        fname, _ = QFileDialog.getOpenFileName(
            self, "Open File", os.getcwd(),
            "All Supported (*.raw *.vcd *.csv *.tsv *.txt *.xlsx *.xls *.ods *.pkl *.pickle *.json *.parquet *.feather *.h5 *.hdf5);;Raw Files (*.raw);;VCD Files (*.vcd);;CSV/TSV (*.csv *.tsv *.txt);;Excel (*.xlsx *.xls *.ods);;Pickle (*.pkl *.pickle);;JSON (*.json);;Parquet (*.parquet);;Feather (*.feather);;HDF5 (*.h5 *.hdf5);;All Files (*)")
        if fname:
            self.browser.openFile(fname)

    def _export_pdf(self):
        p = self._current()
        if p and hasattr(p, 'exportPdf'):
            p.exportPdf()

    def _export_data(self):
        p = self._current()
        if p and hasattr(p, 'exportData'):
            p.exportData()

    def _reload(self):
        p = self._current()
        if p and hasattr(p, 'reloadAll'):
            p.reloadAll()

    def _auto_size(self):
        p = self._current()
        if p and hasattr(p, 'autoSize'):
            p.autoSize()

    def _zoom_in(self):
        p = self._current()
        if p and hasattr(p, 'zoomIn'):
            p.zoomIn()

    def _zoom_out(self):
        p = self._current()
        if p and hasattr(p, 'zoomOut'):
            p.zoomOut()

    def _inc_line_width(self):
        self._line_width = min(self._line_width + 1, 10)
        self._apply_line_width()

    def _dec_line_width(self):
        self._line_width = max(self._line_width - 1, 1)
        self._apply_line_width()

    def _apply_line_width(self):
        for ti in range(self.tab_widget.count()):
            w = self.tab_widget.widget(ti)
            if hasattr(w, 'setLineWidth'):
                w.setLineWidth(self._line_width)

    def _inc_font_size(self):
        self._font_size = min(self._font_size + 1, 24)
        self._apply_font_size()

    def _dec_font_size(self):
        self._font_size = max(self._font_size - 1, 6)
        self._apply_font_size()

    def _apply_font_size(self):
        for ti in range(self.tab_widget.count()):
            w = self.tab_widget.widget(ti)
            if hasattr(w, 'setFontSize'):
                w.setFontSize(self._font_size)

    def _remove_all(self):
        p = self._current()
        if p:
            tags = p.removeAll()
            for tag in tags:
                self.browser.clearWaveColor(tag)

    def _cursor_a(self):
        p = self._current()
        if p and hasattr(p, 'placeCursorA'):
            p.placeCursorA()

    def _cursor_b(self):
        p = self._current()
        if p and hasattr(p, 'placeCursorB'):
            p.placeCursorB()

    def _clear_cursors(self):
        p = self._current()
        if p and hasattr(p, 'clearCursors'):
            p.clearCursors()

    def _toggle_legend(self):
        p = self._current()
        if p and hasattr(p, 'toggleLegend'):
            p.toggleLegend()

    def _set_theme(self, theme_name):
        app = QApplication.instance()
        _apply_theme(app, theme_name)
        theme = _get_theme()
        for ti in range(self.tab_widget.count()):
            w = self.tab_widget.widget(ti)
            if hasattr(w, '_apply_panel_style'):
                w._apply_panel_style()
            if hasattr(w, 'gw'):
                w.gw.setBackground(theme['pg_background'])
                _apply_grid(w.plot)
            if hasattr(w, 'pw'):
                w.pw.setBackground(theme['pg_background'])
                _apply_grid(w.pw.plotItem)

    def _show_help(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Keyboard Shortcuts")
        layout = QVBoxLayout(dlg)
        text = QLabel(
            "Keyboard Shortcuts\n"
            "══════════════════════════════\n"
            "\n"
            "File\n"
            "  Ctrl+O        Open file\n"
            "  Ctrl+S        Save session\n"
            "  Ctrl+P        Export PDF/PNG/SVG\n"
            "  Ctrl+E        Export plotted data (CSV/Parquet/...)\n"
            "  Ctrl+Q        Quit\n"
            "\n"
            "Edit\n"
            "  Ctrl+N        New plot tab\n"
            "  Ctrl+W        Close current tab\n"
            "  Ctrl+L        Set axis labels\n"
            "  Ctrl+T        Add annotation\n"
            "  R             Reload all waves\n"
            "  F             Fit all (auto scale)\n"
            "  Z             Zoom in\n"
            "  Shift+Z       Zoom out\n"
            "  Ctrl+Z        Zoom out (alias)\n"
            "\n"
            "Cursors\n"
            "  A             Set cursor A at mouse\n"
            "  B             Set cursor B at mouse\n"
            "  Escape        Clear cursors\n"
            "  Drag cursor   Move cursor\n"
            "\n"
            "View\n"
            "  L             Toggle legend\n"
            "  D             Toggle focused wave on the digital pane\n"
            "  Ctrl+Up       Increase line width\n"
            "  Ctrl+Down     Decrease line width\n"
            "  Ctrl+=        Increase font size\n"
            "  Ctrl+-        Decrease font size\n"
            "\n"
            "Mouse\n"
            "  Left-drag          Pan\n"
            "  Scroll             Zoom x-axis\n"
            "  Shift+Scroll       Zoom y-axis\n"
            "  Shift+Right-drag   Zoom x-axis\n"
            "  Ctrl+Right-drag    Zoom y-axis\n"
            "\n"
            "Browser\n"
            "  Double-click       Add to plot\n"
            "  Right-click        Context menu\n"
            "\n"
            "Analysis (right-click menu)\n"
            "  FFT / PSD          Spectral density\n"
            "  Histogram          Distribution + fit\n"
            "  Differentiate      Numerical dy/dx\n"
            "  X vs Y             Parametric plot\n"
        )
        text.setFont(_mono_font(11))
        theme = _get_theme()
        text.setStyleSheet(
            "background-color: %s; color: %s; padding: 16px;" % (
                theme['panel_bg'], theme['panel_fg']))
        layout.addWidget(text)
        btn = QPushButton("Close")
        btn.clicked.connect(dlg.accept)
        layout.addWidget(btn)
        dlg.exec()

    # ------------------------------------------------------------------
    # Default X axis (new loads + persistence)
    # ------------------------------------------------------------------

    def _edit_default_xaxis(self):
        text, ok = QInputDialog.getText(
            self, "Default X Axis",
            "Column name used as X when the file has no standard axis "
            "(time, frequency, sweeps, …).\n"
            "Leave empty for automatic detection.\n"
            "Applies to newly opened files; saved for later sessions.",
            QLineEdit.Normal,
            self.browser.xaxis or "")
        if not ok:
            return
        col = text.strip() or None
        self.browser.xaxis = col
        _write_saved_default_xaxis(col)

    # ------------------------------------------------------------------
    # Axis labels dialog
    # ------------------------------------------------------------------

    def _set_axis_labels(self):
        p = self._current()
        if not isinstance(p, PgWavePlot):
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Set Axis Labels")
        form = QVBoxLayout(dlg)

        def _row(label_text, default):
            row = QHBoxLayout()
            row.addWidget(QLabel(label_text))
            le = QLineEdit(default or "")
            row.addWidget(le)
            form.addLayout(row)
            return le

        title_le = _row("Title:", p.custom_title)
        xlabel_le = _row("X-axis:", p.custom_xlabel)
        ylabel_le = _row("Y-axis:", p.custom_ylabel)

        btn = QPushButton("Apply")
        btn.clicked.connect(dlg.accept)
        form.addWidget(btn)

        if dlg.exec() != QDialog.Accepted:
            return
        p.custom_title = title_le.text().strip() or None
        p.custom_xlabel = xlabel_le.text().strip() or None
        p.custom_ylabel = ylabel_le.text().strip() or None
        if p.custom_title:
            p.plot.setTitle(p.custom_title,
                            color=_get_theme()['title_color'], size='11pt')
        else:
            p.plot.setTitle(None)
        if p.custom_xlabel:
            p.plot.setLabel('bottom', p.custom_xlabel)
        if p.custom_ylabel:
            p.plot.setLabel('left', p.custom_ylabel)

    # ------------------------------------------------------------------
    # Annotations
    # ------------------------------------------------------------------

    def _add_annotation(self):
        p = self._current()
        if not isinstance(p, PgWavePlot):
            return
        if p._last_x is None:
            return
        text, ok = QInputDialog.getText(self, "Add Annotation",
                                        "Text:")
        if not ok or not text.strip():
            return
        vr = p.plot.viewRange()
        y = (vr[1][0] + vr[1][1]) / 2.0
        p.addAnnotation(p._last_x, y, text.strip())

    def _clear_annotations(self):
        p = self._current()
        if isinstance(p, PgWavePlot):
            p.removeAnnotations()

    # ------------------------------------------------------------------
    # Session save / load
    # ------------------------------------------------------------------

    def _build_session(self):
        """Collect current GUI state into a serialisable dict."""
        files = []
        wf_to_idx = {}
        for fkey, wf in self.browser.files.items():
            idx = len(files)
            orig = getattr(wf, '_original_path', None) or wf.fname
            entry = {'path': os.path.abspath(orig)}
            pivot_path = getattr(wf, '_pivot_spec_path', None)
            if pivot_path:
                entry['pivot'] = pivot_path
            files.append(entry)
            wf_to_idx[id(wf)] = idx

        plots = []
        for ti in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(ti)
            if not isinstance(widget, PgWavePlot):
                continue
            tab_name = self.tab_widget.tabText(ti)
            waves = []
            for tag, (wave, yunit) in widget.wave_data.items():
                fi = wf_to_idx.get(id(wave.wfile))
                waves.append({
                    'file': fi,
                    'name': wave.key,
                    'style': getattr(wave, 'style', 'Lines'),
                })
            plot_dict = {'name': tab_name, 'waves': waves}
            if widget.custom_xlabel:
                plot_dict['xlabel'] = widget.custom_xlabel
            if widget.custom_ylabel:
                plot_dict['ylabel'] = widget.custom_ylabel
            if widget.custom_title:
                plot_dict['title'] = widget.custom_title
            if widget._annotations:
                plot_dict['annotations'] = [
                    {'text': a['text'], 'x': float(a['x']),
                     'y': float(a['y'])}
                    for a in widget._annotations
                ]
            plots.append(plot_dict)

        return {'files': files, 'plots': plots}

    def _save_session(self):
        import yaml
        fname, _ = QFileDialog.getSaveFileName(
            self, "Save Session", os.getcwd(),
            "Session files (*.cicwave.yaml);;YAML files (*.yaml);;All Files (*)")
        if not fname:
            return
        session = self._build_session()
        session_dir = os.path.dirname(os.path.abspath(fname))
        for fe in session.get('files', []):
            fe['path'] = os.path.relpath(fe['path'], session_dir)
            if 'pivot' in fe:
                fe['pivot'] = os.path.relpath(fe['pivot'], session_dir)

        with open(fname, 'w') as fh:
            yaml.dump(session, fh, default_flow_style=False, sort_keys=False)

    def _load_session(self):
        fname, _ = QFileDialog.getOpenFileName(
            self, "Load Session", os.getcwd(),
            "Session files (*.cicwave.yaml *.yaml);;All Files (*)")
        if not fname:
            return
        self.applySession(fname)

    def applySession(self, session_path):
        """Load a session file and restore the GUI state."""
        import yaml
        with open(session_path) as fh:
            session = yaml.safe_load(fh)

        session_dir = os.path.dirname(os.path.abspath(session_path))

        for fe in session.get('files', []):
            fpath = fe['path']
            if not os.path.isabs(fpath):
                fpath = os.path.normpath(os.path.join(session_dir, fpath))
            pivot_path = fe.get('pivot')
            if pivot_path and not os.path.isabs(pivot_path):
                pivot_path = os.path.normpath(
                    os.path.join(session_dir, pivot_path))

            if pivot_path:
                from cicsim.pivot import load_spec, apply_pivot
                from cicsim.wavefiles import WaveFile
                spec = load_spec(pivot_path)
                xaxis = self.browser.xaxis or spec.get('columns', '')
                if not self.browser.xaxis and spec.get('columns'):
                    self.browser.xaxis = spec['columns']
                wf = WaveFile(fpath, xaxis)
                pivoted = apply_pivot(wf.df, spec)
                name = "pivot(%s)" % os.path.basename(fpath)
                self.browser.openDataFrame(pivoted, name)
            else:
                self.browser.openFile(fpath)

        for pd in session.get('plots', []):
            tab_idx = self.tab_widget.count() - 1
            p = self.tab_widget.widget(tab_idx)
            if p is None or (isinstance(p, PgWavePlot) and p.wave_data):
                self._add_plot_tab()
                tab_idx = self.tab_widget.count() - 1
                p = self.tab_widget.widget(tab_idx)

            if pd.get('name'):
                self.tab_widget.setTabText(tab_idx, pd['name'])

            for wd in pd.get('waves', []):
                wave_name = wd.get('name')
                style = wd.get('style', 'Lines')
                wave = self._find_wave(wave_name)
                if wave:
                    result = p.show_wave(wave, style=style)
                    if result:
                        tag, color = result
                        self.browser.setWaveColor(tag, color)

            if pd.get('xlabel'):
                p.custom_xlabel = pd['xlabel']
                p.plot.setLabel('bottom', pd['xlabel'])
            if pd.get('ylabel'):
                p.custom_ylabel = pd['ylabel']
                p.plot.setLabel('left', pd['ylabel'])
            if pd.get('title'):
                p.custom_title = pd['title']
                p.plot.setTitle(pd['title'],
                                color=_get_theme()['title_color'],
                                size='11pt')

            for ann in pd.get('annotations', []):
                p.addAnnotation(ann['x'], ann['y'], ann['text'])

    def _find_wave(self, name):
        """Look up a PgWave by column name across all loaded files."""
        for fkey, wf in self.browser.files.items():
            for wn in wf.getWaveNames():
                if wn == name:
                    tag = wf.getTag(wn)
                    if tag in self.browser._wave_cache:
                        return self.browser._wave_cache[tag]
                    wave = PgWave(wf, wn, self.browser.xaxis)
                    self.browser._wave_cache[tag] = wave
                    return wave
        return None

    def _close_tab(self, index):
        widget = self.tab_widget.widget(index)
        if widget:
            if isinstance(widget, PgWavePlot):
                tags = widget.removeAll()
                for tag in tags:
                    self.browser.clearWaveColor(tag)
            self.tab_widget.removeTab(index)
            widget.deleteLater()
        if self.tab_widget.count() == 0:
            self._add_plot_tab()

    def _close_current_tab(self):
        idx = self.tab_widget.currentIndex()
        if idx >= 0:
            self._close_tab(idx)

    def _on_analysis(self, atype, wave):
        wave.reload()
        x, _ = _to_numeric(wave.x)
        y, _ = _to_numeric(wave.y)

        if atype == "fft":
            self._do_fft(wave.key, x, y, wave.xunit, wave.yunit)
        elif atype == "histogram":
            self._do_histogram(wave.key, y, wave.yunit)
        elif atype == "differentiate":
            self._do_differentiate(wave.key, x, y, wave.xunit, wave.yunit)
        elif atype == "xvy":
            self._do_xvy_dialog(wave)

    def _add_analysis_tab(self, title):
        w = PgAnalysisPlot()
        w.setFontSize(self._font_size)
        self.tab_widget.addTab(w, title)
        self.tab_widget.setCurrentWidget(w)
        return w

    def _do_fft(self, name, x, y, xunit, yunit):
        n = len(y)
        if n < 2:
            return

        dt = np.mean(np.diff(x))
        if dt <= 0:
            return

        window = np.hanning(n)
        yw = y * window
        Y = np.fft.rfft(yw)
        freqs = np.fft.rfftfreq(n, d=dt)

        psd = np.abs(Y) ** 2
        psd[psd < 1e-300] = 1e-300
        psd_db = 10.0 * np.log10(psd / np.max(psd))

        freqs = freqs[1:]
        psd_db = psd_db[1:]

        w = self._add_analysis_tab("FFT: %s" % name)
        w.plot(freqs, psd_db, pen=pg.mkPen('c', width=2))
        w.setLabel('bottom', 'Frequency', units='Hz')
        w.setLabel('left', 'PSD', units='dB')
        if len(freqs) > 1 and freqs[0] > 0:
            w.setLogMode(x=True, y=False)

    def _do_histogram(self, name, y, yunit):
        n = len(y)
        if n < 2:
            return

        nbins = max(10, n // 100)
        counts, edges = np.histogram(y, bins=nbins)
        centers = (edges[:-1] + edges[1:]) / 2.0

        mu = np.mean(y)
        sigma = np.std(y)

        w = self._add_analysis_tab("Hist: %s" % name)
        bar = pg.BarGraphItem(x=centers, height=counts,
                              width=(edges[1] - edges[0]) * 0.85,
                              brush='c', pen='w')
        w.addItem(bar)

        if sigma > 0:
            xfit = np.linspace(edges[0], edges[-1], 200)
            scale = np.max(counts)
            gauss = scale * np.exp(-0.5 * ((xfit - mu) / sigma) ** 2)
            w.plot(xfit, gauss, pen=pg.mkPen('r', width=2))

        w.setLabel('bottom', yunit if yunit else name)
        w.setLabel('left', 'Count')
        txt = pg.TextItem("μ = %s\nσ = %s" % (_eng(mu, yunit), _eng(sigma, yunit)),
                          color=_get_theme()['text_color'], anchor=(0, 1))
        w.addItem(txt, ignoreBounds=True)

        _busy = [False]

        def _reposition():
            if _busy[0]:
                return
            _busy[0] = True
            vr = w.viewRange()
            txt.setPos(vr[0][0] + 0.02 * (vr[0][1] - vr[0][0]),
                       vr[1][1] - 0.02 * (vr[1][1] - vr[1][0]))
            _busy[0] = False
        w.sigRangeChanged.connect(_reposition)
        _reposition()

    def _do_differentiate(self, name, x, y, xunit, yunit):
        if len(x) < 2:
            return
        dydx = np.gradient(y, x)
        dy_unit = ""
        if yunit and xunit:
            dy_unit = "%s/%s" % (yunit, xunit)

        w = self._add_analysis_tab("d/dx: %s" % name)
        w.plot(x, dydx, pen=pg.mkPen('m', width=2))
        w.setLabel('bottom', xunit if xunit else 'x')
        w.setLabel('left', dy_unit if dy_unit else "d(%s)/dx" % name)

    def _do_xvy_dialog(self, wave_y):
        f = self.browser.files.getSelected()
        if not f:
            return
        names = list(f.getWaveNames())
        dlg = _SignalPickerDialog(self, "Select X-axis signal", names,
                                  file_label=f.name)
        if dlg.exec() != QDialog.Accepted:
            return
        chosen = dlg.selected()
        if not chosen:
            return
        xwave = PgWave(f, chosen, self.browser.xaxis)
        xwave.reload()
        xx, xlabels = _to_numeric(xwave.y)
        yy, ylabels = _to_numeric(wave_y.y)
        min_len = min(len(xx), len(yy))
        xx, yy = xx[:min_len], yy[:min_len]

        w = self._add_analysis_tab("%s vs %s" % (wave_y.key, chosen))
        w.plot(xx, yy, pen=pg.mkPen('y', width=2))
        w.setLabel('bottom', chosen)
        w.setLabel('left', wave_y.key)
        if xlabels:
            ticks = list(zip(xx[:min_len], xlabels[:min_len]))
            _apply_rotated_ticks(w.pw.plotItem, 'bottom', ticks)
        if ylabels:
            ticks = list(zip(yy[:min_len], ylabels[:min_len]))
            w.pw.getAxis('left').setTicks([ticks])

    def openFile(self, fname, sheet_name=None):
        self.browser.openFile(fname, sheet_name=sheet_name)

    def openDataFrame(self, df, name, **kwargs):
        self.browser.openDataFrame(df, name, **kwargs)


def _apply_theme(app, theme_name='dark'):
    _set_active_theme(theme_name)
    theme = _get_theme()
    app.setStyle("Fusion")
    p = QPalette()
    for role_name, rgb in theme['palette'].items():
        p.setColor(getattr(QPalette, role_name), QColor(*rgb))
    p.setColor(QPalette.Disabled, QPalette.Text, QColor(128, 128, 128))
    p.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(128, 128, 128))
    app.setPalette(p)
    pg.setConfigOptions(background=theme['pg_background'],
                        foreground=theme['pg_foreground'])


def _detect_opengl():
    """Return True if pyqtgraph's OpenGL backend should be enabled.

    PyOpenGL must be importable (pyqtgraph needs it for the GL-accelerated
    renderer); without it we stay on the raster backend.

    OpenGL is enabled by default on every platform when PyOpenGL is
    available. On macOS we additionally log a one-time warning because
    some pyqtgraph + Qt + Cocoa combinations render an empty plot
    canvas; the user can disable GL with ``CICSIM_USE_OPENGL=0`` if
    they hit that. ``CICSIM_USE_OPENGL=1`` force-enables on any
    platform (still requires PyOpenGL).
    """
    env = os.environ.get("CICSIM_USE_OPENGL")
    if env == "0":
        return False
    try:
        import OpenGL  # noqa: F401
    except Exception:
        return False
    if env == "1":
        return True
    if sys.platform == "darwin" and not _detect_opengl._mac_warned:
        import logging
        logging.getLogger("cicsim").warning(
            "Enabling pyqtgraph OpenGL backend on macOS. Some Qt/Cocoa "
            "builds render an empty plot canvas with OpenGL; if you see "
            "blank plots, run again with CICSIM_USE_OPENGL=0 to fall "
            "back to the raster renderer."
        )
        _detect_opengl._mac_warned = True
    return True


_detect_opengl._mac_warned = False


class CmdWavePg:
    def __init__(self, xaxis, theme='dark'):
        self.app = QApplication.instance() or QApplication(sys.argv)
        # Enable OpenGL when available: gives a large speedup when many
        # curves are on screen (e.g. one curve per file across hundreds of
        # files). Falls back silently to raster when PyOpenGL is missing
        # or on platforms where it renders blank plots (macOS).
        use_gl = _detect_opengl()
        pg.setConfigOptions(antialias=False, useOpenGL=use_gl)
        _apply_theme(self.app, theme)
        effective = xaxis
        if not effective:
            effective = _read_saved_default_xaxis()
        self.xaxis = effective if effective else None
        self.win = PgWaveWindow(self.xaxis)

    def openFile(self, fname, sheet_name=None):
        self.win.openFile(fname, sheet_name=sheet_name)

    def openDataFrame(self, df, name, **kwargs):
        self.win.openDataFrame(df, name, **kwargs)

    def run(self):
        self.win.show()
        self.app.exec()

    def exportAndExit(self, fname):
        """Export the current plot to a file without showing the GUI."""
        for ti in range(self.win.tab_widget.count()):
            widget = self.win.tab_widget.widget(ti)
            if isinstance(widget, PgWavePlot) and widget.wave_data:
                if self.win.tab_widget.count() > 1:
                    base, ext = os.path.splitext(fname)
                    out = "%s_%d%s" % (base, ti, ext) if ti > 0 else fname
                else:
                    out = fname
                widget._export_matplotlib(out)
                print("Exported: %s" % out)
                break
        self.app.quit()
