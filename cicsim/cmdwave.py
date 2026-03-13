#!/usr/bin/env python3

import cicsim as cs
import tkinter
from tkinter import *
from tkinter import ttk
import os

from .wavebrowser import *
from .wavegraph import *
from .cmdwave_pg import _get_theme


#- I try to follow a Model, View, Controller type of design pattern
#
# Controller: WaveBrowser
# View: WaveGraph
# Model: WaveFiles
#
# In principle, I want as little as possible to be known across the MVC boundaries
# The Model should not need to know how the data is presented, and the View should
# not need to know how the model reloads data.


class CmdWave(cs.Command):
    def __init__(self, xaxis):
        super().__init__()

        self.root = tkinter.Tk()
        self.root.wm_title(f"cIcWave: {os.getcwd()}")
        self.root.option_add('*tearOff', FALSE)
        self.root.geometry("1200x700")

        # --- Menu bar ---
        menubar = Menu(self.root)
        self.root['menu'] = menubar

        menu_file = Menu(menubar)
        menu_edit = Menu(menubar)
        menu_view = Menu(menubar)
        menubar.add_cascade(menu=menu_file, label="File")
        menubar.add_cascade(menu=menu_edit, label="Edit")
        menubar.add_cascade(menu=menu_view, label="View")

        self._line_width = 2
        self._font_size = 9

        menu_file.add_command(label="Open Raw          Ctrl+O",
                              command=self.openFileDialog)
        menu_file.add_command(label="Export PDF        Ctrl+P",
                              command=self._exportPdf)
        menu_file.add_separator()
        menu_file.add_command(label="Quit              Ctrl+Q",
                              command=self.root.destroy)

        menu_edit.add_command(label="New Plot          Ctrl+N",
                              command=self.newPlot)
        menu_edit.add_command(label="Add Axis          Ctrl+A",
                              command=self._addAxis)
        menu_edit.add_separator()
        menu_edit.add_command(label="Reload All        R",
                              command=self.reloadPlots)
        menu_edit.add_command(label="Auto Scale        F",
                              command=self._autoSize)
        menu_edit.add_command(label="Zoom In           Shift+Z",
                              command=self._zoomIn)
        menu_edit.add_command(label="Zoom Out          Ctrl+Z",
                              command=self._zoomOut)
        menu_edit.add_separator()
        menu_edit.add_command(label="Remove Selected   Delete",
                              command=self._removeLine)
        menu_edit.add_command(label="Remove All",
                              command=self._removeAll)

        menu_view.add_command(label="Set Cursor A      A",
                              command=self._setCursorA)
        menu_view.add_command(label="Set Cursor B      B",
                              command=self._setCursorB)
        menu_view.add_command(label="Clear Cursors     Escape",
                              command=self._clearCursors)
        menu_view.add_separator()
        menu_view.add_command(label="Toggle Legend      L",
                              command=self._toggleLegend)
        menu_view.add_separator()
        menu_view.add_command(label="Increase Line Width   Ctrl+Up",
                              command=self._incLineWidth)
        menu_view.add_command(label="Decrease Line Width   Ctrl+Down",
                              command=self._decLineWidth)
        menu_view.add_separator()
        menu_view.add_command(label="Increase Font Size    Ctrl+=",
                              command=self._incFontSize)
        menu_view.add_command(label="Decrease Font Size    Ctrl+-",
                              command=self._decFontSize)

        menu_help = Menu(menubar)
        menubar.add_cascade(menu=menu_help, label="Help")
        menu_help.add_command(label="Keyboard Shortcuts",
                              command=self._showHotkeyHelp)

        # --- Main layout ---
        content = ttk.PanedWindow(self.root, orient=HORIZONTAL)
        height = 600
        self.graph = WaveGraph(content, height=height)
        self.browser = WaveBrowser(content, self.graph, xaxis, height=height)
        content.grid(column=0, row=0, sticky=(N, S, E, W))
        content.add(self.browser)
        content.add(self.graph)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # --- Keyboard shortcuts ---
        self.root.bind('<Control-o>', lambda e: self.openFileDialog())
        self.root.bind('<Control-n>', lambda e: self.newPlot())
        self.root.bind('<Control-q>', lambda e: self.root.destroy())
        self.root.bind('<Control-a>', lambda e: self._addAxis())
        self.root.bind('<Control-p>', lambda e: self._exportPdf())
        self.root.bind('<Delete>', lambda e: self._removeLine())
        self.root.bind('<Escape>', lambda e: self._clearCursors())

        self.root.bind('<Control-z>', lambda e: self._zoomOut())
        self.root.bind('<Control-Up>', lambda e: self._incLineWidth())
        self.root.bind('<Control-Down>', lambda e: self._decLineWidth())
        self.root.bind('<Control-equal>', lambda e: self._incFontSize())
        self.root.bind('<Control-minus>', lambda e: self._decFontSize())

        # Single-key shortcuts — skip when focus is in an Entry widget
        for key, func in [('r', self.reloadPlots),
                          ('f', self._autoSize),
                          ('a', self._setCursorA),
                          ('b', self._setCursorB),
                          ('l', self._toggleLegend),
                          ('Z', self._zoomIn)]:
            self.root.bind(key, self._make_key_handler(func))

    def _make_key_handler(self, func):
        def handler(event):
            if isinstance(event.widget, (ttk.Entry, Entry)):
                return
            func()
        return handler

    # --- Delegate to current plot tab ---

    def _addAxis(self):
        p = self.graph.getCurrentPlot()
        if p:
            p.addAxis()

    def _autoSize(self):
        p = self.graph.getCurrentPlot()
        if p:
            p.autoSize()

    def _zoomIn(self):
        p = self.graph.getCurrentPlot()
        if p:
            p.zoomIn()

    def _zoomOut(self):
        p = self.graph.getCurrentPlot()
        if p:
            p.zoomOut()

    def _incLineWidth(self):
        self._line_width = min(self._line_width + 1, 10)
        self._applyLineWidth()

    def _decLineWidth(self):
        self._line_width = max(self._line_width - 1, 1)
        self._applyLineWidth()

    def _applyLineWidth(self):
        for t in self.graph.nb.tabs():
            self.graph.nb.nametowidget(t).setLineWidth(self._line_width)

    def _incFontSize(self):
        self._font_size = min(self._font_size + 1, 24)
        self._applyFontSize()

    def _decFontSize(self):
        self._font_size = max(self._font_size - 1, 6)
        self._applyFontSize()

    def _applyFontSize(self):
        for t in self.graph.nb.tabs():
            self.graph.nb.nametowidget(t).setFontSize(self._font_size)

    def _removeLine(self):
        p = self.graph.getCurrentPlot()
        if p:
            p.removeLine()

    def _removeAll(self):
        p = self.graph.getCurrentPlot()
        if p:
            p.removeAll()

    def _setCursorA(self):
        p = self.graph.getCurrentPlot()
        if p:
            p.placeCursorA()

    def _setCursorB(self):
        p = self.graph.getCurrentPlot()
        if p:
            p.placeCursorB()

    def _clearCursors(self):
        p = self.graph.getCurrentPlot()
        if p:
            p.clearCursors()

    def _toggleLegend(self):
        p = self.graph.getCurrentPlot()
        if p:
            p.toggleLegend()

    def _exportPdf(self):
        p = self.graph.getCurrentPlot()
        if p:
            p.exportPdf()

    def _showHotkeyHelp(self):
        text = (
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
            "  Ctrl+A        Add axis\n"
            "  R             Reload all waves\n"
            "  F             Auto scale (fit)\n"
            "  Shift+Z       Zoom in\n"
            "  Ctrl+Z        Zoom out\n"
            "  Delete        Remove selected wave\n"
            "\n"
            "Cursors\n"
            "  A             Set cursor A at mouse\n"
            "  B             Set cursor B at mouse\n"
            "  Escape        Clear cursors\n"
            "  Click         Place cursor A\n"
            "  Shift+Click   Place cursor B\n"
            "  Right-Click   Place cursor B\n"
            "  Drag cursor   Move cursor\n"
            "\n"
            "View\n"
            "  L             Toggle legend\n"
            "  Ctrl+Up       Increase line width\n"
            "  Ctrl+Down     Decrease line width\n"
            "  Ctrl+=        Increase font size\n"
            "  Ctrl+-        Decrease font size\n"
            "\n"
            "Zoom\n"
            "  Scroll        Zoom x-axis\n"
            "  Shift+Scroll  Zoom y-axis\n"
        )
        win = Toplevel(self.root)
        win.title("Keyboard Shortcuts")
        win.resizable(False, False)
        theme = _get_theme()
        label = Label(win, text=text, justify=LEFT,
                      font=("Courier", 11),
                      bg=theme['panel_bg'], fg=theme['panel_fg'],
                      padx=16, pady=12)
        label.pack(fill=BOTH, expand=True)
        btn = ttk.Button(win, text="Close", command=win.destroy)
        btn.pack(pady=(0, 10))
        win.transient(self.root)
        win.grab_set()

    # --- Menu actions ---

    def newPlot(self):
        self.graph.addPlot()

    def reloadPlots(self):
        self.graph.reloadPlots()

    def openFile(self, fname, sheet_name=None):
        self.browser.openFile(fname)

    def openDataFrame(self, df, name, **kwargs):
        self.browser.openDataFrame(df, name)

    def run(self):
        tkinter.mainloop()

    def openFileDialog(self):
        filename = tkinter.filedialog.askopenfilename(initialdir=os.getcwd())
        if filename:
            self.browser.openFile(filename)
