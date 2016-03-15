# -*- coding: utf-8 -*-
import functools
import sys
from ..operation import OperationCollection
from .. import utils as _utils
from ..const import DEFAULT_ROOT_NODE_ID
from ..error import WFNodeError


def _raise_found_node_parent(self, node):
    raise WFNodeError("Already parent found.")


class Node():
    __slots__ = ["raw", "_parentid", "__weakref__"]

    def __init__(self, projectid=None, parentid=None, last_modified=0, name="", children=(),
                 description="", completed_at=None, shared=None, parent=None):

        if projectid is None:
            projectid = self.generate_uuid()

        if isinstance(projectid, dict):
            self.raw = projectid
            self._parentid = parentid
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
        return self.raw['id']

    @property
    def last_modified(self):
        return self.raw['lm']

    @property
    def name(self):
        return self.raw['nm']

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
    def children(self):
        # TODO: not allow edit children without API?
        return tuple(self.raw.setdefault('ch', []))

    @property
    def parentid(self):
        # TODO: _projectid can be None or Not assigned! (WORRY)
        return self._parentid

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
            "name={name!r}, children={children!r}, description={description!r}"
            "{_completed_at}{_shared})").format(
            clsname = type(self).__name__,
            projectid = self.projectid,
            last_modified = self.last_modified,
            name = self.name,
            children = self.children,
            description = self.description,
            _completed_at = vif(raw.get('cp'), ", cp={!r}".format(raw['cp']), ""),
            _shared = vif(raw.get('shared'), ", shared={!r}".format(raw['shared']), ""),
        )

    def __bool__(self):
        return len(self) > 0

    def __len__(self):
        return len(self.raw.get('ch', ()))

    def __contains__(self, item):
        if self.raw.get('ch') is None:
            return False

        return item in self.children

    def __iter__(self):
        ch = self.raw.get('ch', ())
        return map(type(self), ch)

    def __getitem__(self, item):
        ch = self.raw.get('ch')
        if not isinstance(item, slice):
            if ch is None:
                raise IndexError(item)

        return type(self)(ch[item])

    if 0:
        def copy(self):
            # TODO: implement this
            raise NotImplementedError

    def _insert(self, index, node):
        self.children
        self.raw['ch'].insert(index, node)

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
        return dict(self.raw)

    @classmethod
    def from_void(cls, uuid=None, project=None):
        return cls(uuid or cls.generate_uuid(), project=project)

    generate_uuid = staticmethod(_utils.generate_uuid)


class _WeakNode(Node):
    __slots__ = []
    
    # virtual attribute
    _wf = NotImplemented

    def __getattr__(self, item):
        if not item.startswith("_") and item in dir(OperationCollection):
            return functools.partial(getattr(self._wf, item), self)

        raise AttributeError(item)

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
        return convert(self.raw['cp'])

    @completed_at.setter
    def completed_at(self, completed_at):
        completed_at = self.complete(completed_at)
        self.raw['cp'] = completed_at

    @Node.completed_at.setter
    def is_completed(self, is_completed):
        if is_completed:
            self.raw['cp'] = self.complete()
        else:
            self.uncomplete()
            self.raw['cp'] = None

#class OperationEngine():
#    "Use yield for operation, and undo?"
#    pass
