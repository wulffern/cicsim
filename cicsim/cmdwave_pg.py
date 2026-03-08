#!/usr/bin/env python3

"""
Waveform viewer using PySide6 + pyqtgraph.

Install:  pip install PySide6 pyqtgraph
"""

import os
import sys
import re
import numpy as np

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTreeWidget, QTreeWidgetItem, QLineEdit, QTabWidget,
    QPushButton, QLabel, QCheckBox, QTextEdit, QFileDialog, QDialog)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QFont, QShortcut, QPainter

import pyqtgraph as pg

from .wavefiles import WaveFile, WaveFiles
from matplotlib.ticker import EngFormatter


CURSOR_A_COLOR = '#2196F3'
CURSOR_B_COLOR = '#FF9800'
ZOOM_FACTOR = 1.3

WAVE_COLORS = [
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
    '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
    '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
]


def _eng(value, unit=""):
    return EngFormatter(unit=unit)(value)


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
            self.curve.setData(np.real(self.x), np.real(self.y))

    def plot(self, target, color='w'):
        """Plot on a PlotItem or ViewBox. Returns the curve or None."""
        if self.y is None:
            return None
        y = np.real(self.y)
        x = np.real(self.x) if self.x is not None else np.arange(len(y))
        self.color = color
        self.curve = pg.PlotDataItem(x, y, pen=pg.mkPen(color, width=1),
                                     name=self.ylabel)
        target.addItem(self.curve)
        return self.curve

    def remove(self):
        if self.curve:
            self.curve.getViewBox().removeItem(self.curve)
            self.curve = None
        self.color = None


class PgWaveBrowser(QWidget):
    waveSelected = Signal(object)
    waveRemoveRequested = Signal(object)

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
        self.wave_tree.itemClicked.connect(self._wave_clicked)
        self.wave_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.wave_tree.customContextMenuRequested.connect(self._wave_context)

        layout.addWidget(self.file_tree, 1)
        layout.addLayout(search_row)
        layout.addWidget(self.wave_tree, 3)

    def openFile(self, fname):
        f = self.files.open(fname, self.xaxis)
        item = QTreeWidgetItem([f.name])
        item.setData(0, Qt.UserRole, fname)
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
            item.setForeground(0, QColor('#e0e0e0'))

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
            return
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        menu.addAction("Remove from plot", lambda: self.waveRemoveRequested.emit(
            self._wave_cache[tag]))
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
        self.readout.setStyleSheet(
            "background-color: #2b2b2b; color: #e0e0e0;")
        layout.addWidget(self.readout)

        self.status = QLabel("")
        self.status.setFont(font)
        self.status.setStyleSheet(
            "background-color: #2b2b2b; color: #e0e0e0; padding: 2px;")
        layout.addWidget(self.status)

        self.plot = self.gw.addPlot(row=0, col=0)
        self.plot.showGrid(x=True, y=True, alpha=0.3)
        self.plot.vb.wheelEvent = lambda ev: self._on_wheel(ev)
        self._orig_mouseDragEvent = self.plot.vb.mouseDragEvent
        self.plot.vb.mouseDragEvent = self._on_mouse_drag

        self._unit_vb = {}
        self._right_vb = None
        self._logx = False

        self.wave_data = {}
        self._color_index = 0
        self._legend_visible = False
        self._legend = None

        self.cursor_a = None
        self.cursor_b = None
        self._cursor_a_lines = []
        self._cursor_b_lines = []
        self._delta_texts = []
        self._last_x = None

        self.gw.scene().sigMouseMoved.connect(self._on_mouse_moved)

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
        vbs = self._all_viewboxes()
        for i, vb in enumerate(vbs):
            if self.cursor_a is not None and i >= len(self._cursor_a_lines):
                line = self._make_cursor_line(
                    self.cursor_a, CURSOR_A_COLOR, 'a')
                vb.addItem(line)
                self._cursor_a_lines.append(line)
            if self.cursor_b is not None and i >= len(self._cursor_b_lines):
                line = self._make_cursor_line(
                    self.cursor_b, CURSOR_B_COLOR, 'b')
                vb.addItem(line)
                self._cursor_b_lines.append(line)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show_wave(self, wave):
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

        color = WAVE_COLORS[self._color_index % len(WAVE_COLORS)]
        self._color_index += 1
        curve = wave.plot(vb, color=color)
        if curve is None:
            return None

        self.wave_data[wave.tag] = (wave, yunit)

        if vb is self.plot.vb:
            self.plot.vb.enableAutoRange()
            self.plot.vb.autoRange()
        else:
            vb.enableAutoRange()
            vb.autoRange()

        return (wave.tag, color)

    def removeLine(self, wave):
        """Remove a single wave from the plot. Returns the tag if removed."""
        tag = wave.tag
        if tag in self.wave_data:
            self._remove_wave(tag)
            return tag
        return None

    def removeAll(self):
        tags = list(self.wave_data.keys())
        for tag in tags:
            self._remove_wave(tag)
        self._reset_axes()
        return tags

    def autoSize(self):
        for vb in self._all_viewboxes():
            vb.enableAutoRange()
            vb.autoRange()

    def reloadAll(self):
        for tag, (wave, _) in self.wave_data.items():
            wave.reload()
        self.autoSize()

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
        if fname.lower().endswith('.svg'):
            from pyqtgraph.exporters import SVGExporter
            SVGExporter(self.gw.scene()).export(fname)
        elif fname.lower().endswith('.png'):
            from pyqtgraph.exporters import ImageExporter
            ImageExporter(self.gw.scene()).export(fname)
        else:
            try:
                from PySide6.QtPrintSupport import QPrinter
                printer = QPrinter(QPrinter.HighResolution)
                printer.setOutputFormat(QPrinter.PdfFormat)
                printer.setOutputFileName(fname)
                painter = QPainter(printer)
                self.gw.render(painter)
                painter.end()
            except ImportError:
                from pyqtgraph.exporters import ImageExporter
                if not fname.lower().endswith('.png'):
                    fname += '.png'
                ImageExporter(self.gw.scene()).export(fname)

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

    # --- Cursors ---

    def _make_cursor_line(self, x, color, which):
        line = pg.InfiniteLine(
            pos=x, angle=90, movable=True,
            pen=pg.mkPen(color, width=1, style=Qt.DashLine))
        line.sigPositionChanged.connect(
            lambda l, w=which: self._cursor_dragged(w, l))
        return line

    def _set_cursor(self, which, x):
        color = CURSOR_A_COLOR if which == 'a' else CURSOR_B_COLOR
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

    def _on_wheel(self, event):
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

        text_item = pg.TextItem(
            text="\n".join(parts), color='#e0e0e0', anchor=(0.5, 0),
            fill=pg.mkBrush(51, 51, 51, 220))
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

    def _update_readout(self):
        if self.cursor_a is None and self.cursor_b is None:
            self.readout.clear()
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
            wparts = ["  %-22s" % wave.key]
            ya = self._interp_y(wave, self.cursor_a)
            yb = self._interp_y(wave, self.cursor_b)
            if ya is not None:
                wparts.append("A: %-14s" % _eng(ya, yu))
            if yb is not None:
                wparts.append("B: %-14s" % _eng(yb, yu))
            if ya is not None and yb is not None:
                wparts.append("Δ: %-14s" % _eng(yb - ya, yu))
            lines.append("".join(wparts))

        self.readout.setPlainText("\n".join(lines))


class PgWaveWindow(QMainWindow):
    def __init__(self, xaxis):
        super().__init__()
        self.setWindowTitle("cIcWave: %s" % os.getcwd())
        self.resize(1200, 700)

        splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(splitter)

        self.browser = PgWaveBrowser(xaxis)
        self.tab_widget = QTabWidget()

        splitter.addWidget(self.browser)
        splitter.addWidget(self.tab_widget)
        splitter.setSizes([250, 950])

        self.plot_index = 0
        self._add_plot_tab()

        self.browser.waveSelected.connect(self._on_wave_selected)
        self.browser.waveRemoveRequested.connect(self._on_wave_remove)

        self._setup_menus()
        self._setup_shortcuts()

    def _setup_menus(self):
        mb = self.menuBar()

        m = mb.addMenu("File")
        m.addAction("Open Raw          Ctrl+O", self._open_file)
        m.addAction("Export PDF        Ctrl+P", self._export_pdf)
        m.addSeparator()
        m.addAction("Quit              Ctrl+Q", self.close)

        m = mb.addMenu("Edit")
        m.addAction("New Plot          Ctrl+N", self._add_plot_tab)
        m.addSeparator()
        m.addAction("Reload All        R", self._reload)
        m.addAction("Auto Scale        F", self._auto_size)
        m.addSeparator()
        m.addAction("Remove All", self._remove_all)

        m = mb.addMenu("View")
        m.addAction("Set Cursor A      A", self._cursor_a)
        m.addAction("Set Cursor B      B", self._cursor_b)
        m.addAction("Clear Cursors     Escape", self._clear_cursors)
        m.addSeparator()
        m.addAction("Toggle Legend      L", self._toggle_legend)

        m = mb.addMenu("Help")
        m.addAction("Keyboard Shortcuts", self._show_help)

    def _setup_shortcuts(self):
        for seq, func in [
            ("Ctrl+O", self._open_file),
            ("Ctrl+P", self._export_pdf),
            ("Ctrl+Q", self.close),
            ("Ctrl+N", self._add_plot_tab),
            ("Escape", self._clear_cursors),
        ]:
            QShortcut(QKeySequence(seq), self, func)

    def keyPressEvent(self, event):
        if isinstance(self.focusWidget(), QLineEdit):
            super().keyPressEvent(event)
            return
        p = self._current()
        key = event.text().lower()
        if p and key == 'a':
            p.placeCursorA()
        elif p and key == 'b':
            p.placeCursorB()
        elif p and key == 'f':
            p.autoSize()
        elif p and key == 'r':
            p.reloadAll()
        elif p and key == 'l':
            p.toggleLegend()
        else:
            super().keyPressEvent(event)

    def _current(self):
        return self.tab_widget.currentWidget()

    def _add_plot_tab(self):
        plot = PgWavePlot()
        self.tab_widget.addTab(plot, "Plot %d" % self.plot_index)
        self.plot_index += 1
        self.tab_widget.setCurrentWidget(plot)

    def _on_wave_selected(self, wave):
        p = self._current()
        if p:
            result = p.show_wave(wave)
            if result:
                tag, color = result
                self.browser.setWaveColor(tag, color)

    def _on_wave_remove(self, wave):
        p = self._current()
        if p:
            tag = p.removeLine(wave)
            if tag:
                self.browser.clearWaveColor(tag)

    def _open_file(self):
        fname, _ = QFileDialog.getOpenFileName(
            self, "Open Raw File", os.getcwd())
        if fname:
            self.browser.openFile(fname)

    def _export_pdf(self):
        p = self._current()
        if p:
            p.exportPdf()

    def _reload(self):
        p = self._current()
        if p:
            p.reloadAll()

    def _auto_size(self):
        p = self._current()
        if p:
            p.autoSize()

    def _remove_all(self):
        p = self._current()
        if p:
            tags = p.removeAll()
            for tag in tags:
                self.browser.clearWaveColor(tag)

    def _cursor_a(self):
        p = self._current()
        if p:
            p.placeCursorA()

    def _cursor_b(self):
        p = self._current()
        if p:
            p.placeCursorB()

    def _clear_cursors(self):
        p = self._current()
        if p:
            p.clearCursors()

    def _toggle_legend(self):
        p = self._current()
        if p:
            p.toggleLegend()

    def _show_help(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Keyboard Shortcuts")
        layout = QVBoxLayout(dlg)
        text = QLabel(
            "Keyboard Shortcuts\n"
            "══════════════════════════════\n"
            "\n"
            "File\n"
            "  Ctrl+O        Open raw file\n"
            "  Ctrl+P        Export PDF\n"
            "  Ctrl+Q        Quit\n"
            "\n"
            "Edit\n"
            "  Ctrl+N        New plot tab\n"
            "  R             Reload all waves\n"
            "  F             Auto scale (fit)\n"
            "\n"
            "Cursors\n"
            "  A             Set cursor A at mouse\n"
            "  B             Set cursor B at mouse\n"
            "  Escape        Clear cursors\n"
            "  Drag cursor   Move cursor\n"
            "\n"
            "View\n"
            "  L             Toggle legend\n"
            "\n"
            "Mouse\n"
            "  Left-drag          Pan\n"
            "  Scroll             Zoom x-axis\n"
            "  Shift+Scroll       Zoom y-axis\n"
            "  Shift+Right-drag   Zoom x-axis\n"
            "  Ctrl+Right-drag    Zoom y-axis\n"
            "  Right-click        Context menu\n"
            "\n"
            "Browser\n"
            "  Click wave    Add to plot\n"
            "  Right-click   Remove from plot\n"
        )
        text.setFont(QFont("Courier", 11))
        text.setStyleSheet(
            "background-color: #2b2b2b; color: #e0e0e0; padding: 16px;")
        layout.addWidget(text)
        btn = QPushButton("Close")
        btn.clicked.connect(dlg.accept)
        layout.addWidget(btn)
        dlg.exec()

    def openFile(self, fname):
        self.browser.openFile(fname)


class CmdWavePg:
    def __init__(self, xaxis):
        self.xaxis = xaxis
        self.app = QApplication.instance() or QApplication(sys.argv)
        pg.setConfigOptions(antialias=True, useOpenGL=False,
                            background='k', foreground='w')
        self.win = PgWaveWindow(xaxis)

    def openFile(self, fname):
        self.win.openFile(fname)

    def run(self):
        self.win.show()
        self.app.exec()
