#!/usr/bin/env python3

from tkinter import *
from tkinter import ttk
import tkinter
import tkinter.filedialog
import os
import numpy as np
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,
                                               NavigationToolbar2Tk)
from matplotlib.figure import Figure
from matplotlib.ticker import EngFormatter

from .cmdwave_pg import _get_theme

CURSOR_KWARGS = {'linestyle': '--', 'linewidth': 1.0, 'alpha': 0.8}
DRAG_TOLERANCE_PX = 10
ZOOM_FACTOR = 1.3


class WavePlot(ttk.PanedWindow):

    def __init__(self, master, **kw):
        super().__init__(master, orient=HORIZONTAL, **kw)

        # --- Left panel: wave list and controls ---
        left = ttk.Frame(self)
        self.add(left)

        self.combo = ttk.Combobox(left)
        self.combo.grid(column=0, row=0, columnspan=2, sticky=(N, E, W))
        self.combo.state(["readonly"])
        self.combo.bind('<<ComboboxSelected>>', self._set_axis_index)

        self.tree = ttk.Treeview(left)
        self.tree.grid(column=0, row=1, columnspan=2, sticky=(N, S, E, W))

        ttk.Button(left, text="Remove", command=self.removeLine).grid(
            column=0, row=2, sticky=(S, E, W))
        ttk.Button(left, text="Remove All", command=self.removeAll).grid(
            column=1, row=2, sticky=(S, E, W))
        ttk.Button(left, text="Reload", command=self.reloadAll).grid(
            column=0, row=3, sticky=(S, E, W))
        ttk.Button(left, text="Auto Scale", command=self.autoSize).grid(
            column=1, row=3, sticky=(S, E, W))
        ttk.Button(left, text="Add Axis", command=self.addAxis).grid(
            column=0, row=4, sticky=(S, E, W))
        ttk.Button(left, text="Rm Axis", command=self.removeAxis).grid(
            column=1, row=4, sticky=(S, E, W))
        ttk.Button(left, text="Legend", command=self.toggleLegend).grid(
            column=0, row=5, sticky=(S, E, W))
        ttk.Button(left, text="Export PDF", command=self.exportPdf).grid(
            column=1, row=5, sticky=(S, E, W))

        left.columnconfigure(0, weight=1)
        left.columnconfigure(1, weight=1)
        left.rowconfigure(1, weight=1)

        # --- Right panel: figure, toolbar, readout ---
        right = ttk.Frame(self)
        self.add(right)

        self.fig = Figure(dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=right)
        self.toolbar = NavigationToolbar2Tk(self.canvas, right, pack_toolbar=False)
        self.toolbar.update()

        theme = _get_theme()
        self.readout = Text(right, height=1, font=("Courier", 9),
                            state=DISABLED, bg=theme['panel_bg'],
                            fg=theme['panel_fg'],
                            wrap=NONE, borderwidth=1, relief="sunken",
                            insertbackground='white')
        self.status_var = StringVar(value="")
        self.status = tkinter.Label(right, textvariable=self.status_var,
                                    font=("Courier", 9), anchor=W,
                                    bg=theme['panel_bg'],
                                    fg=theme['panel_fg'])

        self.canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=True)
        self.toolbar.pack(side=TOP, fill=X)
        self.readout.pack(side=TOP, fill=X, padx=2, pady=(2, 0))
        self.status.pack(side=BOTTOM, fill=X, padx=2)

        # --- State ---
        self.axes = []
        self._num_axes = 0
        self.axis_index = 0
        self.wave_data = {}
        self._legend_visible = False

        # Cursor state
        self.cursor_a_x = None
        self.cursor_b_x = None
        self._cursor_a_lines = []
        self._cursor_b_lines = []
        self._delta_annotations = []
        self._dragging = None
        self._last_mouse_x = None

        # --- Events ---
        self.canvas.mpl_connect('button_press_event', self._on_press)
        self.canvas.mpl_connect('button_release_event', self._on_release)
        self.canvas.mpl_connect('motion_notify_event', self._on_motion)
        self.canvas.mpl_connect('scroll_event', self._on_scroll)
        self.canvas.mpl_connect('key_press_event', self._on_key)

        self.addAxis()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show(self, wave):
        if wave.tag in self.wave_data:
            return

        idx = self.axis_index
        wave.plot(self.axes[idx])
        self.wave_data[wave.tag] = (wave, idx)

        if idx == 0 and len(self.wave_data) == 1:
            self.axes[0].set_xlabel(wave.xlabel)

        text = "A%d: %s" % (idx, wave.ylabel)
        self.tree.insert('', 'end', wave.tag, text=text, tags=(wave.tag,))
        self.tree.tag_configure(wave.tag, foreground=wave.line.get_color())

        self._create_cursor_lines()
        self.canvas.draw_idle()

    def removeAll(self):
        for tag in list(self.tree.get_children()):
            self._remove_tag(tag)
        self.canvas.draw_idle()

    def removeLine(self):
        tag = self.tree.focus()
        self._remove_tag(tag)
        self.canvas.draw_idle()

    def addAxis(self):
        self._num_axes += 1
        self._rebuild_axes()
        self.axis_index = self._num_axes - 1
        self._update_combo()

    def removeAxis(self):
        if self._num_axes <= 1:
            return
        last = self._num_axes - 1
        tags_to_remove = [t for t, (_, ai) in self.wave_data.items() if ai == last]
        for t in tags_to_remove:
            self._remove_tag(t)
        self._num_axes -= 1
        self.axis_index = min(self.axis_index, self._num_axes - 1)
        self._rebuild_axes()
        self._update_combo()

    def autoSize(self):
        for ax in self.axes:
            ax.relim()
            ax.autoscale_view(True, True, True)
        self.canvas.draw_idle()

    def zoomIn(self):
        self._keyboard_zoom(1.0 / ZOOM_FACTOR)

    def zoomOut(self):
        self._keyboard_zoom(ZOOM_FACTOR)

    def _keyboard_zoom(self, scale):
        for ax in self.axes:
            xlo, xhi = ax.get_xlim()
            xmid = (xlo + xhi) / 2.0
            ax.set_xlim(xmid - (xmid - xlo) * scale,
                        xmid + (xhi - xmid) * scale)
            ylo, yhi = ax.get_ylim()
            ymid = (ylo + yhi) / 2.0
            ax.set_ylim(ymid - (ymid - ylo) * scale,
                        ymid + (yhi - ymid) * scale)
        self.canvas.draw_idle()

    def setLineWidth(self, width):
        for tag, (wave, _) in self.wave_data.items():
            if wave.line:
                wave.line.set_linewidth(width)
        self.canvas.draw_idle()

    def setFontSize(self, size):
        for ax in self.axes:
            ax.tick_params(axis='both', labelsize=size)
        self.readout.configure(font=("Courier", size))
        self.status.configure(font=("Courier", size))
        self.canvas.draw_idle()

    def reloadAll(self):
        for tag, (wave, _) in self.wave_data.items():
            wave.reload()
        self.autoSize()

    def clearCursors(self):
        for line in self._cursor_a_lines + self._cursor_b_lines:
            line.remove()
        self._cursor_a_lines.clear()
        self._cursor_b_lines.clear()
        self._clear_delta_annotations()
        self.cursor_a_x = None
        self.cursor_b_x = None
        self._update_readout()
        self.canvas.draw_idle()

    def toggleLegend(self):
        self._legend_visible = not self._legend_visible
        for ax in self.axes:
            legend = ax.get_legend()
            if self._legend_visible:
                ax.legend(loc='best', fontsize=7, framealpha=0.8)
            elif legend:
                legend.remove()
        self.canvas.draw_idle()

    def exportPdf(self):
        filename = tkinter.filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            initialdir=os.getcwd())
        if filename:
            self.fig.savefig(filename, bbox_inches='tight')

    # ------------------------------------------------------------------
    # Axis management
    # ------------------------------------------------------------------

    def _rebuild_axes(self):
        saved_xlim = self.axes[0].get_xlim() if self.axes else None
        saved_ylims = {i: ax.get_ylim() for i, ax in enumerate(self.axes)}

        self.fig.clear()
        n = self._num_axes

        if n == 1:
            self.axes = [self.fig.add_subplot(1, 1, 1)]
        else:
            axs = self.fig.subplots(n, 1, sharex=True)
            self.axes = list(axs)
            self.fig.subplots_adjust(hspace=0.08)

        for ax in self.axes:
            ax.grid(True, alpha=0.3)
            ax.tick_params(axis='both', which='major', labelsize=8)
        if n > 1:
            for ax in self.axes[:-1]:
                ax.tick_params(labelbottom=False)

        for tag, (wave, ax_idx) in list(self.wave_data.items()):
            ax_idx = min(ax_idx, n - 1)
            wave.line = None
            wave.plot(self.axes[ax_idx])
            self.wave_data[tag] = (wave, ax_idx)
            if self.tree.exists(tag) and wave.line:
                self.tree.tag_configure(tag, foreground=wave.line.get_color())

        if saved_xlim and self.axes:
            self.axes[0].set_xlim(saved_xlim)
        for i, ax in enumerate(self.axes):
            if i in saved_ylims:
                ax.set_ylim(saved_ylims[i])

        self._cursor_a_lines.clear()
        self._cursor_b_lines.clear()
        self._delta_annotations.clear()
        self._create_cursor_lines()
        self._update_delta_annotations()
        self.canvas.draw_idle()

    def _update_combo(self):
        labels = ["Axes %d" % i for i in range(self._num_axes)]
        self.combo['values'] = labels
        self.combo.current(self.axis_index)

    def _set_axis_index(self, event):
        self.axis_index = self.combo.current()

    def _remove_tag(self, tag):
        if not tag or not self.tree.exists(tag):
            return
        self.tree.delete(tag)
        if tag in self.wave_data:
            wave, _ = self.wave_data[tag]
            if wave.line:
                wave.line.remove()
                wave.line = None
            del self.wave_data[tag]

    # ------------------------------------------------------------------
    # Cursor system
    # ------------------------------------------------------------------

    def _create_cursor_lines(self):
        existing_a = len(self._cursor_a_lines)
        existing_b = len(self._cursor_b_lines)
        for i, ax in enumerate(self.axes):
            if self.cursor_a_x is not None and i >= existing_a:
                line = ax.axvline(self.cursor_a_x,
                                  color=_get_theme()['cursor_a'],
                                  **CURSOR_KWARGS)
                self._cursor_a_lines.append(line)
            if self.cursor_b_x is not None and i >= existing_b:
                line = ax.axvline(self.cursor_b_x,
                                  color=_get_theme()['cursor_b'],
                                  **CURSOR_KWARGS)
                self._cursor_b_lines.append(line)

    def _set_cursor(self, which, x):
        theme = _get_theme()
        if which == 'a':
            self.cursor_a_x = x
            if not self._cursor_a_lines:
                for ax in self.axes:
                    line = ax.axvline(x, color=theme['cursor_a'],
                                     **CURSOR_KWARGS)
                    self._cursor_a_lines.append(line)
            else:
                for line in self._cursor_a_lines:
                    line.set_xdata([x, x])
        else:
            self.cursor_b_x = x
            if not self._cursor_b_lines:
                for ax in self.axes:
                    line = ax.axvline(x, color=theme['cursor_b'],
                                     **CURSOR_KWARGS)
                    self._cursor_b_lines.append(line)
            else:
                for line in self._cursor_b_lines:
                    line.set_xdata([x, x])
        self._update_readout()
        self.canvas.draw_idle()

    def _near_cursor(self, event, cursor_x):
        if cursor_x is None or event.inaxes is None:
            return False
        disp_cursor, _ = event.inaxes.transData.transform((cursor_x, 0))
        return abs(event.x - disp_cursor) < DRAG_TOLERANCE_PX

    def _interp_y(self, wave, x):
        if wave.x is None or x is None:
            return None
        try:
            return float(np.interp(x, np.real(wave.x), np.real(wave.y)))
        except Exception:
            return None

    def _get_xunit(self):
        for wave, _ in self.wave_data.values():
            if wave.xunit:
                return wave.xunit
        return ""

    @staticmethod
    def _eng(value, unit=""):
        return EngFormatter(unit=unit)(value)

    def _clear_delta_annotations(self):
        for ann in self._delta_annotations:
            ann.remove()
        self._delta_annotations.clear()

    def _update_delta_annotations(self):
        self._clear_delta_annotations()
        if self.cursor_a_x is None or self.cursor_b_x is None:
            return

        xunit = self._get_xunit()
        dx = self.cursor_b_x - self.cursor_a_x
        mid_x = (self.cursor_a_x + self.cursor_b_x) / 2.0

        waves_per_axis = {}
        for tag, (wave, ax_idx) in self.wave_data.items():
            waves_per_axis.setdefault(ax_idx, []).append(wave)

        for ax_idx, ax in enumerate(self.axes):
            text_parts = ["ΔX: %s" % self._eng(dx, xunit)]
            if dx != 0 and xunit == 's':
                text_parts[0] += "  (1/ΔX: %s)" % self._eng(1.0 / abs(dx), 'Hz')

            for wave in waves_per_axis.get(ax_idx, []):
                ya = self._interp_y(wave, self.cursor_a_x)
                yb = self._interp_y(wave, self.cursor_b_x)
                if ya is not None and yb is not None:
                    text_parts.append("Δ%s: %s" % (wave.key, self._eng(yb - ya, wave.yunit)))

            theme = _get_theme()
            ann = ax.annotate(
                "\n".join(text_parts),
                xy=(mid_x, 0.97), xycoords=('data', 'axes fraction'),
                fontsize=7, fontfamily='monospace',
                color=theme['panel_fg'],
                bbox=dict(boxstyle='round,pad=0.3',
                          fc=theme['panel_bg'], ec='#666666', alpha=0.85),
                ha='center', va='top')
            self._delta_annotations.append(ann)

    def _update_readout(self):
        self.readout.config(state=NORMAL)
        self.readout.delete('1.0', END)

        if self.cursor_a_x is None and self.cursor_b_x is None:
            self._clear_delta_annotations()
            self.readout.config(state=DISABLED, height=1)
            return

        xunit = self._get_xunit()
        lines = []
        parts = []
        if self.cursor_a_x is not None:
            parts.append("A: %s" % self._eng(self.cursor_a_x, xunit))
        if self.cursor_b_x is not None:
            parts.append("B: %s" % self._eng(self.cursor_b_x, xunit))
        if self.cursor_a_x is not None and self.cursor_b_x is not None:
            dx = self.cursor_b_x - self.cursor_a_x
            parts.append("ΔX: %s" % self._eng(dx, xunit))
            if dx != 0:
                if xunit == 's':
                    parts.append("(1/ΔX: %s)" % self._eng(1.0 / abs(dx), 'Hz'))
                else:
                    parts.append("(1/ΔX: %s)" % self._eng(1.0 / abs(dx)))
        lines.append("  ".join(parts))

        for tag, (wave, _) in self.wave_data.items():
            yu = wave.yunit
            parts = ["  %-22s" % wave.key]
            ya = self._interp_y(wave, self.cursor_a_x)
            yb = self._interp_y(wave, self.cursor_b_x)
            if ya is not None:
                parts.append("A: %-14s" % self._eng(ya, yu))
            if yb is not None:
                parts.append("B: %-14s" % self._eng(yb, yu))
            if ya is not None and yb is not None:
                parts.append("Δ: %-14s" % self._eng(yb - ya, yu))
            lines.append("".join(parts))

        self._update_delta_annotations()

        self.readout.insert('1.0', "\n".join(lines))
        self.readout.config(state=DISABLED, height=min(len(lines), 8))

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_press(self, event):
        if self.toolbar.mode != '' or event.inaxes is None:
            return
        if event.xdata is None:
            return

        if self._near_cursor(event, self.cursor_a_x):
            self._dragging = 'a'
            return
        if self._near_cursor(event, self.cursor_b_x):
            self._dragging = 'b'
            return

        if event.button == 1:
            if event.key == 'shift':
                self._set_cursor('b', event.xdata)
            else:
                self._set_cursor('a', event.xdata)
        elif event.button == 3:
            self._set_cursor('b', event.xdata)

    def _on_release(self, event):
        self._dragging = None

    def _on_motion(self, event):
        if event.inaxes is not None and event.xdata is not None:
            self._last_mouse_x = event.xdata
            xu = self._get_xunit()
            self.status_var.set("x: %s   y: %.6g" % (self._eng(event.xdata, xu),
                                                       event.ydata))
        else:
            self.status_var.set("")

        if self._dragging and event.xdata is not None:
            self._set_cursor(self._dragging, event.xdata)

    def _on_key(self, event):
        if event.key == 'a' and event.xdata is not None:
            self._set_cursor('a', event.xdata)
        elif event.key == 'b' and event.xdata is not None:
            self._set_cursor('b', event.xdata)

    def placeCursorA(self):
        if self._last_mouse_x is not None:
            self._set_cursor('a', self._last_mouse_x)

    def placeCursorB(self):
        if self._last_mouse_x is not None:
            self._set_cursor('b', self._last_mouse_x)

    def _on_scroll(self, event):
        ax = event.inaxes
        if ax is None or event.xdata is None:
            return

        if event.button == 'up':
            scale = 1.0 / ZOOM_FACTOR
        elif event.button == 'down':
            scale = ZOOM_FACTOR
        else:
            return

        if event.key == 'shift':
            # Zoom y-axis
            ydata = event.ydata
            ylo, yhi = ax.get_ylim()
            new_lo = ydata - (ydata - ylo) * scale
            new_hi = ydata + (yhi - ydata) * scale
            ax.set_ylim(new_lo, new_hi)
        else:
            # Zoom x-axis (affects all shared axes)
            xdata = event.xdata
            xlo, xhi = ax.get_xlim()
            new_lo = xdata - (xdata - xlo) * scale
            new_hi = xdata + (xhi - xdata) * scale
            ax.set_xlim(new_lo, new_hi)

        self.canvas.draw_idle()


class WaveGraph(ttk.Frame):

    def __init__(self, master=None, **kw):
        super().__init__(master, width=800, borderwidth=1, relief="raised", **kw)

        self.nb = ttk.Notebook(self, width=800)
        self.nb.grid(column=0, row=0, sticky=(N, S, E, W))
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.index = 0
        self.addPlot()

    def addPlot(self):
        w = WavePlot(self.nb)
        self.nb.add(w, text="Plot %d" % self.index)
        self.index += 1

    def reloadPlots(self):
        for t in self.nb.tabs():
            self.nb.nametowidget(t).reloadAll()

    def show(self, wave):
        w = self.nb.nametowidget(self.nb.select())
        if w is not None:
            w.show(wave)

    def getCurrentPlot(self):
        tab = self.nb.select()
        if tab:
            return self.nb.nametowidget(tab)
        return None
