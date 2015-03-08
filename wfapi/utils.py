# -*- coding: utf-8 -*-
import os
import uuid
import random
import re
import string
from pprint import pprint
from contextlib import contextmanager
from urllib.error import HTTPError


# TODO: remove pprint from other code.
__all__ = ["pprint"]

def allplus(obj):
    __all__.append(obj.__name__)
    return obj

# for generate_tid
IDENTIFY_TID = string.digits + string.ascii_letters
REGEX_CAPWORD = re.compile("([A-Z]?[^A-Z]+)")

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
# TODO: KEEP attrdict? or add safe() for getting key safety

@allplus
def generate_tid():
    return "".join(random.choice(IDENTIFY_TID) for i in range(8))

@allplus
def generate_uuid():
    return str(uuid.UUID(bytes=os.urandom(16)))

@allplus
def uncapword(word):
    return "_".join(REGEX_CAPWORD.findall(word)).lower()

@allplus
def uncapdict(d):
    for k, v in d.items():
        yield uncapword(k), v
        
@allplus
@contextmanager
def capture_http404(error_class=Exception):
    try:
        yield
    except HTTPError as e:
        if e.code == 404:
            raise error_class from e
        
        raise
