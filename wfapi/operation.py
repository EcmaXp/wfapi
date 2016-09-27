# -*- coding: utf-8 -*-

import json
import warnings

from .error import WFError, WFNodeError
from .tools import attrdict

__all__ = ["OperationCollection", "Operation"]  # and ...
OPERATION_REGISTERED = {}


class TransactionInterface():
    def transaction(self):
        # TODO: raise NotImplementedError
        pass


class OperationCollection(TransactionInterface):
    # TODO: add unsupported operation. (move, etc.)

    def edit(self, node, name=None, description=None):
        with self.transaction() as tr:
            tr += EditOperation(node, name, description)

    def create(self, parent, priority=-1, node=None):
        priority_range = range(len(parent) + 1)

        try:
            priority = priority_range[priority]
        except IndexError:
            raise WFError("invalid priority is selected (use default value)")

        with self.transaction() as tr:
            node = node or tr.project.new_void_node()
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
        raise NotImplementedError("search is not implemented yet.")


class Operation():
    operation_name = NotImplemented
    _cached = None

    def __init__(self, node):
        if self.operation_name is NotImplemented:
            raise NotImplementedError("operation_name is NotImplemented.")

        self.node = node
        raise NotImplementedError
        # ?

    def __repr__(self):
        # const name?
        return "<Operation: %s; %r>" % (self.operation_name, vars(self))

    def pre_operation(self, tr):
        pass

    def post_operation(self, tr):
        pass

    def get_operation(self, tr):
        operation = dict(
            type=self.operation_name,
            data=self.get_operation_data(tr),
        )

        return operation

    def get_cached_operation(self, tr):
        # TODO: check value modify?

        cached_tr = None
        if self._cached is not None:
            cached, cached_tr = self._cached

        if cached_tr is not tr:
            cached, cached_tr = self.get_operation(tr), tr
            self._cached = cached, cached_tr

        return cached.copy()

    def get_client_operation(self, tr):
        operation = self.get_cached_operation(tr)
        operation.update(
            client_timestamp=tr.get_client_timestamp(),
            undo_data=self.get_undo(tr),
            executed_by=12345,
        )

        # must filter by _empty_data_filter, but it lagging?
        return operation

    def get_default_undo_data(self):
        return dict(previous_last_modified=self.node.last_modified)

    def get_undo_data(self, tr):
        raise NotImplementedError

    def get_undo(self, tr):
        # XXX how to coding it? (by automation.)
        undo_data = self.get_default_undo_data()
        undo_data.update(self.get_undo_data(tr))
        return undo_data

    def _empty_data_filter(self, data):
        for key, value in list(data.items()):
            if value is None:
                data.pop(key)
            elif isinstance(value, dict):
                value = self._empty_data_filter(value)

        return data

    def get_operation_data(self, tr):
        raise NotImplementedError

    @classmethod
    def from_server_operation_json(cls, tr, op):
        op = attrdict(op)
        op = cls.prepare_server_operation_json(tr, op)
        assert cls.operation_name == op.type
        return cls.from_server_operation(tr, **op.data)

    @classmethod
    def prepare_server_operation_json(cls, tr, op):
        DEFAULT = object()
        # Sorry, projectid can be None.

        projectid = op.data.pop("projectid", DEFAULT)
        if projectid is not DEFAULT:
            op.data["node"] = tr.wf[projectid]
            # if not exist node, raise error?

        return op

    @classmethod
    def from_server_operation(cls, tr, **data):
        raise NotImplementedError

    def execute(self, tr):
        self.pre_operation(tr)
        self.post_operation(tr)

    @classmethod
    def _register(cls, operation):
        assert issubclass(operation, cls)

        operation_name = operation.operation_name
        assert operation_name not in OPERATION_REGISTERED

        __all__.append(operation.__name__)
        OPERATION_REGISTERED[operation_name] = operation

        return operation


_register_operation = Operation._register


class UnknownOperation(Operation):
    operation_name = "_unknown"

    def __init__(self, op):
        self.op = op

    @property
    def operation_name(self):
        return self.op.type

    @property
    def data(self):
        return self.op.data

    def __repr__(self):
        return "<UnknownOperation: %s; %r>" % (self.operation_name, self.data)

    def pre_operation(self, tr):
        pass

    def post_operation(self, tr):
        # TODO: how to warning?
        warnings.warn("Unknown %s operation detected." % self.operation_name)

    def get_operation_data(self, tr):
        return self.data

    def get_undo_data(self, tr):
        return {}

    @classmethod
    def from_server_operation_json(cls, tr, op):
        op = attrdict(op)
        op = cls.prepare_server_operation_json(tr, op)
        return cls.from_server_operation(tr, op)

    @classmethod
    def prepare_server_operation_json(cls, tr, op):
        return op

    @classmethod
    def from_server_operation(cls, tr, op):
        return cls(op)


@_register_operation
class EditOperation(Operation):
    operation_name = 'edit'

    def __init__(self, node, name=None, description=None):
        self.node = node
        self.name = name
        self.description = description

    def pre_operation(self, tr):
        pass

    def post_operation(self, tr):
        raw = self.node.raw

        if self.name is not None:
            raw['nm'] = self.name

        if self.description is not None:
            raw['no'] = self.description

    @classmethod
    def from_server_operation(cls, tr, node, name=None, description=None):
        return cls(node, name, description)

    def get_operation_data(self, tr):
        return dict(
            projectid=self.node.projectid,
            name=self.name,
            description=self.description,
        )

    def get_undo_data(self, tr):
        return dict(
            previous_name=self.node.name if self.name is not None else None,
            previous_description=self.node.description
            if self.description is not None else None,
        )


@_register_operation
class CreateOperation(Operation):
    operation_name = 'create'

    def __init__(self, parent, node, priority):
        self.parent = parent
        self.node = node
        self.priority = priority

    def pre_operation(self, tr):
        pass

    def post_operation(self, tr):
        self.parent._insert(self.priority, self.node.raw)
        # TODO: register parent
        tr.wf.add_node(self.node, update_quota=True)
        # TODO: better way to manage node.

    def get_operation_data(self, tr):
        return dict(
            projectid=self.node.projectid,
            parentid=self.parent.projectid,
            priority=self.priority,
        )

    def get_default_undo_data(self):
        return dict()

    def get_undo_data(self, tr):
        return {}

    @classmethod
    def prepare_server_operation_json(cls, tr, op):
        return op

    @classmethod
    def from_server_operation(cls, tr, projectid, parentid, priority):
        node = tr.project.new_void_node(projectid)
        node.raw['nm'] = ""
        node.raw['lm'] = tr.get_client_timestamp()
        # TODO: lmb support (lm extend)
        parent = tr.wf[parentid]
        return cls(parent, node, priority)


class _CompleteNodeOperation(Operation):
    operation_name = NotImplemented

    def pre_operation(self, tr):
        pass

    def post_operation(self, tr):
        pass

    def get_operation_data(self, tr):
        return dict(
            projectid=self.node.projectid,
        )

    def get_undo_data(self, tr):
        return dict(
           previous_completed=self.node.completed_at
           if self.node.completed_at is not None else False,
        )

    @classmethod
    def from_server_operation(cls, tr, node):
        return cls(node)


@_register_operation
class CompleteOperation(_CompleteNodeOperation):
    operation_name = 'complete'

    def __init__(self, node, modified=None):
        self.node = node
        self.modified = modified
        # modified will auto fill by get_operation_data if None

    def pre_operation(self, tr):
        super().pre_operation(tr)
        if self.modified is None:
            self.modified = tr.get_client_timestamp()

    def post_operation(self, tr):
        super().post_operation(tr)
        raw = self.node.raw
        raw['cp'] = self.modified


@_register_operation
class UncompleteOperation(_CompleteNodeOperation):
    operation_name = 'uncomplete'

    def __init__(self, node):
        self.node = node

    def post_operation(self, tr):
        raw = self.node.raw
        raw['cp'] = None


@_register_operation
class DeleteOperation(Operation):
    operation_name = 'delete'

    def __init__(self, node):
        self.node = node
        self.priority = self.node.parent.children.index(node)
        # TODO more priority calc safety.

    def pre_operation(self, tr):
        pass

    def post_operation(self, tr):
        node = self.node
        if self.node.parent:
            assert node in self.node.parent
            self.node.parent.raw.get('ch', []).remove(node.raw)

        tr.wf.remove_node(node, recursion=True)

    def get_operation_data(self, tr):
        return dict(
            projectid=self.node.projectid,
        )

    def get_undo_data(self, tr):
        return dict(
            parentid=self.node.parent.projectid,
            priority=self.priority,
        )


@_register_operation
class UndeleteOperation(Operation):
    operation_name = 'undelete'

    def __init__(self):
        raise NotImplementedError("Just don't do that. :P")


@_register_operation
class MoveOperation(Operation):
    operation_name = 'move'

    def __init__(self, parent, node, priority):
        self.parent = parent
        self.node = node
        self.priority = priority

    def pre_operation(self, tr):
        assert tr.project.nodemgr.check_exist_node(self.node)
        if self.parent is None:
            raise WFNodeError(
                "{!r} don't have parent. (possible?)".format(self.node))
        elif self.node not in self.parent:
            raise WFNodeError(
                "{!r} not have {!r}".format(self.parent, self.node))

    def post_operation(self, tr):
        raise NotImplementedError
        # TODO: fix this. (parent is missing; callback?)

        rawnode = self.node.raw
        rawnode.parent.remove(self.node)
        rawnode.parent = self.parent
        self.parent.insert(self.priority, self.node)

    def get_operation_data(self, tr):
        return dict(
            projectid=self.node.projectid,
            parentid=self.parent.projectid,
            priority=self.priority,
        )

    def get_undo_data(self, tr):
        previous_priority = None
        if self.node in self.parent:
            previous_priority = self.parent.ch.index(self.node)

        return dict(
            previous_parentid=self.parent.projectid,
            previous_priority=previous_priority,
        )

    @classmethod
    def prepare_server_operation_json(cls, tr, op):
        op = super().prepare_server_operation_json(tr, op)
        op.data["node"] = tr.wf[op.data.pop("projectid")]
        op.data["parent"] = tr.wf[op.data.pop("parentid")]
        return op

    @classmethod
    def from_server_operation(cls, tr, node, parent, priority):
        return cls(parent, node, priority)


class ShareOperation(Operation):
    operation_name = 'share'
    NotImplemented

    def __init__(self, node, share_type="url", write_permission=False):
        assert share_type == "url"
        self.node = node
        self.share_type = share_type
        self.write_permission = False

    def post_operation(self, tr):
        # rawnode = self.node
        # rawnode.shared = ...
        raise NotImplementedError

    def get_operation_data(self, tr):
        return dict(
            projectid=self.node.projectid,
            share_tyee=self.share_type,
            write_permission=self.write_permission,
        )

    def get_undo_data(self, tr):
        shared = self.node.shared
        if shared is None:
            return dict(
                previous_share_type=None,
                previous_write_permission=None,
            )
        elif "url_shared_info" in shared:
            url_shared = shared["url_shared_info"]
            return dict(
                previous_share_type="url",
                previous_write_permission=url_shared.get("write_permission"),
            )


@_register_operation
class UnshareOperation(Operation):
    operation_name = 'unshare'

    def __init__(self, node):
        self.node = node

    def pre_operation(self, tr):
        # TODO: should check node are shared?
        pass

    def post_operation(self, tr):
        rawnode = self.node
        rawnode.shared = None
        raise NotImplementedError

    def get_operation_data(self, tr):
        return dict(
            projectid=self.node.projectid,
        )

    get_undo_data = ShareOperation.get_undo_data

    @classmethod
    def from_server_operation(cls, tr, node):
        return cls(node)


@_register_operation
class BulkCreateOperation(Operation):
    operation_name = 'bulk_create'
    # This operation does add node (with many child) at one times.

    def __init__(self, parent, project_trees, starting_priority):
        self.parent = parent
        self.project_trees = project_trees
        self.starting_priority = starting_priority

    def pre_operation(self, tr):
        assert tr.project.nodemgr.check_not_exist_node(self.project_trees)

    def post_operation(self, tr):
        self.parent.insert(self.starting_priority, self.project_trees)
        tr.wf.add_node(self.project_trees, recursion=True)

    def get_operation_data(self, tr):
        return dict(
            parentid=self.parent.projectid,
            project_trees=self.project_trees.to_json(),
            starting_priority=self.starting_priority,
        )

    def get_undo_data(self, tr):
        return {}

    @classmethod
    def prepare_server_operation_json(cls, tr, op):
        op = super().prepare_server_operation_json(tr, op)
        op.data["project_trees"] = json.loads(op.data.pop("project_trees"))
        op.data["parent"] = tr.wf[op.data.pop("parentid")]
        return op

    @classmethod
    def from_server_operation(cls, tr, parent, project_trees,
                              starting_priority):
        project_trees = \
            tr.project.nodemgr.new_node_from_json(project_trees, parent=parent)
        return cls(parent, project_trees, starting_priority)


class BulkMoveOperation(Operation):
    operation_name = 'bulk_move'
    NotImplemented
