# -*- coding: utf-8 -*-
import functools

from .. import BaseWorkflowy
from ...node import Node
from ...node.manager import NodeManager
from ...operation import OperationCollection
from ...project import Project
from ...project.manager import ProjectManager

__all__ = ["WFMixinWeak"]


class _WeakNode(Node):
    __slots__ = []
    
    # virtual attribute: _wf

    def __getattr__(self, item):
        if not item.startswith("_") and item in dir(OperationCollection):
            return functools.partial(getattr(self._wf, item), self)

        raise AttributeError(item)

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
        self.raw['cp'] = completed_at

    @Node.completed_at.setter
    def is_completed(self, is_completed):
        if is_completed:
            self.raw.cp = self.complete()
        else:
            self.uncomplete()
            self.raw['cp'] = None

    # TODO: allow shared modify?
    #@property
    #def shared(self):
    #    return self.raw.shared


class WFMixinWeak(BaseWorkflowy):
    PROJECT_MANAGER_CLASS = NotImplemented

    def __init__(self, *args, **kwargs):
        class _Node_(_WeakNode):
            __slots__ = []
            _wf = self
            project = None # ??

        class DynamicNodeManager(NodeManager):
            NODE_CLASS = _Node_

        class DynamicProject(Project):
            NODE_MANAGER_CLASS = DynamicNodeManager

        class DynamicProjectManager(ProjectManager):
            MAIN_PROJECT_CLASS = DynamicProject
            PROJECT_CLASS = DynamicProject

        self.PROJECT_MANAGER_CLASS = DynamicProjectManager
        super().__init__(*args, **kwargs)
