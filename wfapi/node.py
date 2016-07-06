# -*- coding: utf-8 -*-
import copy
import functools
import sys
from weakref import WeakValueDictionary

from .base import BaseNodeManager
from . import utils as _utils
from .const import DEFAULT_ROOT_NODE_ID
from .operation import OperationCollection


class Node():
    __slots__ = ["raw", "_parent", "_context", "__weakref__"]

    def __init__(self, projectid=None, parent=None, context=None, *, last_modified=0, name="", children=(),
                 description="", completed_at=None, shared=None):

        if projectid is None:
            projectid = self.generate_uuid()

        if context is None:
            context = context

        self._parent = parent
        self._context = context

        if isinstance(projectid, dict):
            self.raw = projectid
        else:
            assert not children or all(isinstance(node, dict) for node in children)

            self.raw = dict(
                id=projectid, # UUID-like str or DEFAULT_ROOT_NODE_ID("None")
                lm=last_modified, # Last modified by minute (- @joined)
                nm=name, # Name
                ch=children, # Children
                no=description, # Description
                cp=completed_at, # Last complete by minuted (- @joined or None)
                shared=shared, # Shared infomation
            )

    @property
    def projectid(self):
        """

        :return:UUID-like string
        """
        return self.raw['id']

    @property
    def parent(self):
        return self._parent

    @property
    def last_modified(self):
        return self.raw['lm']

    @property
    def name(self):
        return self.raw.get('nm')

    @property
    def description(self):
        return self.raw['no']

    @property
    def completed_at(self):
        return self.raw['cp']

    @property
    def shared(self):
        return self.raw['shared']

    @property
    def is_completed(self):
        return self.completed_at is not None

    def __repr__(self):
        return "<{clsname}({projectid!r})>".format(
            clsname=type(self).__name__,
            projectid=self.projectid,
        )

    def __str__(self):
        vif = lambda obj, t, f: t if obj is not None else f
        raw = self.raw

        return ("{clsname}(projectid={projectid!r}, last_modified={last_modified!r}, "
            "name={name!r}, len(self)={length!r}, description={description!r}"
            "{_completed_at}{_shared})").format(
            clsname = type(self).__name__,
            projectid = self.projectid,
            last_modified = self.last_modified,
            name = self.name,
            length = len(self),
            description = self.description,
            _completed_at = vif(raw.get('cp'), ", cp={!r}".format(raw['cp']), ""),
            _shared = vif(raw.get('shared'), ", shared={!r}".format(raw['shared']), ""),
        )

    def __bool__(self):
        return len(self) > 0

    def __len__(self):
        return len(self.raw.get('ch', ()))

    def __contains__(self, item):
        childs = self.raw.get('ch')
        if childs is None:
            return False

        if isinstance(item, Node):
            item = item.raw

        return item in childs

    def _get_child(self, raw):
        return type(self)(raw, parent=self)

    def __iter__(self):
        projectid = self.projectid
        ch = self.raw.get('ch', ())
        return map(self._get_child, ch)

    def __getitem__(self, item):
        ch = self.raw.get('ch')
        if not isinstance(item, slice):
            if ch is None:
                raise IndexError(item)

        return self._get_child(ch[item])

    def _insert(self, index, node):
        self.raw.setdefault('ch', []).insert(index, node)

    def walk(self):
        childs = list(self)
        yield self, childs

        for child in childs:
            for x in child.walk():
                yield x

    def fastwalk(self):
        yield self

        for child in self:
            for x in child.fastwalk():
                yield x

    def pretty_print(self, *, stream=None, indent=0):
        if stream is None:
            stream = sys.stdout

        INDENT_SIZE = 2
        p = lambda *args: print(" "*indent + " ".join(args), file=stream)

        is_empty_root = self.projectid == DEFAULT_ROOT_NODE_ID and not self.name and indent == 0
        if is_empty_root:
            p("[*]", "Home")
        else:
            p("[%s]" % (self.raw.get('cp') and "-" or " ",), self.name, "{%s} " % self.projectid)

        for line in self.raw.get('no', "").splitlines():
            p(line)

        indent += INDENT_SIZE
        for child in self:
            child.pretty_print(indent=indent)

    def to_json(self):
        return copy.deepcopy(self.raw)

    @classmethod
    def from_void(cls, uuid=None, project=None):
        return cls(uuid or cls.generate_uuid(), project=project)

    generate_uuid = staticmethod(_utils.generate_uuid)

<<<<<<< HEAD
=======

class WeakNode(Node):
    __slots__ = []

    # virtual attribute
    _wf = NotImplemented
    # _project?

>>>>>>> origin/master
    def __getattr__(self, item):
        if not item.startswith("_") and item in dir(OperationCollection):
            return functools.partial(getattr(self._context.workflowy, item), self)

        raise AttributeError(item)

    @name.setter
    def name(self, name):
        self.edit(name, None)

    @description.setter
    def description(self, description):
        self.edit(None, description)

    @property
    def is_completed(self):
        return bool(self.completed_at)

    @is_completed.setter
    def is_completed(self, is_completed):
        if is_completed:
            self.complete()
        else:
            self.uncomplete()

    @property
    def completed_at(self):
        # TODO: convert wf's timestamp to py's timestamp
        convert = lambda x: x
        return convert(self.raw['cp'])


class NodeManager(BaseNodeManager):
    NODE_CLASS = Node

    def __init__(self, project):
        super().__init__()
        # XXX [!] cycle reference
        self.project = project
        self.data = WeakValueDictionary()
        self.root = None
        self.cache = {}

    def __contains__(self, item):
        return item in self.cache

    def __getitem__(self, item):
        return self.cache[item]

    def update_root(self, root_project, root_project_children):
        self.root = self.new_root_node(root_project, root_project_children)

        cache = self.cache
        for raw in self._walk():
            cache[raw['id']] = raw

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

    def _walk(self, raw=None):
        if raw is None:
            raw = self.root.raw

        yield raw

        ch = raw.get("ch")
        if ch is not None:
            walk = self._walk
            for child in ch:
                yield from walk(child)

    @property
    def pretty_print(self):
        return self.root.pretty_print


