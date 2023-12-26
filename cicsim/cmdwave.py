#!/usr/bin/env python3

import cicsim as cs
import tkinter
import os

from .wavebrowser import *
from .wavegraph import *

from matplotlib.backend_bases import key_press_handler
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,
                                               NavigationToolbar2Tk)
from matplotlib.figure import Figure

class CmdWave(cs.Command):
    def __init__(self):
        super().__init__()

        root = tkinter.Tk()
        root.wm_title(f"cIcWave: {os.getcwd()}")

        root.option_add('*tearOff', FALSE)

        #- Setup Menu
        #win = Toplevel(root)
        menubar = Menu(root)
        root['menu'] = menubar
        menu_file = Menu(menubar)
        menu_edit = Menu(menubar)
        menubar.add_cascade(menu=menu_file,label="File")
        menubar.add_cascade(menu=menu_edit,label="Edit")

        menu_file.add_command(label="Open",command=self.openFileDialog)

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

    def openFile(self,fname):
        self.browser.openFile(fname)

    def run(self):

        tkinter.mainloop()



    def openFileDialog(self):

        filename = tkinter.filedialog.askopenfilename(initialdir=os.getcwd())

        self.browser.openFile(filename)

        pass
