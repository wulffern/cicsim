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


import logging
import cicsim as cs
import re
import os
import yaml
import glob
import pandas as pd
import numpy as np
import time
from rich.console import Console
from rich.table import Table
from rich import box
from rich.markup import escape

logger = logging.getLogger("cicsim")



class CmdResults(cs.Command):
    """ Summarize results of TESTBENCH """

    def __init__(self,runfile,runname=None,progress=False):
        if(runname is None):
            self.runname = runfile.replace(".run","")
        else:
            self.runname = runname
        self.runfile = runfile
        self.ofile = runfile.replace(".run","")
        self.testbench = re.sub("_.*","",runfile)
        self.progress = progress
        super().__init__()

    def summaryToMarkdown(self,specs,df_all):
        with open(f"results/{self.ofile}.md","w") as fo:
            fo.write(f"### Summary {self.runname}\n\n")
            fo.write(f"For details see <a href='{self.ofile}.html'>{self.ofile}.html</a>\n\n")
            fo.write("|**Name**|**Parameter**|**View**|**Min** | **Typ** | **Max**|\n")
            fo.write("|:---|:---|:---:|:---:|:---:|:---:|\n")

            dfg = df_all.groupby(["type"])
            for c in df_all.columns:
                if(c in ["name","type"]):
                    continue
                if(c not in specs):
                    continue
                spec = specs[c]

                for ind,df in dfg:

                    smin = ""
                    fo.write("|%s|%s | Spec | %s | %s | %s |\n" % (spec.name,c.replace("_","\\_"),spec.string(spec.min),spec.string(spec.typ),spec.string(spec.max)))
                    #print("|%s | %s|%0.4g | %0.4g | %0.4g |" % (c,ind,df[c].min(),df[c].mean(),df[c].max()))
                    fo.write("| | | %s|%s | %s | %s |\n" % (ind,spec.string(df[c].min()),spec.string(df[c].median()),spec.string(df[c].max())))

    def allToMarkdown(self,df_all):
        print("\n\n# All corners")
        print(df_all.describe().reset_index().to_markdown(tablefmt="github"))
        print(df_all.to_markdown(index=False,tablefmt="github"))

    def allToHtml(self,df_all):
        html = df_all.to_html()
        with open(f"{self.ofile}.html", "w") as text_file:
            text_file.write(html)

    def printFails(self,specs,df):

        df["OK"] = df.apply(specs.OK,axis=1)

        df.drop(columns=["index"],inplace=True)

        st = df.style.format(specs.format_dict()).apply(specs.css)

        if(not os.path.exists("results")):
            os.mkdir("results")

        logger.info(f"Writing CSV results/{self.ofile}.csv")
        df.to_csv(f"results/{self.ofile}.csv")

        with open(f"results/{self.ofile}.html", "w") as text_file:
            text_file.write(self.header)
            text_file.write(df.describe().style.format(specs.format_dict()).to_html())
            text_file.write(st.hide(axis='index').to_html())
            text_file.write(self.footer)


    def readYaml(self):
        files = list()
        with open(self.runfile) as fi:
            for l in fi:
                l = re.sub("\n","",l)
                files.append(l + ".yaml")

        frames = []
        for f in files:
            with open(f) as yaml_file:
                yaml_contents = yaml.safe_load(yaml_file)
            df = pd.json_normalize(yaml_contents)
            name = re.sub(r".*_", "", os.path.basename(f)).replace(".yaml","")
            df["name"] = name
            (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat(f)
            df["time"] = time.ctime(mtime)
            m = re.search("([A-Z]+[a-z]+)[A-Z]",name)
            if(m):
                df["type"] = m.group(1)
            frames.append(df)

        if not frames:
            return None

        df_all = pd.concat(frames, ignore_index=True)

        if df_all.empty:
            return None

        return df_all




    def printRich(self, df, specs=None):
        console = Console()
        str_cols = {"name", "time", "type"}
        key_cols = [c for c in ["name", "type"] if c in df.columns]
        data_cols = [c for c in df.columns if c not in key_cols]

        def spec_for(col):
            return specs[col] if specs and col in specs else None

        def display_val(col, raw):
            """Return (scaled_float, formatted_string) for a data cell."""
            sp = spec_for(col)
            v = raw * sp.scale if sp and sp.scale != 1 else raw
            return v, f"{v:.4g}"

        def col_header(col):
            sp = spec_for(col)
            if sp and sp.unit:
                return f"{col} {escape(f'[{sp.unit}]')}"
            return col

        def col_width(col):
            """Estimate rendered column width including cell padding."""
            sp = spec_for(col)
            scale = sp.scale if sp else 1
            header_w = len(col_header(col))
            if col in str_cols:
                val_w = df[col].astype(str).str.len().max() if len(df) else 0
            else:
                scaled = df[col].dropna() * scale
                val_w = int(scaled.apply(lambda v: len(f"{v:.4g}")).max()) if len(scaled) else 0
            return max(header_w, val_w) + 2  # +2 for cell padding

        key_width = sum(col_width(c) + 1 for c in key_cols)
        available = console.width - key_width

        # Group data columns into chunks that fit the terminal width
        chunks, chunk, chunk_w = [], [], 0
        for col in data_cols:
            w = col_width(col) + 1
            if chunk and chunk_w + w > available:
                chunks.append(chunk)
                chunk, chunk_w = [col], w
            else:
                chunk.append(col)
                chunk_w += w
        if chunk:
            chunks.append(chunk)

        def make_table(cols):
            t = Table(box=box.SIMPLE_HEAD, show_footer=False, highlight=True)
            for col in cols:
                if col in str_cols:
                    t.add_column(col, style="cyan", no_wrap=True)
                else:
                    t.add_column(col_header(col), justify="right")
            for _, row in df.iterrows():
                cells = []
                for col in cols:
                    val = row[col]
                    if col in str_cols:
                        cells.append(str(val))
                    elif pd.isna(val):
                        cells.append("")
                    else:
                        scaled, formatted = display_val(col, val)
                        sp = spec_for(col)
                        if sp:
                            if sp.OK(scaled):
                                formatted = f"[green]{formatted}[/green]"
                            else:
                                formatted = f"[bold red]{formatted}[/bold red]"
                        cells.append(formatted)
                t.add_row(*cells)
            return t

        for chunk in chunks:
            console.print(make_table(key_cols + chunk))

    def run(self):

        df_all = self.readYaml()
        if(df_all is None):
            logger.warning("No results found in yaml file")
            return

        specs = cs.Specification(self.testbench)

        #-Print all results
        self.printRich(df_all, specs if len(specs) > 0 else None)

        if(len(specs) > 0):
            df = df_all[specs.sources + ["name","type","time"]]
            df.reset_index(inplace=True)
            df = df.apply(specs.scale)

            self.printFails(specs,df)
            self.summaryToMarkdown(specs,df)

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
