# -*- coding: utf-8 -*-
from .settings import DEFAULT_WORKFLOWY_MONTH_QUOTA
from .exception import WFOverflowError

class WFBaseQuota():
    def is_full(self):
        return self.used >= self.total

    def is_overflow(self):
        return self.used > self.total

    def handle_overflow(self):
        # It's NOT OK.
        raise NotImplementedError

    def handle_underflow(self):
        # It's OK.
        pass

    def __iadd__(self, other):
        self.used += other
        if self.is_overflow():
            self.handle_overflow()
        return self

    def __isub__(self, other):
        self.used -= other
        if self.is_underflow():
            self.handle_underflow()
        return self

    def is_full(self):
        return self.used >= self.total

    def is_overflow(self):
        return self.used > self.total

    def is_underflow(self):
        return self.used < 0


class WFQuota(WFBaseQuota):
    def __init__(self, used=0, total=DEFAULT_WORKFLOWY_MONTH_QUOTA):
        self.used = used
        self.total = total

    @classmethod
    def from_main_project(cls, info):
        return cls(info["itemsCreatedInCurrentMonth"], info["monthlyItemQuota"])

    def handle_overflow(self):
        raise WFOverflowError("monthly item quota reached.")


class WFSharedQuota(WFBaseQuota):
    MINIMAL = 0
    MAXIMUM = float('inf')

    def __init__(self, is_over=False):
        super().__init__(self.MINIMAL, self.MAXIMUM)
        self.is_over = is_over

    @property
    def is_over(self):
        return self.used == self.total

    @is_over.setter
    def is_over(self, is_over):
        self.used = self.MAXIMUM if is_over else self.MINIMAL

    def handle_overflow(self):
        raise WFOverflowError("monthly item quota reached in shared view.")
