# -*- coding: utf-8 -*-
from ..error import WFUnsupportedFeature as _WFUnsupportedFeature

from .deamon import WFMixinDeamon
from .weak import WFMixinWeak

try:
    from .autologin import WFMixinAutoLogin
except _WFUnsupportedFeature:
    pass
