import functools
from contextlib import contextmanager

from wfapi.browser import get_default_workflowy_url
from wfapi.error import WFTransactionError


class NodeManagerInterface():
    def __contains__(self, node):
        raise NotImplementedError

    def __getitem__(self, node):
        raise NotImplementedError

    def __iter__(self):
        raise NotImplementedError

    def add_node(self, node, recursion=True, update_quota=True):
        raise NotImplementedError

    def remove_node(self, node, recursion=False, update_quota=True):
        raise NotImplementedError


class BaseWorkflowy(NodeManagerInterface):
    PROJECT_MANAGER_CLASS = NotImplemented
    TRANSACTION_MANAGER_CLASS = NotImplemented

    def __init__(self):
        self._inited = False
        raise NotImplementedError

    def transaction(self):
        raise NotImplementedError

    # smart handler?
    # TODO: change handle method
    @contextmanager
    def smart_handle_init(self):
        try:
            yield
            self.handle_init()
        finally:
            pass

    @contextmanager
    def smart_handle_reset(self):
        try:
            self.handle_reset()
            yield
        finally:
            pass

    def reset(self):
        pass

    def _init(self, *args, **kwargs):
        pass

    def handle_init(self):
        pass

    def handle_reset(self):
        pass

    def handle_logout(self, counter=0):
        pass

    def reset(self):
        # TODO: give argument to _reset and smart handler?
        with self.smart_handle_reset():
            self._reset()

    def init(self, *args, **kwargs):
        # TODO: give argument to smart handler? (_init require argument!)
        with self.smart_handle_init():
            self._init(*args, **kwargs)

    @property
    def inited(self):
        return self._inited

    @inited.setter
    def inited(self, inited):
        if inited:
            self._inited = True
        else:
            if self._inited:
                self.reset()

            self._inited = False


class BaseProject(NodeManagerInterface):
    NODE_MANAGER_CLASS = NotImplemented # type: BaseProjectManager

    def __init__(self, ptree, pm):
        raise NotImplementedError


class BaseProjectManager():
    pass


class BaseTransaction():
    __slots__ = ["wf", "operations", "is_locked", "is_executed"]

    def __init__(self, wf):
        self.wf = wf # wf -> pj??
        self.operations = []
        self.is_executed = False
        self.is_locked = False

    def assert_pushable(self, operation=None):
        if not self.is_locked:
            return

        if operation is None:
            raise WFTransactionError("{!r} is locked".format(self))
        else:
            raise WFTransactionError("{!r} is locked, while push {!r}".format(self, operation))

    def get_client_timestamp(self, current_time=None):
        raise NotImplementedError

    def push(self, operation):
        raise NotImplementedError

    def pre_operation(self):
        for operation in self:
            operation.pre_operation(self)

    def post_operation(self):
        for operation in self:
            operation.post_operation(self)

    def handle_enter(self):
        pass

    def handle_exit(self, error):
        self.is_locked = True
        self.commit()

    def __iter__(self):
        return iter(self.operations)

    def __iadd__(self, other):
        self.push(other)

    def __enter__(self):
        self.handle_enter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.handle_exit(error=True)
            return False
        else:
            self.handle_exit(error=False)
        return False


class BaseTransactionManager():
    pass


class BaseNodeManager():
    NODE_CLASS = NotImplemented
