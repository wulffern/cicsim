#from .spectrewriter import *
from .spiceparser import *
from .spec import *
from .command import *
from .cdsconf import *

import importlib.util

#- Each import is guarded individually so a missing optional dep (e.g. ``rich``)
#- doesn't silently skip later modules. Previously a single try/except wrapping
#- the whole block meant that a missing ``rich`` (used by ``cmdresults``) hid
#- ``ngraw`` and broke ``.raw`` loading in the wave viewer on machines without
#- the full set of optional deps installed (e.g. macOS dev installs).
for _modname in (
    "simcalc",
    "cmdip",
    "cmdspider",
    "cmdresults",
    "cmdsimdir",
    "cmdsimdirng",
    "cmdrun",
    "cmdrunng",
    "cmdsummary",
    "cmdarchive",
    "ngraw",
    "plot",
):
    try:
        _mod = __import__(__name__ + "." + _modname, fromlist=["*"])
        for _attr in getattr(_mod, "__all__", None) or [
            a for a in dir(_mod) if not a.startswith("_")
        ]:
            globals()[_attr] = getattr(_mod, _attr)
    except ModuleNotFoundError:
        #- Allow lightweight use of parser/spec helpers without optional data deps.
        pass

if importlib.util.find_spec("tkinter"):
    try:
        from .cmdwave import *
    except ModuleNotFoundError:
        pass
