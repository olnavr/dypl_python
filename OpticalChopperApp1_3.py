#!/usr/bin/env python
import wx
import numpy as np
import matplotlib.figure as mfigure
import matplotlib.animation as manim
from matplotlib.lines import Line2D
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
import serial
from time import sleep
from serial.tools import list_ports
import threading
import math

"""Tested on Python3"""

class Container():
    """
    Class containes important program data: given value of motoa speed,
    actual value of motor speed, available COM ports 
    """
    def __init__(self):
        """The constructor."""
        self.given = 0.1
        self.actual = 0.1
        self.e = '0'
        self.p = '0'
        self.coms =[]
    def setGiven(self,g):
        self.given = g
    def updateActual(self, a):
        self.actual = a
    def updateComs(self, c):
        self.coms = c

class Scope(object):
    """
    Class resposible for updating plot in real time, also containes data 
    about plot limits and values to be drawn.
    """
    def __init__(self, ax, maxt=2, dt=0.08):
        """The constructor."""
        self.ax = ax
        self.dt = dt
        self.maxt = maxt
        self.tdata = [0]
        
        self.ct = Container()
        
        self.ydata_g = [0]
        self.ydata_c = [0]
        self.ylim = 3
        self.ylim_min = -1
        self.line_g = Line2D(self.tdata, self.ydata_g, color='blue')
        self.line_c = Line2D(self.tdata, self.ydata_c, color='red')
        self.ax.add_line(self.line_g)
        self.ax.add_line(self.line_c)
        
        self.ax.set_ylim(-.1, self.ylim)
        self.ax.set_xlim(0, self.maxt)

    def update(self, y):
        """Function updates data on the plot."""
        lastt = self.tdata[-1]
        if lastt > self.tdata[0] + self.maxt:  
            self.tdata = [self.tdata[-1]]
            self.ydata_g = [self.ydata_g[-1]]
            self.ydata_c = [self.ydata_c[-1]]
            self.ax.set_xlim(self.tdata[0], self.tdata[0] + self.maxt)
            self.ax.figure.canvas.draw()
        self.autoScale() 
        t = self.tdata[-1] + self.dt
        self.tdata.append(t)
        self.ydata_g.append(self.ct.given)
        self.ydata_c.append(self.ct.actual)
        self.line_g.set_data(self.tdata, self.ydata_g)
        self.line_c.set_data(self.tdata, self.ydata_c)
        return self.line_g,self.line_c
        
    def autoScale(self):
        """Function sets new limits of plot."""
        max_y = max(self.ct.given,self.ct.actual)
        min_y = min(self.ct.given,self.ct.actual)
        if max_y > self.ylim or self.ylim > 1.04*max_y:
            self.ylim = math.ceil(1.02*max_y)     
        elif min_y < self.ylim_min or self.ylim_min < 0.96*min_y:
            self.ylim_min =  math.ceil(0.98*min_y)
        if self.ylim == self.ylim_min:
            self.ylim =  math.ceil(1.02*self.ylim)
        self.ax.set_ylim((self.ylim_min, self.ylim))

class MyFrame(wx.Frame):
    """
    Main frame of the program  
    """
    def __init__(self):
        """ The constructor."""
        super(MyFrame,self).__init__(None, wx.ID_ANY, size=(720, 460),title = 'Optical Chopper')
        self.panel=wx.Panel(self)
        self.ser = serial.Serial() 
        self.createFigure()
        self.createButtons()
        self.createSizers()
        self.createStatusBar()
        self.stop_reading_thread = True
        """ Makes an animation by repeatedly calling a function update every 80 ms""" 
        self.animator = manim.FuncAnimation(self.fig,self.update, interval=80)
        
    def  createFigure(self):
        """ Function creates and adds matplotlib figure to frame"""
        self.fig = mfigure.Figure(figsize=(6.2,3.6))
        self.ax = self.fig.add_subplot(111)
        self.sc = Scope(self.ax)
        self.canv = FigureCanvasWxAgg(self.panel, wx.ID_ANY, self.fig)
          
    def  createButtons(self):
        """ Function creates buttons and binds event handlers to them"""
        self.start_fl = False
        self.clockRot_fl = True
        self.bw_st=wx.Button(self.panel,-1,"Start")
        self.bw_st.Bind(wx.EVT_BUTTON, self.OnStart)
        
        self.bw_s=wx.Button(self.panel,-1,"Scan")
        self.bw_s.Bind(wx.EVT_BUTTON, self.OnScan)
        
        self.bw_c=wx.Button(self.panel,-1,"Connect")
        self.bw_c.Bind(wx.EVT_BUTTON, self.OnConnect)
        
        self.ch_com = wx.Choice(self.panel,choices=self.sc.ct.coms,size = (87,-1))
        self.setGiven = wx.TextCtrl(self.panel,size = (530,26))
        
        self.bw_sg=wx.Button(self.panel,-1,"Set")
        self.bw_sg.Bind(wx.EVT_BUTTON, self.OnSet)
        
    def createSizers(self):
        """ Function creates sizers and adds buttons to them"""
        self.mvsizer = wx.BoxSizer(wx.VERTICAL)  
        self.mhsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.hs1 = wx.BoxSizer(wx.HORIZONTAL)
        self.vs1 = wx.BoxSizer(wx.VERTICAL)
        self.hs1l = wx.BoxSizer(wx.HORIZONTAL)
        
        self.vs1.Add(self.ch_com,wx.EXPAND)
        self.vs1.Add(self.bw_s,wx.EXPAND)
        self.vs1.Add(self.bw_c,wx.EXPAND)
        self.vs1.Add(self.bw_st,wx.EXPAND)
        
        self.hs1l.Add((88,26))
        self.hs1l.Add(self.setGiven)
        self.hs1l.Add(self.bw_sg)
        
        self.mhsizer.Add(self.vs1)
        line = wx.StaticLine(self.panel, wx.ID_ANY, size=(1,360), style=wx.LI_VERTICAL)
        self.mhsizer.Add(line)
        self.mhsizer.Add(self.canv)
        
        self.mvsizer.Add(self.mhsizer)
        self.mvsizer.Add(self.hs1l)
        
        self.panel.SetSizer(self.mvsizer)
        self.mvsizer.Fit(self.panel)
        
    def createStatusBar(self):
        """ Function creates StatusBar with 3 fields"""
        self.statusbar = self.CreateStatusBar(3)
        self.statusbar.SetStatusText("Disconnected",2)
        
    def update(self,a):
        """ Function updates statusbar data and plot"""
        msg1 = "Given: " + str(self.sc.ct.given)
        msg2 = "Active: " + str(self.sc.ct.actual)
        self.statusbar.SetStatusText(msg1)
        self.statusbar.SetStatusText(msg2,1)
        return self.sc.update(a)
        
    def readCOM(self):
        """ Function reads data from cpend COM port, is opend in separate thread"""
        while self.stop_reading_thread == False :
            x = self.ser.readline().decode()
            if x.find(',') != -1:
                a,x = x.split(',')
                self.sc.ct.actual = math.ceil(60_000_000/float(a))
                
    def stop(self):
        """Function sends request to device to stop motor"""
        stop = 'p'
        self.start_fl = False
        self.bw_st.SetLabel("Start")
        self.ser.write(stop.encode('UTF-8'))
        
    def start(self):
        """Function sends request to device to start motor"""    
        start = 's'
        self.start_fl = True
        self.bw_st.SetLabel("Stop")
        self.ser.write(start.encode('UTF-8'))
        
    def OnStart(self,e):
        """Handler of Start/Stop button"""
        if self.ser.is_open == True:
            if self.start_fl == False:
                self.start()
            else:
                self.stop()
        
    def OnScan(self,e):
        """Handler of Scan button, updates list of available COM ports"""
        ser = serial.tools.list_ports.comports(include_links=False)
        self.sc.ct.coms = []
        for s in ser:
            st = str(s).split()[0]
            self.sc.ct.coms.append(st)
        self.ch_com.SetItems(self.sc.ct.coms)
            
    def OnConnect(self,e):
        """Handler of Connect button, sets connection with device"""
        inx = self.ch_com.GetSelection()
        if inx ==  wx.NOT_FOUND:
            self.statusbar.SetStatusText("Index not found",1)
        if self.ser.is_open == True:
            self.stop_reading_thread = True
            self.stop();
            self.ser.close()
            self.bw_c.SetLabel('Connect')
            self.statusbar.SetStatusText("Disconnected",2)
        else:
            com = self.sc.ct.coms[inx]
            self.ser = serial.Serial(com, 256000, timeout=2000,
            parity=serial.PARITY_NONE, rtscts=1)
            self.statusbar.SetStatusText("Connected",2)
            self.bw_c.SetLabel('Disconnect')
            self.stop_reading_thread = False
            t = threading.Thread(target=self.readCOM)
            t.start()
            t.deamon = True
        
    def OnSet(self,e):
        """Handler of Set button, sets new value of motor speed and 
        sends it to device"""
        minutes = 60_000_000
        step = 18
        if self.ser.is_open == True:
            self.sc.ct.given = float(self.setGiven.GetValue())
            step_time = 0.998*minutes/self.sc.ct.given/step
            self.ser.write(('u'+str(step_time)).encode('UTF-8'))

def main(argv):            
    wxa = wx.App()
    w = MyFrame()
    w.Show(True)
    wxa.MainLoop()
    return 0
    
if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))
