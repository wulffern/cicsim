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
        breloadAll = ttk.Button(frm,text="Reload",command=self.reloadAll)
        bdelete = ttk.Button(frm,text="Remove",command=self.removeLine)
        bdeleteAll = ttk.Button(frm,text="Remove All",command=self.removeAll)
        bautosize = ttk.Button(frm,text="Auto size",command=self.autoSize)
        self.tree.grid(column=0,row=0,columnspan=2,sticky=(N,S,E,W))
        bdelete.grid(column=0,row=1,sticky=(S,E,W))
        bdeleteAll.grid(column=1,row=1,sticky=(S,E,W))
        breloadAll.grid(column=0,row=2,sticky=(S,E,W))
        bautosize.grid(column=1,row=2,sticky=(S,E,W))
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

        self.waves = dict()
        pass

    def show(self,wfile,ylabel):

        wave = wfile.getWave(ylabel)

        if(wave.tag in self.waves):
            return

        if(wave.x is not None):
            if(not wave.logx and not wave.logy):
                wave.line, = self.ax.plot(wave.x,wave.y,label=wave.ylabel)
            elif(wave.logx and not wave.logy):
                wave.line, = self.ax.semilogx(wave.x,wave.y,label=wave.ylabel)
            elif(not wave.logx and wave.logy):
                wave.line, = self.ax.semilogy(wave.x,wave.y,label=wave.ylabel)
            elif(wave.logx and wave.logy):
                wave.line, = self.ax.loglog(wave.x,wave.y,label=wave.ylabel)
        else:
            wave.line, = self.ax.plot(wave.y,label=wave.ylabel)

        self.waves[wave.tag] = wave

        self.tree.insert('','end',wave.tag,text=ylabel,tags=(wave.tag,))
        self.tree.tag_configure(wave.tag,foreground=wave.line.get_color())
        self.ax.set_xlabel(wave.xlabel)
        self.canvas.draw()

    def removeAll(self):
        ll = self.tree.get_children()
        for tag in ll:
            self.removeTag(tag)

        self.canvas.draw()
        pass


    def autoSize(self):
        if(self.ax):
            self.ax.relim()
            self.ax.autoscale_view(True,True,True)
            self.canvas.draw()
        pass

    def reloadAll(self):
        ll = self.tree.get_children()
        for tag in ll:
            wave = self.waves[tag]
            wave.reload()
        self.autoSize()

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
        if(tag in self.waves):
            self.waves[tag].deleteLine()
            del self.waves[tag]




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

    def reloadPlots(self):
        tabs = self.nb.tabs()
        for t in tabs:
            w = self.nb.nametowidget(t)
            w.reloadAll()

    def show(self,wfile,ylabel):
        w = self.nb.nametowidget(self.nb.select())
        if(w is not None):
            w.show(wfile,ylabel)


        #if(x is not None):
        #    self.ax.plot(x,y,label=ylabel)
        #else:
        #    self.ax.plot(y,label=ylabel)

        #self.canvas.draw()
