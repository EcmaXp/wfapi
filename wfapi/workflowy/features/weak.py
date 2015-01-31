# -*- coding: utf-8 -*-
import functools
from .. import BaseWorkflowy
from ...node import Node
from ...node.manager import NodeManager
from ...operation import OperationCollection


__all__ = ["WFMixinWeak"]

class _WeakNode(Node):
    __slots__ = []
    
    # virtual attribute: _wf

    def __getattr__(self, item):
        if not item.startswith("_") and item in dir(OperationCollection):
            return functools.partial(getattr(self._wf, item), self)
        
        raise AttributeError(item)

    # ??
    @property
    def projectid(self):
        return self.raw.id

    @property
    def last_modified(self):
        return self.raw.lm

    @property
    def name(self):
        return self.raw.nm

    @property
    def description(self):
        return self.raw.no

    @property
    def completed_at(self):
        return self.raw.cp

    @property
    def shared(self):
        return self.raw.shared

    @property
    def parent(self):
        return self.raw.parent
    # ??


    @Node.name.setter
    def name(self, name):
        self.edit(name, None)
        self.raw.nm = name

    @Node.description.setter
    def description(self, description):
        self.edit(None, description)
        self.raw.no = description

    @property
    def completed_at(self):
        # TODO: convert wf's timestamp to py's timestamp
        convert = lambda x: x
        return convert(self.raw.cp)

    @completed_at.setter
    def completed_at(self, completed_at):
        completed_at = self.complete(completed_at)
        self.raw.cp = completed_at

    @Node.completed_at.setter
    def is_completed(self, is_completed):
        if is_completed:
            self.raw.cp = self.complete()
        else:
            self.uncomplete()
            self.raw.cp = None

    # TODO: allow shared modify?
    #@property
    #def shared(self):
    #    return self.raw.shared

class WFMixinWeak(BaseWorkflowy):
    NODE_MANAGER_CLASS = NotImplemented

    def __init__(self, *args, **kwargs):
        # _WeakNode.define_with_workflowy()
        # NodeManager.define_with_nodecls()
        
        class _Node_(_WeakNode):
            __slots__ = []
            _wf = self

        class WFDynamicNodeManager(NodeManager):
            NODE_CLASS = _Node_

        self.NODE_MANAGER_CLASS = WFDynamicNodeManager
        super().__init__(*args, **kwargs)