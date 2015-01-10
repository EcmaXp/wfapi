# -*- coding: utf-8 -*-
import functools
from ..node import WFNode
from ..nodemgr import WFNodeManager
from ..workflowy import BaseWorkflowy
from ..operation import WFOperationCollection


__all__ = ["WFMixinWeak"]

class WF_WeakNode(WFNode):
    __slots__ = []
    
    # virtual attribute: _wf

    def __getattr__(self, item):
        if not item.startswith("_") and item in dir(WFOperationCollection):
            return functools.partial(getattr(self._wf, item), self)

        raise AttributeError(item)

    @WFNode.name.setter
    def name(self, name):
        self.edit(name, None)
        self.raw.nm = name

    @WFNode.description.setter
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

    @WFNode.completed_at.setter
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
        # WF_WeakNode.define_with_workflowy()
        # WFNodeManager.define_with_nodecls()
        
        class _WFNode_(WF_WeakNode):
            __slots__ = []
            _wf = self

        class WFDynamicNodeManager(WFNodeManager):
            NODE_CLASS = _WFNode_

        self.NODE_MANAGER_CLASS = WFDynamicNodeManager
        super().__init__(*args, **kwargs)