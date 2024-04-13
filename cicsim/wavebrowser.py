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
    def __init__(self,simfolder,graph,master=None,**kw):

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

        self.tr_waves= ttk.Treeview(p)
        self.tr_waves.bind('<<TreeviewSelect>>', self.waveSelected)

        p.add(self.tr_files)
        p.add(self.tr_search)
        p.add(self.tr_waves)

        self.files = WaveFiles()


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
        f = self.files.open(fname)
        self.tr_files.insert('','end',f.fname,text=f.name)
        self.fillColumns()
