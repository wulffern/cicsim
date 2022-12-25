#!/usr/bin/env python3

import cicsim as cs
import os
import yaml
import pandas as pd

class ResultFile(cs.Command):

    def __init__(self,dataitem,specs):
        self.name = dataitem["name"]
        self.src = dataitem["src"] + ".csv"
        self.html = dataitem["src"] + ".html"
        self.method = dataitem["method"]
        super().__init__()

        self.link = f"<a href='{self.html}'>" + self.name + "</a>"
        self.df = None
        self.minimum = None
        self.typ = None
        self.maximum = None

        if(not os.path.exists(self.src)):
            self.warning(f"Could not find {self.src}")
            return


        self.df = pd.read_csv(self.src)



        self.df = self.df[specs.sources]

        self.df.reset_index(inplace=True)

        if("typ" in self.method):
            self.typical = self.df.median()
        elif("3std" in self.method):
            self.typical = self.df.mean()
            std = self.df.std()
            self.minimum = self.typical - 3*std
            self.maximum = self.typical + 3*std
        elif("std" in self.method):
            self.typical = self.df.mean()
            self.minimum = self.typical - self.df.std()
            self.maximum = self.typical + self.df.std()
        else:
            self.minimum = self.df.min()
            self.typical = self.df.median()
            self.maximum = self.df.max()

        pass



class SimulationSummary(cs.Command):

    def __init__(self,name,obj):
        self.tag = name
        self.specs = cs.Specification(self.tag)
        self.name = obj["name"]
        self.data = obj["data"]
        self.description = obj["description"]
        self.results = list()
        super().__init__()

        for k in self.data:
            self.results.append(ResultFile(k,self.specs))

    def heading(self,ss):
        if(ss is None or ss == ""):
            return ss
        else:
            return "**" + ss + "**"

    def to_markdown(self):

        ss = f"""### {self.name} ({self.tag})\n
{self.description}\n\n
|**Name**|**Parameter**|**Description**| |**Min**|**Typ**|**Max**| Unit|
|:---|:---|:---|---:|:---:|:---:|:---:| ---:|
"""

        for c in self.specs.sources:
            spec = self.specs[c]
            ss += "|%s|%s | | %s  | %s | %s | %s | %s |\n" % (self.heading(spec.name),
                                                                self.heading(c.replace("_","\\_")),
                                                                self.heading("Spec"),
                                                                self.heading(spec.stringNoUnit(spec.min)),
                                                                self.heading(spec.stringNoUnit(spec.typ)),
                                                                self.heading(spec.stringNoUnit(spec.max)),
                                                                self.heading(spec.unit))
            for r in self.results:
                minimum = ""
                if(r.minimum is not None and c in r.minimum):
                    minimum = spec.markdown(r.minimum[c])
                typ = ""
                if(r.typical is not None and c in r.typical):
                    typ = spec.markdown(r.typical[c])
                maximum = ""
                if(r.maximum is not None and c in r.maximum):
                    maximum = spec.markdown(r.maximum[c])


                ss +="| | | |%s|%s | %s | %s | |\n" % (r.link,minimum,typ,maximum)

        pass

        ss += "\n"


        return ss



class Summary(cs.Command):

    def __init__(self,filename):
        self.filename = filename
        self.sims = list()
        super().__init__()

        if(not os.path.exists(self.filename)):
            self.error(f"Could not find {self.filename}")
            exit()

        with open(self.filename) as fi:
            obj =yaml.safe_load(fi)


        self.description = obj["description"]
        o_sim = obj["simulations"]
        for k in o_sim:
            sim = SimulationSummary(k,o_sim[k])
            self.sims.append(sim)

    def to_markdown(self):
        ss = f"{self.description}\n\n"
        for s in self.sims:
            ss += s.to_markdown()
        return ss



class CmdSummary(cs.Command):

    def __init__(self,filename,output):
        self.filename = filename
        self.output = output

    def run(self):

        sm = Summary(self.filename)
        ss = sm.to_markdown()
        with open(self.output,"w") as fo:
            fo.write(ss)
