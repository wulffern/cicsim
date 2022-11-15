######################################################################
##        Copyright (c) 2020 Carsten Wulff Software, Norway
## ###################################################################
## Created       : wulff at 2020-10-24
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

import os
import re


class colors:
    '''Colors class:
    reset all colors with colors.reset
    
    '''
    reset='\033[0m'
    bold='\033[01m'
    disable='\033[02m'
    fg = {
        "red" : '\033[31m',
        "green" : '\033[32m',
        "blue" : '\033[34m',
        "cyan" :'\033[36m',
        "yellow" :'\033[93m',
        "default": '',
    }

class Command:

    def __init__(self):
        self.indentstr = "|-"
        self.indent = 0

    def getColor(self,color):
        if(color in colors.fg):
            return colors.fg[color]
        else:
            return colors.fg["default"]

    def getIndent(self,nextindent=None):

        if(nextindent is None):
            nextindent = self.indent
        
        if(nextindent == 0):
            return ""
        else:
            return self.indentstr + self.getIndent(nextindent-1)

    def comment(self,ss,color="green"):
        print(self.getIndent() + self.getColor(color) + ss  + colors.reset)

    def warning(self,ss):
        self.comment(ss,"yellow")

    def error(self,ss):
        ss_h = "Error: "
        self.comment(ss_h + ss,"red")

    def doCmd(self,cmd):
        os.system(cmd)

    def sub(self,buffer,keyval):
        """Replace ${NAME} constructs in buffer with values from 'dict' or shell environment"""
        for (k,v) in keyval.items():
            buffer = re.sub('\${%s}'%k,v,buffer)
        m = re.search('\${([^}]+)}',buffer)
        if(m):
            for var in m.groups():
                val = os.getenv(var)
                if(val):
                    buffer = re.sub('\${%s}' %var,val,buffer)
        return buffer
