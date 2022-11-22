######################################################################
##        Copyright (c) 2020 Carsten Wulff Software, Norway
## ###################################################################
## Created       : wulff at 2020-12-11
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


import cicsim as cs
import re
import os
import errno
import yaml
import shutil as sh

class CmdIp(cs.Command):
    """Make IP from a TEMPLATE YAML file
    
    It will first create the IP directory, then read the yaml to figure out what to do.

    Example yaml:

       # Make directories, expect array\n
       dirs: \n
         - dir1 \n
         - dir2 \n
       # Copy files, only used if --src IP is specified \n
       copy: \n
         - file1 \n
         - file2 \n
       # Create files
       create: \n
         filename: text content \n
       # Run commands in the folder after creating \n
       do:    \n
        - git init\n

    Variables:

      Before the file is read as YAML it will replace ${NAME} type variables in the following order.\n
       - ${IP} = IP \n
       - ${CELL} = re.sub("_[^\_]+$","",IP) \n
       - Environment variables, i.e ${USER} \n

    """
    

    def __init__(self,ip,template,src=None,cell=None):
        self.ip = ip
        self.template = template
        self.src = src
        self.cell = cell
        super().__init__()

    def getReplacedBuffer(self,filename):
        with open(filename,"r") as fi:
            buffer = fi.read()
            buffer = self.sub(buffer,{ "CELL": self.cell,
                                       "IP" : self.ip,
                                       "cell": self.cell.lower(),
                                       "ip" : self.ip.lower()
                                      })
        return buffer

    def run(self):
        if not os.path.exists(self.template):
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), self.template)

        useCellName = False
        if(not self.cell):
            self.cell = re.sub("_[^\_]+$","",self.ip)
        else:
            useCellName = True


        buffer = self.getReplacedBuffer(self.template)

        self.buf =  yaml.safe_load(buffer)

        # Make ip
        dir = self.ip.lower()
        if(useCellName):
            dir = self.cell

        os.makedirs(dir)
        os.chdir(dir)

        self.content = list()

        # Run the CMDs in the yaml files
        for (k,v) in self.buf.items():
            try:
                o = getattr(self,k)

            except Exception as e:
                self.error("Don't know how to support command '%s'" %k)
                o = None
            if(o):
                o(v)

    def dirs(self,data):
        """ Create dirs from a list of directories"""
        for d in data:
            self.comment("dirs: make '%s'" %d)
            self.content.append(d)
            os.makedirs(d)


    def copy(self,data):
        replaceVars = False

        if not self.src:
            path = ".." + os.path.sep + os.path.dirname(self.template) + os.path.sep
            replaceVars = True
        else:
            path = ".." + os.path.sep + self.src + os.path.sep

        for f in data:

            fsrc = path + f
            self.comment("copy: '%s'" %fsrc)
            self.content.append(f)
            if(os.path.exists(fsrc)):
                if(replaceVars):
                    buffer = self.getReplacedBuffer(fsrc)
                    with open(f,"w") as fo:
                        fo.write(buffer)
                else:
                    sh.copy(fsrc,f,follow_symlinks=False)
            else:
                self.comment("Could find %s" %fsrc)

    def create(self,data):
        for (k,v) in data.items():
            self.content.append(k)
            with open(k,"w") as fo:
                self.comment("create: '%s'" %k)
                fo.write(v)

    def do(self,data):
        for k in data:
            self.comment("do: '%s'" %k)
            self.doCmd(k)

    def echo(self,data):
        self.comment(data)
