#!/usr/bin/env python3

#- Viewer for waves

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

        self.combo = ttk.Combobox(frm)
        self.combo.grid(column=0,row=0,columnspan=2,sticky=(N,E,W))
        self.combo.state(["readonly"])
        self.combo.bind('<<ComboboxSelected>>', self.setAxesIndex)

        self.tree = ttk.Treeview(frm)
        self.tree.grid(column=0,row=1,columnspan=2,sticky=(N,S,E,W))

        breloadAll = ttk.Button(frm,text="Reload",command=self.reloadAll)
        breloadAll.grid(column=0,row=3,sticky=(S,E,W))

        bdelete = ttk.Button(frm,text="Remove",command=self.removeLine)
        bdelete.grid(column=0,row=2,sticky=(S,E,W))

        bdeleteAll = ttk.Button(frm,text="Remove All",command=self.removeAll)
        bdeleteAll.grid(column=1,row=2,sticky=(S,E,W))

        baddaxis = ttk.Button(frm,text="Add Axis",command=self.addAxis)
        baddaxis.grid(column=0,row=4,sticky=(S,E,W))

        bautosize = ttk.Button(frm,text="Auto size",command=self.autoSize)
        bautosize.grid(column=1,row=4,sticky=(S,E,W))

        frm.columnconfigure(0,weight=1)
        frm.rowconfigure(1,weight=1)

        self.fig = Figure(dpi=90)
        self.gridspec = self.fig.add_gridspec(1, 1)

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
        self.axes = list()
        self.index = 0
        self.addAxis()
        pass

    def show(self,wave):

        if(wave.tag in self.waves):
            return

        #- Let the wave figure out how to plot on the axis
        wave.plot(self.axes[self.index])

        if(self.index == 0):
            self.axes[self.index].set_xlabel(wave.xlabel)

        #- Set Meta info on the wave
        self.waves[wave.tag] = wave


        text = "A%d: " %self.index + wave.ylabel

        self.tree.insert('','end',wave.tag,text=text ,tags=(wave.tag,))
        self.tree.tag_configure(wave.tag,foreground=wave.line.get_color())
        self.canvas.draw()

    def removeAll(self):
        """Go through all waves in treeview and remove them"""
        ll = self.tree.get_children()
        for tag in ll:
            self.removeTag(tag)

        self.canvas.draw()
        pass

    def setAxesIndex(self,event):
        self.index = self.combo.current()

    def addAxis(self):
        if(len(self.axes) == 0):
            ax  = self.fig.add_subplot()
        else:
            ax  = self.fig.add_subplot(sharex=self.axes[0])
            ax.xaxis.set_tick_params(labelbottom=False)

        ax.grid()
        ax.autoscale()
        self.axes.append(ax)
        N = len(self.axes)
        self.index = N-1

        saxes = list()
        for i in range(0,N):
            saxes.append("Axes %d" %i)

        self.combo['values'] = saxes
        self.combo.current(self.index)

        axes = self.fig.get_axes()

        #- Find boundingrect
        for a in axes:
            pos = a.get_position()

        width = 0.85
        height = 0.85

        x = 0.1
        htext = 0
        y  = 0.1 + htext
        axh = height/N
        for a in axes:
            pos = [x,y,width,axh - htext]
            #print(pos)
            y += axh + htext
            a.set_position(pos)

        self.canvas.draw()
        pass

    def autoSize(self):
        for ax in self.axes:
            if(ax):
                ax.relim()
                ax.autoscale_view(True,True,True)
        self.canvas.draw()

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

    def show(self,wave):
        w = self.nb.nametowidget(self.nb.select())
        if(w is not None):
            w.show(wave)
