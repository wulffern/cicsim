#!/usr/bin/env python3
#
import logging
import cicsim as cs
from cicsim.utils import parse_runfile
import glob
import os
import shutil
import datetime

logger = logging.getLogger("cicsim")

class CmdArchive(cs.Command):

    def __init__(self,name):

        dt = datetime.datetime.now()

        self.date =dt.strftime("%Y-%m-%d_%H-%M")
        self.fullname = "archive" + os.path.sep +  self.date + "_" + name.replace(" ","_")
        super().__init__()

    def archiveAll(self,runfiles):
        for f in runfiles:
            self.archive(f)

    def archive(self,runfile):

        files = parse_runfile(runfile)

        os.makedirs(self.fullname,exist_ok=True)

        baserun = os.path.basename(runfile)
        newrun = self.fullname + "_" + baserun

        newrunfiles = list()
        for f in files:
            fb = self.fullname + os.path.sep + os.path.basename(f)
            newrunfiles.append(fb)


            for src in glob.glob(f"{f}*"):
                logger.info(f"cp {src} {self.fullname}")
                shutil.copy2(src, self.fullname)

        logger.info(f"Writing {newrun}")
        with open(newrun,"w") as fo:
            for f in newrunfiles:
                fo.write(f)
