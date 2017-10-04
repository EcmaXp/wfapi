# -*- coding: utf-8 -*-


class WFException(Exception):
    pass


class ProjectReload(WFException):
    pass


class WFError(WFException):
    pass


class WFRuntimeError(WFError):
    pass


class WFTransactionError(WFError):
    pass


class WFLoginError(WFError):
    pass


class WFNodeError(WFError):
    pass


class WFNodeNotFoundError(WFNodeError):
    pass


class WFOverflowError(WFError):
    pass
