# -*- coding: utf-8 -*-
from weakref import WeakValueDictionary

from . import Node
from ..const import DEFAULT_ROOT_NODE_ID
from ..error import WFNodeError

__all__ = ["BaseNodeManager", "NodeManager", "NodeManagerInterface"]


class BaseNodeManager():
    NODE_CLASS = NotImplemented


class NodeManager(BaseNodeManager):
    NODE_CLASS = Node

    def __init__(self, project):
        super().__init__()
        # XXX [!] cycle reference
        self.project = project
        self.data = WeakValueDictionary()
        self.root = None

    def update_root(self, root_project, root_project_children):
        self.root = self.new_root_node(root_project, root_project_children)

    def new_root_node(self, root_project, root_project_children):
        # XXX [!] project is Project, root_project is root node. ?!
        if root_project is None:
            root_project = dict(id=DEFAULT_ROOT_NODE_ID)
        else:
            root_project.update(id=DEFAULT_ROOT_NODE_ID)
            # in shared mode, root will have uuid -(replace)> DEFAULT_ROOT_NODE_ID

        root_project.update(ch=root_project_children)
        root = self.NODE_CLASS(root_project)
        return root

    def new_void_node(self):
        return self.NODE_CLASS()

    @property
    def pretty_print(self):
        return self.root.pretty_print


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
