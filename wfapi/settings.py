# -*- coding: utf-8 -*-

# TODO: Add more debug option and use logging module.
DETAIL_DEBUG = False

DEFAULT_WORKFLOWY_URL = "https://workflowy.com/"
DEFAULT_ROOT_NODE_ID = "None"

FEATURE_XXX_PRO_USER = False # it does nothing. just define more empty classes.
FEATURE_USE_FAST_REQUEST = True

DEFAULT_WORKFLOWY_CLIENT_VERSION = 14 # @ 2014-12-22
DEFAULT_WORKFLOWY_MONTH_QUOTA = 250

def _setup():
    from http.client import HTTPConnection

    if DETAIL_DEBUG:
        _HTTPConnection.debuglevel = 1
        
_setup()
del _setup