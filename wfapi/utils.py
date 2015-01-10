# -*- coding: utf-8 -*-
import os
import uuid
import random
import string
from contextlib import contextmanager

__all__ = []

def allplus(obj):
    __all__.append(obj.__name__)
    return obj

# for generate_tid
IDENTIFY_TID = string.digits + string.ascii_letters


@allplus
@contextmanager
def debug_helper_with_json(info):
    if __debug__:
        try:
            yield
        except Exception:
            print()
            print("[ERROR] Error Raised!")
            # TODO?
            pprint(info)
            raise
    else:
        yield

@allplus
class attrdict(dict):
    def __init__(self, *args, **kwargs):
          super().__init__(*args, **kwargs)
          self.__dict__ = self

    def steal(self, obj, key):
        value = obj[key]
        del obj[key]
        self.update(value)

@allplus
def generate_tid():
    return "".join(random.choice(IDENTIFY_TID) for i in range(8))

@allplus
def generate_uuid():
    return str(uuid.UUID(bytes=os.urandom(16)))