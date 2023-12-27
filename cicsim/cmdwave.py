#!/usr/bin/env python3

import cicsim as cs
import tkinter
import os

from .wavebrowser import *
from .wavegraph import *


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
    def __init__(self):
        super().__init__()

        root = tkinter.Tk()
        root.wm_title(f"cIcWave: {os.getcwd()}")

        root.option_add('*tearOff', FALSE)

        #- Setup Menu
        menubar = Menu(root)
        root['menu'] = menubar
        menu_file = Menu(menubar)
        menu_edit = Menu(menubar)
        menubar.add_cascade(menu=menu_file,label="File")
        menubar.add_cascade(menu=menu_edit,label="Edit")
        menu_file.add_command(label="New Plot",command=self.newPlot)
        menu_file.add_command(label="Reload Plots",command=self.reloadPlots)
        menu_file.add_command(label="Open Raw",command=self.openFileDialog)

        #- Setup top interface
        content = ttk.PanedWindow(root,orient=HORIZONTAL)
        height = 500
        self.graph = WaveGraph(content,height=height)
        self.browser = WaveBrowser(content,self.graph,height=height)
        content.grid(column=0,row=0,sticky=(N,S,E,W))
        content.add(self.browser)
        content.add(self.graph)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

        pass

    def newPlot(self):
        self.graph.addPlot()

    def reloadPlots(self):
        self.graph.reloadPlots()

    def openFile(self,fname):
        self.browser.openFile(fname)

    def run(self):
        tkinter.mainloop()

    def openFileDialog(self):
        filename = tkinter.filedialog.askopenfilename(initialdir=os.getcwd())
        self.browser.openFile(filename)
        pass
