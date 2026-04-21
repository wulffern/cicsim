#from .spectrewriter import *
from .spiceparser import *
from .spec import *
from .command import *
from .cdsconf import *

import importlib.util

try:
    from .simcalc import *
    from .cmdip import *
    from .cmdspider import *
    from .cmdresults import *
    from .cmdsimdir import *
    from .cmdsimdirng import *
    from .cmdrun import *
    from .cmdrunng import *
    from .cmdsummary import *
    from .cmdarchive import *
    from .ngraw import *
    from .plot import *
except ModuleNotFoundError:
    #- Allow lightweight use of parser/spec helpers without optional data deps.
    pass

if importlib.util.find_spec("tkinter"):
    try:
        from .cmdwave import *
    except ModuleNotFoundError:
        pass
