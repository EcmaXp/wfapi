# -*- coding: utf-8 -*-
from ...error import WFUnsupportedFeature as _WFUnsupportedFeature

# TODO: renamve 

from .deamon import *
from .weak import *

try:
    from .autologin import *
except _WFUnsupportedFeature:
    pass