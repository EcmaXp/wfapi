# -*- coding: utf-8 -*-
raise NotImplementedError
import enum #?

# TODO: move shared to node.shared or node.shared_info


class WFBaseSharedInfo():
    pass

class WFSharedImfo(WFBaseSharedInfo):
    @classmethod
    def from_json(cls, data):
        pass

class WFURLSharedInfo(WFBaseSharedInfo):
    __slots__ = []

    def __init__(self, shared_info):
        pass

    @classmethod
    def from_shared_info(cls):
        pass
