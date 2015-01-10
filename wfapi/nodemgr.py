# -*- coding: utf-8 -*-
from weakref import WeakValueDictionary
from .node import WFNode
from .settings import DEFAULT_ROOT_NODE_ID

__all__ = ["WFBaseNodeManager", "WFNodeManager"]


class WFBaseNodeManager():
    NODE_CLASS = NotImplemented


class WFNodeManager(WFBaseNodeManager):
    NODE_CLASS = WFNode

    def __init__(self):
        super().__init__()
        self.data = WeakValueDictionary()
        self.root = None

    def update_root(self, root_project, root_project_children):
        self.root = self.new_root_node(root_project, root_project_children)

    def __setitem__(self, projectid, node):
        assert self.check_not_exist_node(node)
        assert projectid == node.projectid
        self.data[node.projectid] = node
        assert self.check_exist_node(node)

    def __delitem__(self, node):
        assert self.check_exist_node(node)
        del self.data[node.projectid]
        assert self.check_not_exist_node(node)

    def __iter__(self):
        # how to support lock for iter? just copy dict?
        return iter(self.data.values())

    def __contains__(self, node):
        if node is None:
            return False

        newnode = self.data.get(node.projectid)
        return node is newnode # ?!

    def __len__(self):
        return len(self.data)

    def __bool__(self):
        return len(self) != 0

    @property
    def get(self):
        return self.data.get

    @property
    def clear(self):
        return self.data.clear

    # TODO: add expend node. (not operation.)

    def check_exist_node(self, node):
        original_node = self.get(node.projectid)
        if original_node is None:
            raise WFNodeError("{!r} is not exists.".format(node))
        elif original_node is not node:
            raise WFNodeError("{!r} is invalid node.".format(node))
        return True

    def check_not_exist_node(self, node):
        if node in self:
            raise WFNodeError("{!r} is already exists.".format(node))
        return True

    def new_void_node(self, uuid=None):
        return self.NODE_CLASS.from_void(uuid)

    def new_node_from_json(self, data, parent=None):
        return self.NODE_CLASS.from_json(data, parent=parent)

    def add(self, node, update_child=True):
        assert update_child is True

        added_nodes = 0
        def register_node(node):
            nonlocal added_nodes
            self[node.projectid] = node
            added_nodes += 1

        register_node(node)
        if update_child:
            def deep(node):
                for subnode in node:
                    register_node(subnode)
                    deep(subnode)

            deep(node)

        return added_nodes

    def remove(self, node, recursion_delete=True):
        assert self.check_exist_node(node)
        if node.parent is not None:
            assert self.check_exist_node(node.parent)
            if node in node.parent:
                raise WFNodeError("node are still exists in parent node.")

        removed_nodes = 0
        def unregister_node(node):
            nonlocal removed_nodes
            del node.parent
            del self[node]
            removed_nodes += 1

        unregister_node(node)
        if recursion_delete:
            def deep(node):
                if not node:
                    return

                child_nodes, node.ch = node.ch[:], None
                for child in child_nodes:
                    unregister_node(node)
                    deep(child)

            deep(node)

        return removed_nodes

    def new_root_node(self, root_project, root_project_children):
        if root_project is None:
            root_project = dict(id=DEFAULT_ROOT_NODE_ID)
        else:
            root_project.update(id=DEFAULT_ROOT_NODE_ID)
            # in shared mode, root will have uuid -(replace)> DEFAULT_ROOT_NODE_ID

        root_project.update(ch=root_project_children)
        root = self.new_node_from_json(root_project)
        self.add(root, update_child=True)
        return root

    @property
    def pretty_print(self):
        return self.root.pretty_print
