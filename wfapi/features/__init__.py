# -*- coding: utf-8 -*-
from ..error import WFUnsupportedFeature as _WFUnsupportedFeature

try:
    from .autologin import WFMixinAutoLogin
except _WFUnsupportedFeature:
    pass
