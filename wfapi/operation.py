# -*- coding: utf-8 -*-

import warnings

if False:
    from .project import Project

__all__ = ["Operation", "EditOperation", "CreateOperation", "CompleteOperation",
           "UncompleteOperation", "DeleteOperation"]

OPERATION_REGISTERED = {}


class Operation():
    operation_name = NotImplemented

    @classmethod
    def __init_subclass__(cls, **kwargs):
        OPERATION_REGISTERED[cls.operation_name] = cls

    def __init__(self, project, node):
        self.project = project  # type: project.Project
        self.node = node  # type: node.Node

    def __repr__(self):
        return "<Operation: %s; %r>" % (self.operation_name, vars(self))

    def pre_operation(self):
        # execute by client & server
        pass

    def post_operation(self):
        # execute by server only
        raise NotImplementedError

    def get_operation(self):
        operation = dict(
            type=self.operation_name,
            data=self.get_operation_data(),
        )

        return operation

    def get_default_undo_data(self):
        return dict(previous_last_modified=self.node.raw.get('lm'))

    def get_undo_data(self):
        raise NotImplementedError

    def get_undo(self):
        undo_data = self.get_default_undo_data()
        undo_data.update(self.get_undo_data())
        return undo_data

    def get_operation_data(self):
        raise NotImplementedError

    @classmethod
    def from_server_operation(cls, project, data) -> "Operation":
        raise NotImplementedError

    @classmethod
    def _empty_data_filter(cls, data):
        for key, value in list(data.items()):
            if value is None:
                data.pop(key)
            elif isinstance(value, dict):
                value = cls._empty_data_filter(value)

        return data


class UnknownOperation(Operation):
    operation_name = "_unknown"

    def __init__(self, project, node, op):
        super().__init__(project, None)
        self.op = op

    @property
    def operation_name(self):
        return self.op.type

    @property
    def data(self):
        return self.op.data

    def __repr__(self):
        return f"<UnknownOperation: {self.operation_name}; {self.data!r}>"

    def pre_operation(self):
        pass

    def post_operation(self):
        # TODO: how to warning?
        warnings.warn("Unknown %s operation detected." % self.operation_name)

    def get_operation_data(self):
        return self.data

    def get_undo_data(self):
        return {}

    @classmethod
    def from_server_operation(cls, project, op):
        return cls(project, None, op)


class EditOperation(Operation):
    operation_name = 'edit'

    def __init__(self, project, node, name=None, description=None):
        super().__init__(project, node)
        self.name = name
        self.description = description

    def pre_operation(self):
        pass

    def post_operation(self):
        raw = self.node.raw

        if self.name is not None:
            raw['nm'] = self.name

        if self.description is not None:
            raw['no'] = self.description

    @classmethod
    def from_server_operation(cls, project: "Project", data):
        return cls(
            project=project,
            node=project.find_node(data['projectid']),
            name=data["name"],
            description=data["description"],
        )

    def get_operation_data(self):
        return dict(
            projectid=self.node.projectid,
            name=self.name,
            description=self.description,
        )

    def get_undo_data(self):
        return dict(
            previous_name=self.node.raw.get('nm') if self.name is not None else None,
            previous_description=self.node.raw.get('no')
            if self.description is not None else None,
        )


class CreateOperation(Operation):
    operation_name = 'create'

    def __init__(self, project, node, child, priority):
        super().__init__(project, node)
        self.child = child
        self.priority = priority

    def pre_operation(self):
        if self.priority < 0:
            self.priority = len(self.node) + self.priority + 1

        self.project.pending.setdefault(self.child.projectid, self.child)

    def post_operation(self):
        self.project.pending.pop(self.child.projectid, None)

        # noinspection PyProtectedMember
        self.node._insert(self.priority, self.child.raw)
        self.project.add_node(node=self.child, parent=self.node, update_quota=True)

    def get_operation_data(self):
        return dict(
            parentid=self.node.projectid,
            projectid=self.child.projectid,
            priority=self.priority,
        )

    def get_default_undo_data(self):
        return dict()

    def get_undo_data(self):
        return {}

    @classmethod
    def from_server_operation(cls, project: "Project", data):
        child = project.find_pending(data['projectid'])
        child.raw.update({
            'nm': '',
            'lm': project.get_client_timestamp(),
        })

        node = project.find_node(data['parentid'])

        return cls(
            project=project,
            node=node,
            child=child,
            priority=data["priority"],
        )


# noinspection PyAbstractClass
class _CompleteNodeOperation(Operation):
    operation_name = NotImplemented

    def get_operation_data(self):
        return dict(
            projectid=self.node.projectid,
        )

    def get_undo_data(self):
        return dict(
            previous_completed=self.node.raw.get('cp', False),
        )

    @classmethod
    def from_server_operation(cls, project: "Project", data):
        return cls(
            project=project,
            node=project.find_node(data['projectid']),
        )


class CompleteOperation(_CompleteNodeOperation):
    operation_name = 'complete'

    def __init__(self, project, node, modified=None):
        super().__init__(project, node)
        self.modified = modified

    def pre_operation(self):
        if self.modified is None:
            self.modified = self.project.get_client_timestamp()

    def post_operation(self):
        raw = self.node.raw
        raw['cp'] = self.modified


class UncompleteOperation(_CompleteNodeOperation):
    operation_name = 'uncomplete'

    def __init__(self, project, node):
        super().__init__(project, node)

    def post_operation(self):
        raw = self.node.raw
        raw['cp'] = None


class DeleteOperation(Operation):
    operation_name = 'delete'

    def __init__(self, project, node):
        super().__init__(project, node)
        self.node = node
        self.priority = self.node.parent.children.index(node)

    def pre_operation(self):
        pass

    def post_operation(self):
        node = self.node
        if self.node.parent:
            assert node in self.node.parent
            self.node.parent.raw.get('ch', []).remove(node.raw)

        self.project.remove_node(node=node)

    def get_operation_data(self):
        return dict(
            projectid=self.node.projectid,
        )

    def get_undo_data(self):
        return dict(
            parentid=self.node.parent.projectid,
            priority=self.priority,
        )

    @classmethod
    def from_server_operation(cls, project, data) -> "Operation":
        return cls(
            project=project,
            node=project.find_node(data['projectid']),
        )
