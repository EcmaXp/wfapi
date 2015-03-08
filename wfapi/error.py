# -*- coding: utf-8 -*-

class ProjectReload(BaseException):
    pass


class WFError(Exception):
    pass


class WFUnsupportedFeature(WFError):
    pass


class WFRuntimeError(WFError):
    pass


class WFTransactionError(WFError):
    pass


class WFLoginError(WFError):
    pass


class WFNodeError(WFError):
    pass


class WFOverflowError(WFError, OverflowError):
    pass