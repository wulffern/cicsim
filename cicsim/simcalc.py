######################################################################
##        Copyright (c) 2020 Carsten Wulff Software, Norway
## ###################################################################
## Created       : wulff at 2020-10-25
## ###################################################################
##  The MIT License (MIT)
##
##  Permission is hereby granted, free of charge, to any person obtaining a copy
##  of this software and associated documentation files (the "Software"), to deal
##  in the Software without restriction, including without limitation the rights
##  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
##  copies of the Software, and to permit persons to whom the Software is
##  furnished to do so, subject to the following conditions:
##
##  The above copyright notice and this permission notice shall be included in all
##  copies or substantial portions of the Software.
##
##  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
##  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
##  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
##  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
##  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
##  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
##  SOFTWARE.
##
######################################################################
import pandas as pd
import yaml
import sys
import os
import numpy as np

class SimCalc():
    def __init__(self):
        pass

    def fft(self,ser):
        N = len(ser)
        pwr2 = np.floor(np.log2(N))
        M = int(2**pwr2)
        x = ser[int(N - M):]
        x = x - x.mean()

        #h = np.hanning(M)
        y = np.fft.fft(x)
        y = y[:int(M/2)]*2

        #- Normalize amplitude
        y = y/(M/2)
        ydB = 20*np.log10(np.abs(y))

        sig = np.max(ydB)
        fbin = np.argmax(ydB)

        sigbins = [ 0] +fbin


        noisebins = np.arange(0,int(M/2)-1,1)
        noisebins[sigbins] = 0
        noisebins[0:2] = 0

        s = np.linalg.norm(y[sigbins],2)

        n = np.linalg.norm(y[noisebins],2)

        data = {}
        data["sndr"] = 20*np.log10(s/n)
        data["amp"] = max(ydB)
        data["sfdr"] = max(ydB) - np.max(ydB[noisebins])
        data["enob"] = (data["sndr"]-1.76)/6.02

        return (data,ydB)

    def fftWithHanning(self,ser):
        N = len(ser)
        pwr2 = np.floor(np.log2(N))
        M = int(2**pwr2)
        x = ser[int(N - M):]
        x = x - x.mean()

        h = np.hanning(M)
        y = np.fft.fft(np.multiply(h,x))
        y = y[:int(M/2)]*2

        sigpow = 1.2
        
        #- Normalize amplitude
        y = y/(M/2)
        ydB = 20*np.log10(np.abs(y))
        
        sig = np.max(y)
        fbin = np.argmax(y)

        if(fbin < 3):
            fbin = 3


        sigbins = [-3,-2,-1,0,1,2,3] + fbin

        noisebins = np.arange(0,int(M/2)-1,1)
        noisebins[sigbins] = 0
        noisebins[0:2] = 0

        s = np.linalg.norm(y[sigbins],2)

        n = np.linalg.norm(y[noisebins],2)

        data = {}
        data["sndr"] = 20*np.log10(s/n)
        data["amp"] = max(ydB)
        data["sfdr"] = max(ydB) - np.max(ydB[noisebins])
        data["enob"] = (data["sndr"]-1.76)/6.02


        return (data,ydB)
        

def SimCalcYaml(function):
    def wrapper(fname):
        df = pd.DataFrame()
        
        fnyaml = fname + ".yaml"
        if(os.path.exists(fnyaml)):
            obj = {}
            with open(fnyaml,"r") as fi:
                obj = yaml.safe_load(fi)
            df = pd.DataFrame([obj])
        function(fname,df)
    return wrapper
