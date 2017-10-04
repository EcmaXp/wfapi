import os
import random
import re
import string
import uuid

__all__ = ["attrdict", "generate_uuid", "uncapdict"]

# for generate_tid
IDENTIFY_TID = string.digits + string.ascii_letters
RE_CAPWORD = re.compile("([A-Z]?[^A-Z]+)")


class attrdict(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self

    def steal(self, obj, key):
        value = obj[key]
        del obj[key]
        self.update(value)


def generate_tid():
    return "".join(random.choice(IDENTIFY_TID) for i in range(8))


def generate_uuid():
    return str(uuid.UUID(bytes=os.urandom(16)))


def uncapword(word):
    return "_".join(RE_CAPWORD.findall(word)).lower()


def uncapdict(d):
    for k, v in d.items():
        yield uncapword(k), v
