# -*- coding: utf-8 -*-
from ..const import DEFAULT_WORKFLOWY_MONTH_QUOTA
from ..error import WFOverflowError
from math import isinf

__all__ = ["BaseQuota", "DefaultQuota", "ProQuota", "VoidQuota", 
    "SharedQuota"]

INF = float('inf')
assert isinf(INF)


class BaseQuota():
    def __init__(self):
        raise NotImplementedError

    def is_full(self):
        return self.used >= self.total

    def is_overflow(self):
        return self.used > self.total

    def is_underflow(self):
        return self.used < 0
        
    def handle_modify(self):
        if self.is_overflow():
            self.handle_overflow()
        elif self.is_underflow():
            self.handle_underflow()

    def handle_overflow(self):
        # It's NOT OK.
        raise NotImplementedError

    def handle_underflow(self):
        # It's OK.
        pass

    def __iadd__(self, other):
        self.used += other
        self.handle_modify()
        return self

    def __isub__(self, other):
        self.used -= other
        self.handle_modify()
        return self


class DefaultQuota(BaseQuota):
    def __init__(self, used=0, total=DEFAULT_WORKFLOWY_MONTH_QUOTA):
        self.used = used
        self.total = total

    @classmethod
    def from_main_project(cls, info):
        return cls(info["itemsCreatedInCurrentMonth"], info["monthlyItemQuota"])

    def handle_overflow(self):
        raise WFOverflowError("monthly item quota reached.")


class ProQuota(BaseQuota):
    def __init__(self):
        self.used = 0
        self.total = INF

    def handle_overflow(self):
        pass


class VoidQuota(BaseQuota):
    def __init__(self):
        self.used = INF
        self.total = 0

    def handle_overflow(self):
        raise WFOverflowError("quota infomation are not inited.")


class SharedQuota(BaseQuota):
    def __init__(self, is_over=False):
        self.used = 0
        self.total = INF
        self.is_over = is_over

    @property
    def is_over(self):
        return self.used == self.total

    @is_over.setter
    def is_over(self, is_over):
        self.used = INF if is_over else 0

    def is_overflow(self):
        return self.is_over

    def handle_overflow(self):
        raise WFOverflowError("monthly item quota reached in shared view.")
