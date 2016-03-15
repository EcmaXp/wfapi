# -*- coding: utf-8 -*-
from ..error import WFError
from .operations import (CompleteOperation, CreateOperation, DeleteOperation,
                         EditOperation, UncompleteOperation)

__all__ = ["OperationCollection"]

class OperationCollection():
    # TODO: add unsupported operation. (move, etc.)

    def edit(self, node, name=None, description=None):
        with self.transaction() as tr:
            tr += EditOperation(node, name, description)

    def create(self, parent, priority=-1, *, node=None):
        #import pdb; pdb.set_trace()
        priority_range = range(len(parent) + 1)

        try:
            priority = priority_range[priority]
        except IndexError:
            raise WFError("invalid priority are selected. (just use default value.)")


        with self.transaction() as tr:
            node = tr.project.nodemgr.new_void_node() if node is None else node
            tr += CreateOperation(parent, node, priority)

        return node

    def complete(self, node, client_timestamp=None):
        with self.transaction() as tr:
            if client_timestamp is None:
                client_timestamp = tr.get_client_timestamp()
            tr += CompleteOperation(node, client_timestamp)
        return client_timestamp

    def uncomplete(self, node):
        with self.transaction() as tr:
            tr += UncompleteOperation(node)

    def delete(self, node):
        with self.transaction() as tr:
            tr += DeleteOperation(node)

    def search(self, node, pattern):
        # pattern is very complex.
        # http://blog.workflowy.com/2012/09/25/hidden-search-operators/
        raise NotImplementedError("search are not implemented yet.")
