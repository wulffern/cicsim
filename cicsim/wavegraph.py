#!/usr/bin/env python3
#
from tkinter import *
from tkinter import ttk
import tkinter
from matplotlib.backend_bases import key_press_handler
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,
                                               NavigationToolbar2Tk)
from matplotlib.figure import Figure


class WavePlot(ttk.PanedWindow):
    def __init__(self,master,**kw):
        #self.current = ttk.Frame(self.nb)
        #self.nb.add(self.current,text="Plot")
        super().__init__(master,orient=HORIZONTAL,**kw)

        frm = ttk.Frame(self)
        self.add(frm)
        self.tree = ttk.Treeview(frm)
        bdelete = ttk.Button(frm,text="Remove",command=self.removeLine)
        bdeleteAll = ttk.Button(frm,text="Remove All",command=self.removeAll)
        self.tree.grid(column=0,row=0,columnspan=2,sticky=(N,S,E,W))
        bdelete.grid(column=0,row=1,sticky=(S,E,W))
        bdeleteAll.grid(column=1,row=1,sticky=(S,E,W))
        frm.columnconfigure(0,weight=1)
        frm.rowconfigure(0,weight=1)

        self.fig = Figure(dpi=100)
        self.ax  = self.fig.add_subplot()
        self.ax.grid()
        self.ax.autoscale()
        frame = ttk.Frame(self)
        self.add(frame)
        self.canvas = FigureCanvasTkAgg(self.fig, master=frame)# A tk.DrawingArea.
        toolbar = NavigationToolbar2Tk(self.canvas, frame, pack_toolbar=True)
        toolbar.update()

        self.canvas.mpl_connect(
            "key_press_event", lambda event: print(f"you pressed {event.key}"))
        self.canvas.mpl_connect("key_press_event", key_press_handler)
        toolbar.pack(side=tkinter.BOTTOM, fill=tkinter.X)
        self.canvas.get_tk_widget().pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=True)

        self.lines = dict()
        pass

    def show(self,wfile,ylabel):

        tag = wfile.getTag(ylabel)

        print(tag)

        if(tag in self.lines):
            return

        (x,xlabel) = wfile.getX()
        y = wfile.getY(ylabel)


        line, = self.ax.plot(x,y,label=ylabel)

        self.lines[tag] = line

        self.tree.insert('','end',tag,text=ylabel,tags=(tag,))
        self.tree.tag_configure(tag,foreground=line.get_color())
        self.canvas.draw()

    def removeAll(self):
        ll = self.tree.get_children()
        for tag in ll:
            self.removeTag(tag)

        self.canvas.draw()
        pass



    def removeLine(self):
        tag = self.tree.focus()
        self.removeTag(tag)
        self.canvas.draw()
        pass

    def removeTag(self,tag):
        if(tag == ""):
            return
        if(not self.tree.exists(tag)):
            return
        self.tree.delete(tag)
        if(tag in self.lines):
            self.lines[tag].remove()
            del self.lines[tag]


class WaveGraph(ttk.Frame):

    def __init__(self,master=None,**kw):
        super().__init__(master,width=800,borderwidth=1,relief="raised", **kw)

        self.nb = ttk.Notebook(self,width=800)
        self.nb.grid(column=0,row=0,sticky=(N,S,E,W))
        self.columnconfigure(0,weight=1)
        self.rowconfigure(0,weight=1)

        self.index = 0
        self.current = None

        self.addPlot()

    def addPlot(self):
        w = WavePlot(self.nb)
        self.nb.add(w,text=f"Plot {self.index}")
        self.index +=1


    def show(self,wfile,ylabel):
        w = self.nb.nametowidget(self.nb.select())
        if(w is not None):
            w.show(wfile,ylabel)


        #if(x is not None):
        #    self.ax.plot(x,y,label=ylabel)
        #else:
        #    self.ax.plot(y,label=ylabel)

        #self.canvas.draw()
