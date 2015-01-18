# -*- coding: utf-8 -*-
import pickle
import sys
import warnings
import random
import threading
from collections import namedtuple
from .. import BaseWorkflowy
from ...error import WFUnsupportedFeature

__all__ = ["WFMixinAutoLogin"]

try:
    sys._getframe(0)
except Exception:
    raise WFUnsupportedFeature("autologin are disabled. cause by sys._getframe calling is failed.")

def _SafeSupport():
    global DEFAULT_PROTECTED_OBJECT
    DEFAULT_PROTECTED_OBJECT = object()
    B = random.randrange(2**32)
    C = random.randrange(2**32) * B / len(repr(DEFAULT_PROTECTED_OBJECT))
    D = random.randrange(0xFF)

    def E(F):
        I = random.Random(B)
        return bytes((J^F for J, F in zip((I.randrange(2**8)^D^(i&0xFF) for i in range(len(F))), F)))
    
    global Protected
    class Protected():
        __slots__ = ["froms"]
        
        def __init__(self, froms=None):
            self.froms = froms
     
        def __repr__(self):
            assert self is not self.froms
            return "<%s object from %r>" % (type(self).__name__, self.froms)

    global ProtectObject
    class ProtectObject():
        __slots__ = ["_data"]
     
        def __init__(self, data=DEFAULT_PROTECTED_OBJECT, secret_data=None):
            if secret_data is not None:
                self._data = secret_data
            elif data is DEFAULT_PROTECTED_OBJECT:
                del self.data # set default
            else:
                self.data = data
     
        @property
        def data(self, _getframe=sys._getframe):
            if _getframe(1).f_globals == globals():
                return pickle.loads(E(self._data))
 
            return Protected(self)
     
        @data.setter
        def data(self, data):
            self._data = E(pickle.dumps(data))
     
        @data.deleter
        def data(self):
            self.data = Protected()
     
        def __repr__(self):
            module = type(self).__module__
            module = (module and module != "__main__") and "%s." % (module,) or ""
            name = type(self).__name__
            
            return "%s%s(secret_data=%r)" % (module, name, self._data)

_SafeSupport()
del _SafeSupport

AuthInfo = namedtuple("AuthInfo", "username, password")


class WFMixinAutoLogin(BaseWorkflowy):
    def __init__(self, *args, **kwargs):
        self.share_id = None
        self.auth = None
        super().__init__(*args, **kwargs)

    def _reset(self):
        self.share_id = None
        self.auth = None
        super()._reset()

    def login(self, username_or_sessionid, password=None, **kwargs):
        if password is not None:
            self.auth = AuthInfo(
                username=Protected(username_or_sessionid),
                password=Protected(password),
            )
            
        super().__init__(username_or_sessionid, password, **kwargs)
        
    def _init(self, share_id=None, **kwargs):
        if share_id is not None:
            self.share_id = share_id
        
        super()._init(self.share_id, **kwargs)
        
    def handle_logout(self, counter=0):
        self.login(self.auth.username.data, self.auth.password.data)
        if counter:
            raise WFLoginError("Login counter are not zero!")
