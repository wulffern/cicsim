######################################################################
##        Copyright (c) 2020 Carsten Wulff Software, Norway
## ###################################################################
## Created       : wulff at 2020-12-13
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
import glob
import pandas as pd
import numpy as np
import time
import json

class SpecMinMax:

    def __init__(self,obj = None):

        self.min = None
        self.max = None
        self.unit = "V"
        self.scale = 1
        self.digits = 2
        self.sources = list()

        if(obj):
            if("src" in obj):
                if(type(obj["src"]) is list):
                    for s in obj["src"]:
                        self.sources.append(s)
                else:
                    self.sources.append(obj["src"])
            if("min" in obj):
                if(type(obj["min"]) is str):
                    self.min = eval(obj["min"])
                else:
                    self.min = obj["min"]

            if("max" in obj):
                if(type(obj["max"]) is str):
                    self.max = eval(obj["max"])
                else:
                    self.max = obj["max"]
            if("scale" in obj):
                self.scale = float(obj["scale"])
            if("unit" in obj):
                self.unit = obj["unit"]
            if("digits" in obj):
                self.digits = obj["digits"]


    def css(self,ser):

        css = list()
        for v in ser:
#            print(v)
#            print(self.max)
#               print(self.min)
            if(v > self.max or v < self.min):
                css.append('background-color:lightcoral')
            #elif(np.abs(v-self.max)/self.max > 0.1  or np.abs(v-self.min)/self.min > 0.1):
            #    css.append('background-color:red')
            else:
                css.append('')
        return css


    def format(self):
        return "{0:.%df} %s" % (self.digits,self.unit)
    
    def applyScale(self,s):

        return s*self.scale




class Specification(dict):

    def __init__(self,testbench):
        self.fname = testbench + ".yaml"
        self.sources = list()

        if(os.path.exists(self.fname)):
            with open(self.fname,"r") as fi:
                specobj = yaml.safe_load(fi)
            if(specobj):
                for k, v in specobj.items():
                    if("type"in v):
                        #Preparing for future types
                        pass
                    else:
                        self[k] = SpecMinMax(v)
                        for s in self[k].sources:
                            self.sources.append(s)
                            self[s] = self[k]

    def css(self,s):
        if(s.name in self):
            return self[s.name].css(s)
        else:
            return ['' for v in s]

    def scale(self,s):
        if(s.name in self):

            return self[s.name].applyScale(s)
        else:
            return s

    def format_dict(self):

        d = dict()
        for s,v in self.items():
            d[s] = v.format()
        return d



class CmdResults(cs.Command):
    """ Summarize results of TESTBENCH """

    def __init__(self,testbench):
        self.testbench = testbench
        super().__init__()

    def summaryToMarkdown(self,df_all):
        print("# Summary")
        print("|**Parameter**|**View**|**Min** | **Typ** | **Max**|**Unit**|")
        print("|:---| :-:| :-:| :-:| :-:| :-:|")

        dfg = df_all.groupby(["type"])
        for c in df_all.columns:
            if(c in ["name","type"]):
                continue
            for ind,df in dfg:
                print("|%s | %s|%0.4g | %0.4g | %0.4g |" % (c,ind,df[c].min(),df[c].mean(),df[c].max()))

    def allToMarkdown(self,df_all):
        print("\n\n# All corners")
        print(dfg.describe().reset_index().to_markdown(tablefmt="github"))
        print(df_all.to_markdown(index=False,tablefmt="github"))

    def allToHtml(self,df_all):
        html = df_all.to_html()
        text_file = open(f"{self.testbench}.html", "w")
        text_file.write(html)
        text_file.close()

    def printFails(self,specs,df):
        df = df[specs.sources + ["name","type","time"]]
        df.reset_index(inplace=True)
        #df = df[not "Index"]
        df = df.apply(specs.scale)
        st = df.style.format(specs.format_dict()).apply(specs.css)

        if(not os.path.exists("results")):
            os.mkdir("results")

        text_file = open(f"results/{self.testbench}.html", "w")
        text_file.write(self.header)
        text_file.write(df.describe().style.render())
        text_file.write(st.hide_index().render())
        text_file.write(self.footer)
        text_file.close()


    def readCsv(self):
        files = glob.glob(f"output_{self.testbench}/{self.testbench}_*.csv")
        df_all = pd.DataFrame()
        for f in files:
            df = pd.read_csv(f)
            name = os.path.basename(f).replace(".*_","").replace(".csv","")
            df["name"] = name
            (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat(f)
            df["time"] = time.ctime(mtime)
            m = re.search("([A-Z]+[a-z]+)[A-Z]",name)
            if(m):
                df["type"] = m.group(1)
            df_all = pd.concat([df,df_all])

        if(df_all.empty):
            self.warning("No CSV files found")
            return None

        #- Print each corner
        df_all.drop(columns=["Unnamed: 0"],inplace=True)
        return df_all

    def readYaml(self):
        files = glob.glob(f"output_{self.testbench}/{self.testbench}_*.yaml")
        df_all = pd.DataFrame()
        for f in files:
            with open(f) as yaml_file:
                yaml_contents = yaml.safe_load(yaml_file)
            df = pd.json_normalize(yaml_contents)
            name = os.path.basename(f).replace(".*_","").replace(".csv","")
            df["name"] = name
            (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat(f)
            df["time"] = time.ctime(mtime)
            m = re.search("([A-Z]+[a-z]+)[A-Z]",name)
            if(m):
                df["type"] = m.group(1)
            df_all = pd.concat([df,df_all])

        if(df_all.empty):
            self.error("No YAML files found either")
            return None
        return df_all




    def run(self):
        df_all = self.readCsv()
        if(df_all is None):
            df_all = self.readYaml()


        specs = Specification(self.testbench)

        if(len(specs) > 0):
            self.printFails(specs,df_all)

    header = """

<html><head>
<style>

table {
  background-color: #EEEEEE;
  width: 100%;
  text-align: left;
  border-collapse: collapse;
}
table td, table th {
  border: 3px solid #FFFFFF;
  padding: 6px 6px;
}
table tbody td {
  font-size: 13px;
}
table tr:nth-child(even) {
  background: #FCFCFC;
}
table thead {
  background: #1C6EA4;
  background: -moz-linear-gradient(top, #5592bb 0%, #327cad 66%, #1C6EA4 100%);
  background: -webkit-linear-gradient(top, #5592bb 0%, #327cad 66%, #1C6EA4 100%);
  background: linear-gradient(to bottom, #5592bb 0%, #327cad 66%, #1C6EA4 100%);
  border-bottom: 2px solid #444444;
}
table thead th {
  font-size: 15px;
  font-weight: bold;
  color: #FFFFFF;
  border-left: 2px solid #D0E4F5;
}
table thead th:first-child {
  border-left: none;
}

table tfoot {
  font-size: 14px;
  font-weight: bold;
  color: #FFFFFF;
}
table tfoot td {
  font-size: 14px;
}
table tfoot .links {
  text-align: right;
}
table tfoot .links a{
  display: inline-block;
  background: #1C6EA4;
  color: #FFFFFF;
  padding: 2px 8px;
  border-radius: 5px;
}


</style>
<head>
<body>
    """
    footer = """
    </body></html>"""
