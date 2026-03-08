#!/usr/bin/env python3

#- Controller for waves

from tkinter import *
from tkinter import ttk
import cicsim as cs
import re
import os

#- Data Model
from .wavefiles import *

class WaveBrowser(ttk.Frame):
    """
The WaveBrowser keeps track of files loaded, and shows the waves in the files.

Click on a wave will ask the WaveGraph to show the plot
    """
    def __init__(self,simfolder,graph,xaxis,master=None,**kw):

        self.xaxis = xaxis
        super().__init__(master,width=300,borderwidth=1,relief="raised",**kw)
        self.simfolder=simfolder
        self.graph = graph

        p = ttk.PanedWindow(self,orient=VERTICAL)
        p.pack(fill="both",expand=1)


        self.tr_files= ttk.Treeview(p)
        self.tr_files.bind('<<TreeviewSelect>>', self.fileSelected)

        self.search = StringVar()
        self.search.set("")
        self.tr_search = ttk.Entry(p, textvariable=self.search)
        self.search.trace_add("write", self.updateSearch)

        self._tooltip = None
        self._tooltip_id = None
        self.tr_search.bind('<Enter>', self._show_tooltip)
        self.tr_search.bind('<Leave>', self._hide_tooltip)

        self.tr_waves= ttk.Treeview(p)
        self.tr_waves.bind('<<TreeviewSelect>>', self.waveSelected)

        p.add(self.tr_files)
        p.add(self.tr_search)
        p.add(self.tr_waves)

        self.files = WaveFiles()


    _REGEX_HELP = (
        "Regex search filter\n"
        "─────────────────────\n"
        ".        any character\n"
        ".*       match anything\n"
        "^abc     starts with abc\n"
        "abc$     ends with abc\n"
        "[abc]    a, b, or c\n"
        "[^abc]   not a, b, or c\n"
        "a|b      a or b\n"
        "\\(       literal (\n"
        "\\d       any digit\n"
        "Examples:\n"
        "  v\\(.*out   signals matching v(...out\n"
        "  ^i\\(       current signals\n"
        "  vdd|vss    vdd or vss"
    )

    def _show_tooltip(self, event):
        self._tooltip_id = self.tr_search.after(500, self._create_tooltip)

    def _hide_tooltip(self, event=None):
        if self._tooltip_id:
            self.tr_search.after_cancel(self._tooltip_id)
            self._tooltip_id = None
        if self._tooltip:
            self._tooltip.destroy()
            self._tooltip = None

    def _create_tooltip(self):
        x = self.tr_search.winfo_rootx() + 20
        y = self.tr_search.winfo_rooty() + self.tr_search.winfo_height() + 4
        self._tooltip = Toplevel(self.tr_search)
        self._tooltip.wm_overrideredirect(True)
        self._tooltip.wm_geometry("+%d+%d" % (x, y))
        label = Label(self._tooltip, text=self._REGEX_HELP,
                      justify=LEFT, font=("Courier", 10),
                      bg="#2b2b2b", fg="#e0e0e0",
                      borderwidth=1, relief="solid", padx=6, pady=4)
        label.pack()

    def updateSearch(self,*args):
        self.fillColumns()
        pass

    def fileSelected(self,event):
        fname = self.tr_files.focus()
        self.files.select(fname)
        self.fillColumns()

    def waveSelected(self,event):
        yname = self.tr_waves.focus()
        if(yname == ""):
            return
        self.graph.show(self.files.getSelected().getWave(yname))

    def fillColumns(self):
        #- Clear Treeview
        for item in self.tr_waves.get_children():
            self.tr_waves.delete(item)

        f = self.files.getSelected()
        for wn in f.getWaveNames():
            if(self.search.get() == "" or re.search(self.search.get(),wn)):
                self.tr_waves.insert('','end',wn,text=wn)

    def openFile(self,fname):
        f = self.files.open(fname,self.xaxis)
        self.tr_files.insert('','end',f.fname,text=f.name)
        self.fillColumns()
