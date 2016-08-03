# -*- coding: utf-8 -*-
import copy
import functools
import sys
from weakref import WeakValueDictionary

from .base import BaseNodeManager
from . import utils as _utils
from .const import DEFAULT_ROOT_NODE_ID
from .operation import OperationCollection


class Node(object):
    __slots__ = ["wf", "raw", "parent", "_context", "__weakref__"]

    def __init__(self, projectid=None, context=None,
                 last_modified=0, name="", children=[],
                 description="", completed_at=None, shared=None,
                 parent=None):

        if projectid is None:
            projectid = self.generate_uuid()

        self.parent = parent
        self._context = context

        if isinstance(projectid, dict):
            self.raw = projectid
        else:
            assert not children or \
                all(isinstance(node, dict) for node in children)

            self.raw = dict(
                id=projectid,  # UUID-like str or DEFAULT_ROOT_NODE_ID("None")
                lm=last_modified,  # Last modified by minute (- @joined)
                nm=name,  # Name
                ch=children,  # Children
                no=description,  # Description
                cp=completed_at,  # Last complete by minute (- @joined or None)
                shared=shared,  # Shared infomation
            )

    @property
    def projectid(self):
        return self.raw.get('id')

    @property
    def last_modified(self):
        return self.raw.get('lm')

    @property
    def name(self):
        return self.raw.get('nm')

    @property
    def description(self):
        return self.raw.get('no')

    @property
    def completed_at(self):
        return self.raw.get('cp')

    @property
    def shared(self):
        return self.raw.get('shared')

    def create(self, *args, **kwargs):
        return self._context.project.pm.wf.create(self, *args, **kwargs)

    def edit(self, *args, **kwargs):
        return self._context.project.pm.wf.edit(self, *args, **kwargs)

    def complete(self, *args, **kwargs):
        return self._context.project.pm.wf.complete(self, *args, **kwargs)

    def uncomplete(self, *args, **kwargs):
        return self._context.project.pm.wf.uncomplete(self, *args, **kwargs)

    def delete(self, *args, **kwargs):
        return self._context.project.pm.wf.delete(self, *args, **kwargs)

    def search(self, *args, **kwargs):
        return self._context.project.pm.wf.search(self, *args, **kwargs)

    @property
    def is_completed(self):
        return bool(self.completed_at)

    def __repr__(self):
        return "<{clsname}({projectid!r})>".format(
            clsname=type(self).__name__,
            projectid=self.projectid,
        )

    def __str__(self):
        completed = ", cp={!r}".format(self.completed_at) \
            if self.completed_at is not None else ""
        shared = ", shared={!r}".format(self.shared) \
            if self.shared else ""

        return "{clsname}(projectid={projectid!r}, "
        "last_modified={last_modified!r}, "
        "name={name!r}, len(self)={length!r}, description={description!r}"
        "{_completed_at}{_shared})".format(
            clsname=type(self).__name__,
            projectid=self.projectid,
            last_modified=self.last_modified,
            name=self.name,
            length=len(self),
            description=self.description,
            _completed_at=completed,
            _shared=shared,
        )

    def __bool__(self):
        return len(self) > 0

    def __len__(self):
        return len(self.raw.get('ch', []))

    def __contains__(self, item):
        childs = self.raw.get('ch')
        if childs is None:
            return False

        if isinstance(item, Node):
            item = item.raw

        return item in childs

    def __iter__(self):
        for raw_child in self.raw.get('ch', []):
            yield type(self)(raw_child, context=self._context, parent=self)

    @property
    def children(self):
        return list(self)

    def __getitem__(self, item):
        return self.children[item]

    def _insert(self, index, node):
        self.raw.setdefault('ch', []).insert(index, node)

    def walk(self):
        children = self.children
        yield self, children

        for child in children:
            for x in child.walk():
                yield x

    def fastwalk(self):
        yield self

        for child in self:
            for x in child.fastwalk():
                yield x

    def pretty_print(self, stream=None, indent=0):
        if stream is None:
            stream = sys.stdout

        INDENT_SIZE = 2

        def p(*args):
            print(" " * indent + " ".join(args), file=stream)

        is_empty_root = \
            self.projectid == DEFAULT_ROOT_NODE_ID \
            and not self.name \
            and indent == 0
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
            child.pretty_print(indent=indent)

    def to_json(self):
        return copy.deepcopy(self.raw)

    def __eq__(self, other):
        return self.raw == other.raw

    @classmethod
    def from_void(cls, uuid=None, project=None):
        return cls(uuid or cls.generate_uuid(), project=project)

    generate_uuid = staticmethod(_utils.generate_uuid)


class WeakNode(Node):
    __slots__ = []

    # virtual attribute
    _wf = NotImplemented
    # _project?

    def __getattr__(self, item):
        if not item.startswith("_") and item in dir(OperationCollection):
            return functools.partial(
                getattr(self._context.workflowy, item),
                self
            )

        raise AttributeError(item)

    @Node.name.setter
    def name(self, name):
        self.edit(name, None)

    @Node.description.setter
    def description(self, description):
        self.edit(None, description)

    @Node.is_completed.setter
    def is_completed(self, is_completed):
        if is_completed:
            self.complete()
        else:
            self.uncomplete()

    @property
    def completed_at(self):
        # TODO: convert wf's timestamp to py's timestamp
        def convert(x):
            return x

        return convert(self.completed_at)


class NodeManager(BaseNodeManager):
    def __init__(self, project):
        super().__init__()
        # XXX [!] cycle reference
        self.project = project
        self.data = WeakValueDictionary()
        self.root = None
        self.cache = {}

    def __contains__(self, item):
        if isinstance(item, Node):
            item = item.projectid

        return item in self.cache

    def __getitem__(self, projectid):
        return self.node_from_raw(self.cache[projectid])

    def update_root(self, root_project, root_project_children):
        self.root = self.new_root_node(root_project, root_project_children)
        cache = self.cache

        def _update_child(raw):
            assert "id" in raw
            projectid = raw.get('id')

            cache[projectid] = raw

            ch = raw.get("ch")
            if ch is None:
                return

            for child in ch:
                child['_p'] = projectid
                _update_child(child)

        _update_child(self.root.raw)

    def new_root_node(self, root_project, root_project_children):
        # XXX [!] project is Project, root_project is root node. ?!
        if root_project is None:
            root_project = dict(id=DEFAULT_ROOT_NODE_ID)
        else:
            root_project.update(id=DEFAULT_ROOT_NODE_ID)
            # in shared mode,
            # root will have uuid -(replace)> DEFAULT_ROOT_NODE_ID

        root_project.update(ch=root_project_children)
        root = self.node_from_raw(root_project)
        return root

    def new_void_node(self, parent):
        return Node(context=self, parent=parent)

    def node_from_raw(self, raw):
        return Node(raw, context=self)

    def _walk(self, raw=None):
        if raw is None:
            raw = self.root.raw

        yield raw

        ch = raw.get("ch")
        if ch is not None:
            walk = self._walk
            for child in ch:
                yield from walk(child)

    def pretty_print(self):
        return self.root.pretty_print
