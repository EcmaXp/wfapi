# -*- coding: utf-8 -*-
from ..node import NodeManager, WeakNode
from ..project import Project, ProjectManager
from ..workflowy import BaseWorkflowy

__all__ = ["WFMixinWeak"]

# TODO: remove Weak and merge to wfapi!

class WFMixinWeak(BaseWorkflowy):
    PROJECT_MANAGER_CLASS = NotImplemented

    def __init__(self, *args, **kwargs):
        wf = self

        class DynamicProjectManager(ProjectManager):
            @property
            def PROJECT_CLASS(self):
                class _Node_(WeakNode):
                    __slots__ = []
                    _wf = wf
                    project = None

                class DynamicNodeManager(NodeManager):
                    NODE_CLASS = _Node_

                class DynamicProject(Project):
                    NODE_MANAGER_CLASS = DynamicNodeManager

                    def __init__(self, *args, **kwargs):
                        _Node_.project = self
                        super().__init__(*args, **kwargs)

                return DynamicProject

            @property
            def MAIN_PROJECT_CLASS(self):
                return self.PROJECT_CLASS

        self.PROJECT_MANAGER_CLASS = DynamicProjectManager
        super().__init__(*args, **kwargs)
