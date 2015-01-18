import time
raise NotImplementedError

# TODO: move timestamp to utils.timestamp or etc.

__all__ = ["py2wftime", "wf2pytime"]

def py2wftime(t, joined):
    return (t - joined) // 60

def cutminute(t, joined):
    # py to py but remove second infomation
    # return (t - joined) // 60 * 60?
    raise NotImplementedError

def wf2pytime(t, joined):
    # TODO: check by docstring, and check vaild
    raise NotImplementedError
    j = joined // 60
    return (t + j) * 60