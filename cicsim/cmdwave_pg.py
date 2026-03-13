#!/usr/bin/env python3

"""
Waveform viewer using PySide6 + pyqtgraph.

Install:  pip install PySide6 pyqtgraph
"""

import os
import sys
import re
import numpy as np
from importlib.metadata import version as _pkg_version

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTreeWidget, QTreeWidgetItem, QLineEdit, QTabWidget,
    QPushButton, QLabel, QCheckBox, QTextEdit, QFileDialog, QDialog,
    QInputDialog, QMenu, QComboBox)
from PySide6 import QtCore
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QFont, QShortcut, QPainter, QColor, QPalette

import pyqtgraph as pg

from .wavefiles import WaveFile, WaveFiles
from matplotlib.ticker import EngFormatter


ZOOM_FACTOR = 1.3

THEMES = {
    'dark': {
        'pg_background': 'k',
        'pg_foreground': 'w',
        'panel_bg': '#2b2b2b',
        'panel_fg': '#e0e0e0',
        'text_color': '#e0e0e0',
        'overlay_fill': (51, 51, 51, 220),
        'annotation_fill': (51, 51, 51, 200),
        'annotation_border': 'w',
        'title_color': 'w',
        'tree_default_fg': '#e0e0e0',
        'cursor_a': '#2196F3',
        'cursor_b': '#FF9800',
        'wave_colors': [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
            '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
            '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
        ],
        'export_colors': [
            '#0060a8', '#d45800', '#1a8a1a', '#c02020', '#7040a0',
            '#6b4226', '#b8439e', '#505050', '#8a8c00', '#008fa8',
            '#2980b9', '#e67e22', '#27ae60', '#e74c3c', '#8e44ad',
        ],
        'export_annotation_color': '#333333',
        'export_annotation_bg': '#ffffcc',
        'export_annotation_ec': '#888888',
        'export_stats_color': '#666666',
        'palette': {
            'Window': (43, 43, 43),
            'WindowText': (224, 224, 224),
            'Base': (30, 30, 30),
            'AlternateBase': (43, 43, 43),
            'ToolTipBase': (43, 43, 43),
            'ToolTipText': (224, 224, 224),
            'Text': (224, 224, 224),
            'Button': (53, 53, 53),
            'ButtonText': (224, 224, 224),
            'BrightText': (255, 50, 50),
            'Link': (42, 130, 218),
            'Highlight': (42, 130, 218),
            'HighlightedText': (0, 0, 0),
        },
    },
    'light': {
        'pg_background': 'w',
        'pg_foreground': 'k',
        'panel_bg': '#f0f0f0',
        'panel_fg': '#1a1a1a',
        'text_color': '#1a1a1a',
        'overlay_fill': (240, 240, 240, 230),
        'annotation_fill': (255, 255, 240, 220),
        'annotation_border': '#888888',
        'title_color': 'k',
        'tree_default_fg': '#1a1a1a',
        'cursor_a': '#1565C0',
        'cursor_b': '#E65100',
        'wave_colors': [
            '#0060a8', '#d45800', '#1a8a1a', '#c02020', '#7040a0',
            '#6b4226', '#b8439e', '#505050', '#8a8c00', '#008fa8',
            '#2980b9', '#e67e22', '#27ae60', '#e74c3c', '#8e44ad',
        ],
        'export_colors': [
            '#0060a8', '#d45800', '#1a8a1a', '#c02020', '#7040a0',
            '#6b4226', '#b8439e', '#505050', '#8a8c00', '#008fa8',
            '#2980b9', '#e67e22', '#27ae60', '#e74c3c', '#8e44ad',
        ],
        'export_annotation_color': '#333333',
        'export_annotation_bg': '#ffffcc',
        'export_annotation_ec': '#888888',
        'export_stats_color': '#666666',
        'palette': {
            'Window': (240, 240, 240),
            'WindowText': (26, 26, 26),
            'Base': (255, 255, 255),
            'AlternateBase': (245, 245, 245),
            'ToolTipBase': (255, 255, 220),
            'ToolTipText': (26, 26, 26),
            'Text': (26, 26, 26),
            'Button': (225, 225, 225),
            'ButtonText': (26, 26, 26),
            'BrightText': (200, 30, 30),
            'Link': (42, 130, 218),
            'Highlight': (42, 130, 218),
            'HighlightedText': (255, 255, 255),
        },
    },
}

_active_theme = THEMES['dark']


def _get_theme():
    return _active_theme

PLOT_STYLES = ['Lines', 'Markers', 'Lines+Markers', 'Steps']


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


def _eng(value, unit=""):
    return EngFormatter(unit=unit)(value)


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
    """Modal dialog with regex-filtered signal list."""

    def __init__(self, parent, title, names):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(400, 500)
        self._names = names

        layout = QVBoxLayout(self)
        self._search = QLineEdit()
        self._search.setPlaceholderText("Regex filter…")
        self._search.textChanged.connect(self._filter)
        layout.addWidget(self._search)

        from PySide6.QtWidgets import QListWidget
        self._list = QListWidget()
        self._list.addItems(names)
        self._list.itemDoubleClicked.connect(self.accept)
        layout.addWidget(self._list)

        row = QHBoxLayout()
        ok = QPushButton("OK")
        ok.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        row.addWidget(ok)
        row.addWidget(cancel)
        layout.addLayout(row)

    def _filter(self, text):
        self._list.clear()
        try:
            pat = re.compile(text, re.IGNORECASE)
        except re.error:
            pat = None
        for n in self._names:
            if not pat or pat.search(n):
                self._list.addItem(n)

    def selected(self):
        items = self._list.selectedItems()
        if items:
            return items[0].text()
        if self._list.count() > 0:
            return self._list.item(0).text()
        return None


class PgWave:
    """Associates a WaveFile column with a pyqtgraph PlotDataItem."""

    def __init__(self, wfile, key, xaxis):
        self.wfile = wfile
        self.key = key
        self.xaxis = xaxis
        self.x = None
        self.y = None
        self.xlabel = "Samples"
        self.xunit = ""
        self.yunit = self._infer_yunit(key)
        self.ylabel = "%s (%s)" % (key, wfile.name)
        self.logx = False
        self.tag = wfile.getTag(key)
        self.curve = None
        self.color = None
        self._xlabels = None
        self._ylabels = None
        self.reload()

    @staticmethod
    def _infer_yunit(key):
        kl = key.lower()
        if kl.startswith("v(") or kl.startswith("v-"):
            return "V"
        if kl.startswith("i(") or kl.startswith("i-"):
            return "A"
        return ""

    def reload(self):
        self.wfile.reload()
        keys = self.wfile.df.columns

        if "time" in keys:
            self.x = self.wfile.df["time"].to_numpy()
            self.xlabel = "Time"
            self.xunit = "s"
        elif "frequency" in keys:
            self.x = self.wfile.df["frequency"].to_numpy()
            self.xlabel = "Frequency"
            self.xunit = "Hz"
            self.logx = True
        elif "v(v-sweep)" in keys:
            self.x = self.wfile.df["v(v-sweep)"].to_numpy()
            self.xlabel = "Voltage"
            self.xunit = "V"
        elif "i(i-sweep)" in keys:
            self.x = self.wfile.df["i(i-sweep)"].to_numpy()
            self.xlabel = "Current"
            self.xunit = "A"
        elif "temp-sweep" in keys:
            self.x = self.wfile.df["temp-sweep"].to_numpy()
            self.xlabel = "Temperature"
            self.xunit = "°C"
        elif self.xaxis in keys:
            self.x = self.wfile.df[self.xaxis].to_numpy()
            self.xlabel = self.xaxis
            self.xunit = ""

        if self.key in keys:
            self.y = self.wfile.df[self.key].to_numpy()

        if self.curve and self.x is not None and self.y is not None:
            x, _ = _to_numeric(self.x)
            y, _ = _to_numeric(self.y)
            self.curve.setData(x, y)

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
        self.curve = pg.PlotDataItem(x, y, name=self.ylabel, **kw)
        target.addItem(self.curve)
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

    def remove(self):
        if self.curve:
            self.curve.getViewBox().removeItem(self.curve)
            self.curve = None
        self.color = None


class PgWaveBrowser(QWidget):
    waveSelected = Signal(object)
    waveRemoveRequested = Signal(object)
    analysisRequested = Signal(str, object)  # (analysis_type, wave)
    styleChanged = Signal(str)

    def __init__(self, xaxis, parent=None):
        super().__init__(parent)
        self.xaxis = xaxis
        self.files = WaveFiles()
        self._wave_cache = {}
        self._tag_to_item = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)

        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderLabel("Files")
        self.file_tree.currentItemChanged.connect(self._file_selected)

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

        self.wave_tree = QTreeWidget()
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

    def _toggle_flat(self, checked):
        self._flat_mode = checked
        self._fill_waves()

    @staticmethod
    def _parse_hierarchy(name):
        """Split 'v(xdut.x1.node)' → ['xdut', 'x1', 'v(node)'].

        The instance path forms the hierarchy; the leaf keeps v()/i().
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
        return [name]

    def _fill_waves(self):
        self.wave_tree.clear()
        self._tag_to_item = {}
        f = self.files.getSelected()
        if f is None:
            return
        pattern = self.search.text()

        names = [n for n in f.getWaveNames()
                 if not pattern or re.search(pattern, n, re.IGNORECASE)]

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

    def _wave_context(self, pos):
        item = self.wave_tree.itemAt(pos)
        if not item:
            return
        yname = item.data(0, Qt.UserRole)
        if not yname:
            return
        f = self.files.getSelected()
        tag = f.getTag(yname)

        if tag not in self._wave_cache:
            self._wave_cache[tag] = PgWave(f, yname, self.xaxis)

        wave = self._wave_cache[tag]
        wave.reload()

        menu = QMenu(self)
        menu.addAction("Plot", lambda: self.waveSelected.emit(wave))
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

        font = QFont("Courier", 9)
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
        self.plot.showGrid(x=True, y=True, alpha=0.3)
        self.plot.vb.wheelEvent = lambda ev: self._on_wheel(ev)
        self._orig_mouseDragEvent = self.plot.vb.mouseDragEvent
        self.plot.vb.mouseDragEvent = self._on_mouse_drag

        self._unit_vb = {}
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

    def _get_or_create_vb(self, yunit):
        """Return the ViewBox for a given yunit, creating axes as needed."""
        if yunit in self._unit_vb:
            return self._unit_vb[yunit]

        if not self._unit_vb:
            self._unit_vb[yunit] = self.plot.vb
            if yunit:
                self.plot.setLabel('left', units=yunit)
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
        if yunit:
            self.plot.setLabel('right', units=yunit)

        self._ensure_cursors_on_right_vb()
        return self._right_vb

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
    # Public API
    # ------------------------------------------------------------------

    def show_wave(self, wave, style='Lines'):
        """Plot a wave. Returns (tag, color) on success, else None."""
        if wave.tag in self.wave_data:
            return None

        yunit = wave.yunit or ""

        if not self.wave_data:
            if wave.xunit:
                self.plot.setLabel('bottom', wave.xlabel, units=wave.xunit)
            if wave.logx:
                self.plot.setLogMode(x=True)
                self._logx = True

        vb = self._get_or_create_vb(yunit)

        theme = _get_theme()
        wcolors = theme['wave_colors']
        color = wcolors[self._color_index % len(wcolors)]
        self._color_index += 1

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

    def autoSize(self):
        for vb in self._all_viewboxes():
            vb.enableAutoRange()
            vb.autoRange()

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
        font = QFont("Courier", size)
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

        if not self.wave_data:
            return

        fig, ax = plt.subplots(figsize=(10, 5))

        units_left = set()
        units_right = set()
        ax_right = None
        tags = list(self.wave_data.keys())

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
        fig.tight_layout()
        fig.subplots_adjust(bottom=max(0.15, fig.subplotpars.bottom))
        dpi = 150 if fname.lower().endswith('.png') else None
        fig.savefig(fname, dpi=dpi, facecolor='white')
        plt.close(fig)

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
            wave.remove()
            del self.wave_data[tag]

    def _reset_axes(self):
        self._unit_vb.clear()
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

    # --- Scroll zoom (matches tk implementation) ---

    def _on_wheel(self, event, axis=None):
        delta = event.delta()
        if delta == 0:
            return

        scale = 1.0 / ZOOM_FACTOR if delta > 0 else ZOOM_FACTOR
        pos = event.pos()
        mouse_point = self.plot.vb.mapSceneToView(pos)

        modifiers = event.modifiers()
        if modifiers & Qt.ShiftModifier:
            for vb in self._all_viewboxes():
                vr = vb.viewRange()
                ylo, yhi = vr[1]
                pt = vb.mapSceneToView(pos)
                ydata = pt.y()
                new_lo = ydata - (ydata - ylo) * scale
                new_hi = ydata + (yhi - ydata) * scale
                vb.setYRange(new_lo, new_hi, padding=0)
        else:
            vr = self.plot.vb.viewRange()
            xlo, xhi = vr[0]
            xdata = mouse_point.x()
            new_lo = xdata - (xdata - xlo) * scale
            new_hi = xdata + (xhi - xdata) * scale
            self.plot.vb.setXRange(new_lo, new_hi, padding=0)

        event.accept()

    def _on_mouse_drag(self, ev, axis=None):
        mods = ev.modifiers()
        if ev.button() == Qt.RightButton and (
                mods & Qt.ShiftModifier or mods & Qt.ControlModifier):
            ev.accept()
            if ev.isFinish():
                return
            delta = ev.pos() - ev.lastPos()
            vb = self.plot.vb
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
                for vbox in self._all_viewboxes():
                    yr = vbox.viewRange()[1]
                    ylo, yhi = yr
                    yspan = yhi - ylo
                    vbox.setYRange(ylo - dy * yspan, yhi + dy * yspan,
                                   padding=0)
        else:
            self._orig_mouseDragEvent(ev, axis)

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
        text_item.setFont(QFont("Courier", 8))
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
            lines.append("  %-22s  min: %-12s  max: %-12s  μ: %-12s  σ: %-12s  pp: %s" % (
                s['key'], _eng(s['min'], u), _eng(s['max'], u),
                _eng(s['mean'], u), _eng(s['std'], u), _eng(s['pp'], u)))
        self.readout.setPlainText("\n".join(lines))

    def addAnnotation(self, x, y, text):
        theme = _get_theme()
        item = pg.TextItem(text=text, color=theme['text_color'], anchor=(0, 1),
                           fill=pg.mkBrush(*theme['annotation_fill']),
                           border=theme['annotation_border'])
        item.setFont(QFont("Courier", 9))
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
            lines.append("".join(wparts))

        self.readout.setPlainText("\n".join(lines))


class PgAnalysisPlot(QWidget):
    """Lightweight analysis tab with basic A/B cursors and readout."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)

        self.pw = pg.PlotWidget()
        self.pw.showGrid(x=True, y=True, alpha=0.3)
        vb = self.pw.plotItem.vb
        vb.wheelEvent = self._on_wheel
        self._orig_drag = vb.mouseDragEvent
        vb.mouseDragEvent = self._on_mouse_drag
        layout.addWidget(self.pw, 1)

        font = QFont("Courier", 9)
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
        font = QFont("Courier", size)
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

        self._setup_menus()
        self._setup_shortcuts()

    def _setup_menus(self):
        mb = self.menuBar()

        m = mb.addMenu("File")
        m.addAction("Open File         Ctrl+O", self._open_file)
        m.addAction("Save Session      Ctrl+S", self._save_session)
        m.addAction("Load Session", self._load_session)
        m.addSeparator()
        m.addAction("Export PDF        Ctrl+P", self._export_pdf)
        m.addSeparator()
        m.addAction("Quit              Ctrl+Q", self.close)

        m = mb.addMenu("Edit")
        m.addAction("New Plot          Ctrl+N", self._add_plot_tab)
        m.addAction("Close Tab         Ctrl+W", self._close_current_tab)
        m.addSeparator()
        m.addAction("Set Axis Labels   Ctrl+L", self._set_axis_labels)
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

    def keyPressEvent(self, event):
        if isinstance(self.focusWidget(), QLineEdit):
            super().keyPressEvent(event)
            return
        p = self._current()
        key = event.text()
        mods = event.modifiers()
        if p and key == 'Z' and hasattr(p, 'zoomIn'):
            p.zoomIn()
        elif p and key.lower() == 'z' and mods & Qt.ControlModifier and hasattr(p, 'zoomOut'):
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

    def _on_wave_selected(self, wave):
        p = self._current()
        if p:
            result = p.show_wave(wave, style=self.browser.plotStyle)
            if result:
                tag, color = result
                self.browser.setWaveColor(tag, color)

    def _on_wave_remove(self, wave):
        p = self._current()
        if p:
            tag = p.removeLine(wave)
            if tag:
                self.browser.clearWaveColor(tag)

    def _on_style_changed(self, style):
        p = self._current()
        if p and hasattr(p, 'setAllStyles'):
            p.setAllStyles(style)

    def _open_file(self):
        fname, _ = QFileDialog.getOpenFileName(
            self, "Open File", os.getcwd(),
            "All Supported (*.raw *.csv *.tsv *.txt *.xlsx *.xls *.ods *.pkl *.pickle *.json *.parquet *.feather *.h5 *.hdf5);;Raw Files (*.raw);;CSV/TSV (*.csv *.tsv *.txt);;Excel (*.xlsx *.xls *.ods);;Pickle (*.pkl *.pickle);;JSON (*.json);;Parquet (*.parquet);;Feather (*.feather);;HDF5 (*.h5 *.hdf5);;All Files (*)")
        if fname:
            self.browser.openFile(fname)

    def _export_pdf(self):
        p = self._current()
        if p and hasattr(p, 'exportPdf'):
            p.exportPdf()

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
            if hasattr(w, 'pw'):
                w.pw.setBackground(theme['pg_background'])

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
            "  Ctrl+Q        Quit\n"
            "\n"
            "Edit\n"
            "  Ctrl+N        New plot tab\n"
            "  Ctrl+W        Close current tab\n"
            "  Ctrl+L        Set axis labels\n"
            "  Ctrl+T        Add annotation\n"
            "  R             Reload all waves\n"
            "  F             Auto scale (fit)\n"
            "  Shift+Z       Zoom in\n"
            "  Ctrl+Z        Zoom out\n"
            "\n"
            "Cursors\n"
            "  A             Set cursor A at mouse\n"
            "  B             Set cursor B at mouse\n"
            "  Escape        Clear cursors\n"
            "  Drag cursor   Move cursor\n"
            "\n"
            "View\n"
            "  L             Toggle legend\n"
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
        text.setFont(QFont("Courier", 11))
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
        dlg = _SignalPickerDialog(self, "Select X-axis signal", names)
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
    global _active_theme
    _active_theme = THEMES[theme_name]
    theme = _active_theme
    app.setStyle("Fusion")
    p = QPalette()
    for role_name, rgb in theme['palette'].items():
        p.setColor(getattr(QPalette, role_name), QColor(*rgb))
    p.setColor(QPalette.Disabled, QPalette.Text, QColor(128, 128, 128))
    p.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(128, 128, 128))
    app.setPalette(p)
    pg.setConfigOptions(background=theme['pg_background'],
                        foreground=theme['pg_foreground'])


class CmdWavePg:
    def __init__(self, xaxis, theme='dark'):
        self.xaxis = xaxis
        self.app = QApplication.instance() or QApplication(sys.argv)
        pg.setConfigOptions(antialias=True, useOpenGL=False)
        _apply_theme(self.app, theme)
        self.win = PgWaveWindow(xaxis)

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
