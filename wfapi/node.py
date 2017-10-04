import copy
import datetime
import sys
from typing import Iterator

from .config import DEFAULT_ROOT_NODE_ID

if False:
    from .project import Project

__all__ = ["Node"]


class Node:
    __slots__ = ["project", "raw", "__weakref__"]

    def __init__(self, project, raw):
        self.project = project  # type: Project
        self.raw = raw

    def __repr__(self):
        return f"<{type(self).__name__}: {self.projectid!r}; {self.last_modified}; ...>"

    def __str__(self):
        completed = "; cp={!r}".format(self.completed_at) \
            if self.completed_at is not None else ""
        shared = "; shared={!r}".format(self.shared) \
            if self.shared else ""

        return (f"<{type(self).__name__}: "
                f"{self.projectid}; "
                f"{self.last_modified}; "
                f"name={self.name!r}; "
                f"description={self.description!r}; "
                f"len(self)={len(self)!r}"
                f"{completed}{shared}"
                ">")

    @property
    def parentid(self):
        """
        parent's node id
        """
        return self.project.track[self.projectid]

    @property
    def parent(self):
        """
        parent node

        :rtype: Node
        """
        parentid = self.parentid
        if parentid is None:
            return None

        return self.project.find_parent(self)

    @property
    def projectid(self):
        """
        node id

        :rtype: str
        """
        return self.raw["id"]

    def create(self, priority=-1, node=None) -> "Node":
        """
        create new node, parent will be this node.

        :rtype: Node
        """

        return self.project.op_create(self, priority=priority, child=node)

    def edit(self, name=None, description=None):
        """
        edit node's name and description.
        """

        return self.project.op_edit(self, name=name, description=description)

    def complete(self, modified=None):
        """
        Marked as completed.
        """

        return self.project.op_complete(self, modified=modified)

    def uncomplete(self):
        """
        Alias of `wfapi.node.Node:incomplete` function.
        """
        return self.project.op_uncomplete(self)

    def incomplete(self):
        """
        Marked as incompleted.
        """
        return self.uncomplete()

    def delete(self):
        """
        Delete the node from project and parent.
        """
        return self.project.op_delete(self)

    def search(self, pattern):
        """WIP: not implemented yet."""
        return self.project.op_search(self, pattern)

    @property
    def last_modified(self) -> datetime:
        """
        last modified time of node.

        :rtype datetime.datetime
        """
        lm = self.raw.get('lm')
        return self.project.get_python_timestamp(lm) if lm else None

    @property
    def name(self):
        """
        name of the node
        """
        return self.raw.get('nm')

    @name.setter
    def name(self, value):
        self.edit(name=value)

    @property
    def description(self):
        """
        description (aka memo) of the node

        :rtype datetime.datetime
        """
        return self.raw.get('no')

    @description.setter
    def description(self, value):
        self.edit(description=value)

    @property
    def completed_at(self):
        """
        completed time
        """
        cp = self.raw.get('cp')
        return self.project.get_python_timestamp(cp) if cp else None

    @property
    def shared(self):
        """
        shared info

        :return raw json object
        """
        return self.raw.get('shared')

    @property
    def is_completed(self):
        """
        check/assign node are completed (completed and incompleted)
        """
        return bool(self.completed_at)

    @is_completed.setter
    def is_completed(self, is_completed):
        if is_completed:
            self.complete()
        else:
            self.uncomplete()

    @property
    def children(self):
        """

        :return: copy of the child list.
        """
        return list(self)

    def _insert(self, index, node):
        self.raw.setdefault('ch', []).insert(index, node)

    def walk(self):
        """
        walk the node.
        """
        yield self

        for child in self:
            yield from child.walk()

    def pretty_print(self, stream=sys.stdout, indent=0):
        """
        pretty print the node.
        """
        INDENT_SIZE = 2

        def p(*args):
            print(" " * indent + " ".join(map(str, args)), file=stream)

        is_empty_root = (
            self.projectid == DEFAULT_ROOT_NODE_ID and
            not self.name and indent == 0)

        if is_empty_root:
            p("[*]", "Home")
        else:
            p("[%s]" % (self.raw.get('cp') and "-" or " ",),
              self.name,
              "{%s} " % self.projectid)

        for line in self.raw.get('no', "").splitlines():
            p(line)

        indent += INDENT_SIZE
        for child in self:
            child.pretty_print(stream=stream, indent=indent)

    def to_json(self):
        """
        copy the node's json object
        """
        return copy.deepcopy(self.raw)

    def __iter__(self) -> Iterator["Node"]:
        yield from self.project.find_child(self)

    def __bool__(self):
        return len(self) > 0

    def __len__(self):
        return len(self.raw.get('ch', []))

    def __getitem__(self, item) -> "Node":
        return self.children[item]

    def __delitem__(self, item):
        self[item].delete()

    def __eq__(self, other):
        return self.raw == other.raw
