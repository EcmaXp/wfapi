import time

# TODO: move timestamp to utils.timestamp or etc.

__all__ = ["py2wftime", "wf2pytime"]


def py2wftime(t, joined):
    return (t - joined) // 60


def cutminute(t, joined):
    # py to py but remove second infomation
    return t - ((t - joined) % 60)


def wf2pytime(t, joined):
    # TODO: check by docstring, and check vaild
    raise NotImplementedError
    j = joined // 60
    return (t + j) * 60
