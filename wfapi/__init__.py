#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Workflowy Python3 API v{__version__}
{__project_url__} by {__author__}

Workflowy: Organize your brain.
But did you think about what if workflowy can access by API?

This module provide api for workflowy with python3.

You can add node, edit, complete, or uncomplete, etc.
"""
from .workflowy import Workflowy
from .workflowy.features import *

__project_url__ = "http://github.com/sigsrv/wfapi"
__author__ = "sigsrv (sigsrv@sigsrv.net)"

__version__ = "0.4.0-alpha"

__doc__ = __doc__.format_map(globals())
__all__ = ["Workflowy"]


def _setup():
    for k, v in globals().items():
        if k.startswith("WFMixin"):
            if not k[len("WFMixin"):].startswith("_"):
                __all__.append(k)
            # TODO: other mixin support, mean check allowed mix with wf class

_setup()
del _setup
