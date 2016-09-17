# -*- coding: utf-8 -*-
import copy
import sys

from .const import DEFAULT_ROOT_NODE_ID
from .context import WFContext


class Node(object):
    __slots__ = ["raw", "context", "__weakref__"]

    def __init__(self, context:WFContext, raw):
        self.context = context
        self.raw = raw

    @property
    def parent(self):
        raise NotImplementedError

    @property
    def projectid(self):
        return self.raw.get('id')

    @property
    def last_modified(self):
        return self.raw.get('lm')

    @property
    def last_modified_b(self):
        # TODO: lmb support (lm extend) and change name
        return self.raw.get('lmb')

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
        return self.context.create(self, *args, **kwargs)

    def edit(self, *args, **kwargs):
        return self.context.edit(self, *args, **kwargs)

    def complete(self, *args, **kwargs):
        return self.context.complete(self, *args, **kwargs)

    def uncomplete(self):
        return self.context.uncomplete(self)

    def delete(self):
        return self.context.delete(self)

    def search(self, *args, **kwargs):
        return self.context.search(self, *args, **kwargs)

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

        return ("{clsname}(projectid={projectid!r}, "
        "last_modified={last_modified!r}, "
        "name={name!r}, len(self)={length!r}, description={description!r}"
        "{_completed_at}{_shared})").format(
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
            yield type(self)(self.context, raw_child)

    @property
    def children(self):
        return list(self)

    def __getitem__(self, item):
        return self.children[item]

    def __delitem__(self, item):
        self[item].delete()

    # TODO: delitem?

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
            print(" " * indent + " ".join(map(str, args)), file=stream)

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

    @name.setter
    def name(self, name):
        self.edit(name, None)

    @description.setter
    def description(self, description):
        self.edit(None, description)

    @is_completed.setter
    def is_completed(self, is_completed):
        if is_completed:
            self.complete()
        else:
            self.uncomplete()

