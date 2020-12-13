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

class CmdResults(cs.Command):
    """ Summarize results of TESTBENCH """

    def __init__(self,testbench):
        self.testbench = testbench
        super().__init__()


    def run(self):
        files = glob.glob(f"output_{self.testbench}/{self.testbench}_*.csv")
        df_all = pd.DataFrame()
        for f in files:
            df = pd.read_csv(f)
            name = os.path.basename(f).replace("tran_","").replace(".csv","")
            df["name"] = name
            m = re.search("([A-Z]+[a-z]+)[A-Z]",name)
            if(m):
                df["type"] = m.group(1)
            df_all = pd.concat([df,df_all])

        if(df_all.empty):
            self.error("No CSV files found")
            return

        #- Print each corner
        df_all.drop(columns=["Unnamed: 0"],inplace=True)

        print("# Summary")
        print("|**Parameter**|**View**|**Min** | **Typ** | **Max**|**Unit**|")
        print("|:---| :-:| :-:| :-:| :-:| :-:|")

        dfg = df_all.groupby(["type"])
        for c in df_all.columns:
            if(c in ["name","type"]):
                continue
            for ind,df in dfg:
                print("|%s | %s|%0.2g | %0.2g | %0.2g |" % (c,ind,df[c].min(),df[c].mean(),df[c].max()))


        print("\n\n# All corners")
        #print(dfg.describe().reset_index().to_markdown(tablefmt="github"))
        print(df_all.to_markdown(index=False,tablefmt="github"))
