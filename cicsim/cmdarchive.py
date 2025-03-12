#!/usr/bin/env python3
#
import cicsim as cs
import os
import datetime

class CmdArchive(cs.Command):

    def __init__(self,name,color=True):

        dt = datetime.datetime.now()

        self.date =dt.strftime("%Y-%m-%d_%H-%M")
        self.fullname = "archive" + os.path.sep +  self.date + "_" + name.replace(" ","_")
        super().__init__(color)
        pass

    def archiveAll(self,runfiles):
        for f in runfiles:
            self.archive(f)

    def archive(self,runfile):

        files = list()
        with open(runfile) as fi:
            for line in fi:
                files.append(line)

        os.makedirs(self.fullname,exist_ok=True)


        baserun = os.path.basename(runfile)
        newrun = self.fullname + "_" + baserun

        newrunfiles = list()
        for f in files:
            f = f.strip()
            fb = self.fullname + os.path.sep + os.path.basename(f)
            newrunfiles.append(fb)


            cmd = f"cp {f}* {self.fullname}"
            self.comment("Info: " + cmd)
            os.system(cmd)

        self.comment(f"Info: writing {newrun}")
        with open(newrun,"w") as fo:
            for f in newrunfiles:
                fo.write(f)
