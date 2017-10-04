from math import isinf

from .config import DEFAULT_WORKFLOWY_MONTH_QUOTA
from .error import WFOverflowError

__all__ = ["Quota", "DefaultQuota", "ProQuota", "VoidQuota", "SharedQuota"]

INF = float('inf')
assert isinf(INF)


class Quota():
    def __init__(self, used, total):
        self.used = used
        self.total = total

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

    def update(self, status):
        pass

    def __iadd__(self, other):
        self.used += other
        self.handle_modify()
        return self

    def __isub__(self, other):
        self.used -= other
        self.handle_modify()
        return self


class DefaultQuota(Quota):
    def __init__(self, used=0, total=DEFAULT_WORKFLOWY_MONTH_QUOTA):
        super().__init__(used=used, total=total)

    def update(self, status):
        self.used = status.items_created_in_current_month
        self.total = status.monthly_item_quota

    def handle_overflow(self):
        raise WFOverflowError("monthly item quota reached.")


class ProQuota(Quota):
    def __init__(self):
        super().__init__(used=0, total=INF)

    def handle_overflow(self):
        pass


class VoidQuota(Quota):
    def __init__(self):
        super().__init__(used=INF, total=0)

    def handle_overflow(self):
        raise WFOverflowError("quota information are not inited.")


class SharedQuota(Quota):
    def __init__(self, is_over=False):
        super().__init__(used=0, total=INF)
        self.is_over = is_over

    def update(self, status):
        self.is_over = status.over_quota

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
