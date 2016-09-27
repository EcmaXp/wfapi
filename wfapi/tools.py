# -*- coding: utf-8 -*-

import json
import os
import random
import re
import string
import uuid
from contextlib import contextmanager
from pprint import pprint
from urllib.error import HTTPError

__all__ = ["pprint", "debug_helper_with_json", "attrdict",
        "generate_tid", "generate_uuid", "uncapword", "uncapdict",
        "capture_http404"]


# for generate_tid
IDENTIFY_TID = string.digits + string.ascii_letters
RE_CAPWORD = re.compile("([A-Z]?[^A-Z]+)")


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


class attrdict(dict):
    def __init__(self, *args, **kwargs):
          super().__init__(*args, **kwargs)
          self.__dict__ = self

    def steal(self, obj, key):
        value = obj[key]
        del obj[key]
        self.update(value)
# TODO: KEEP attrdict? or add safe() for getting key safety


def generate_tid():
    return "".join(random.choice(IDENTIFY_TID) for i in range(8))


def generate_uuid():
    return str(uuid.UUID(bytes=os.urandom(16)))


def uncapword(word):
    return "_".join(RE_CAPWORD.findall(word)).lower()


def uncapdict(d):
    for k, v in d.items():
        yield uncapword(k), v


@contextmanager
def capture_http404(error_class=Exception):
    try:
        yield
    except HTTPError as e:
        if e.code == 404:
            raise error_class from e
        
        raise


def get_globals_from_home(content):
    for source in SCRIPT_TAG_REGEX.findall(content):
        if "(" in source:
            # function call found while parsing.
            continue

        for key, value in SCRIPT_VAR_REGEX.findall(source):
            if value.startswith("'") and value.endswith("'"):
                assert '"' not in value
                value = '"{}"'.format(value[+1:-1])

            if key == "FIRST_LOAD_FLAGS" or key == "SETTINGS":
                # TODO: non-standard json parse by demjson?
                continue

            value = json.loads(value)
            yield key, value


SCRIPT_TAG_REGEX = re.compile("".join([
re.escape('<script type="text/javascript">'), "(.*?)", re.escape('</script>'),
]), re.DOTALL)
SCRIPT_VAR_REGEX = re.compile("".join([
re.escape("var "), "(.*?)", re.escape(" = "), "(.*?|\{.*?\})", re.escape(";"), '$',
]), re.DOTALL | re.MULTILINE)