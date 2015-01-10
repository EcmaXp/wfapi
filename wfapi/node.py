# -*- coding: utf-8 -*-
import copy
import sys
from . import utils as _utils
from .settings import DEFAULT_ROOT_NODE_ID


def _raise_found_node_parent(self, node):
    raise WFNodeError("Already parent found.")

class WFRawNode():
    # TODO: add 'as' attribute for embbedded node!
    # FORMAT IS {"as":"hBYC5FQsDC","lm":2044727,"id":"c1e46ee6-53b1-4999-b65b-f11131afbaa0","nm":""}
    # MEAN MUST GIVE wf argument for new_node! OMG!!!

    __slots__  = ["id", "lm", "nm", "ch", "no", "cp", "shared", "parent"]
    default_value = dict(lm=0, nm="", ch=None, no="", cp=None, shared=None, parent=None)

    def __setattr__(self, key, value):
        alter_key = "set_{}".format(key)
        if hasattr(self, alter_key):
            getattr(self, alter_key)(value)
        else:
            super().__setattr__(key, value)

    @classmethod
    def from_vaild_json(cls, info):
        assert isinstance(info, dict)
        self = cls()
        value = cls.default_value.copy()
        value.update(info)

        setattr_node = super(cls, self).__setattr__
        for k, v in value.items():
            setattr_node(k, v)

        return self

    @classmethod
    def from_node_init(cls, node, info):
        assert isinstance(info, dict)

        self = cls()
        node_cls = type(self)
        slot_map = node_cls.slot_map
        filter_map = node_cls.filter_map

        setattr_node = super(cls, self).__setattr__
        for k, v in info.items():
            k = slot_map.get(k, k)
            if k in filter_map:
                getattr(node, "set_{}".format(k))(v)
            else:
                setattr_node(k, v)

    def to_json(self):
        info = {}
        for k in self.__slots__:
            v = getattr(self, k)
            info[k] = v

        del info["parent"]
        return info

    def set_projectid(self, projectid):
        if isinstance(projectid, uuid.UUID):
            projectid = str(projectid)

        self.id = projectid

    def set_last_modified(self, last_modified):
        assert isinstance(last_modified, int)
        self.lm = last_modified

    def set_name(self, name):
        self.nm = name

    def set_children(self, childs):
        if hasattr(self, "ch"):
            # if already ch is exists, how to work?
            raise NotImplementedError
        elif childs is None:
            self.ch = None
        else:
            ch = self.ch = []
            for child in childs:
                if child.parent is not None:
                    _raise_found_node_parent(node)

                child.parent = self
                ch.append(child)

    def set_description(self, description):
        assert isinstance(description, str)
        self.no = description

    def set_completed_at(self, at):
        if at is None:
            self.cp = None
        else:
            assert isinstance(at, (int, float))
            self.cp = int(at)

    # XXX RuntimeError: maximum recursion depth exceeded
    #def set_shared(self, shared):
    #    # TODO: check isinstance with shared
    #    self.shared = shared
    #def set_parent(self, parent):
    #    assert isinstance(parent, WFNode) or parent is None, parent
    #    self.parent = parent


class WFNode():
    __slots__  = ["raw", "__weakref__"]

    # TODO: how to control slot info?
    slots = ["projectid", "last_modified", "name", "children", "description", "completed_at", "shared", "parent"]
    virtual_slots = ["parentid", "is_completed"]

    slot_map = dict(
        id="projectid",
        lm="last_modified",
        nm="name",
        ch="children",
        no="description",
        cp="completed_at",
        shared="shared",
        parent="parent",
    )

    def __init__(self, projectid, last_modified=0, name="", children=None, \
                 description="", completed_at=None, shared=None, parent=None):
        if isinstance(projectid, WFRawNode):
            self.raw = projectid
        else:
            self.raw = WFRawNode.from_node_init(self, dict(
                id=projectid, # UUID-like str or DEFAULT_ROOT_NODE_ID("None")
                lm=last_modified, # Last modified by minute (- @joined)
                nm=name, # Name
                ch=children, # Children
                no=description, # Description
                cp=completed_at, # Last complete by minuted (- @joined or None)
                shared=shared, # Shared infomation
                parent=parent, # Parent node (or None)
            ))

    @property
    def projectid(self):
        return self.raw.id

    @property
    def last_modified(self):
        return self.raw.lm

    @property
    def name(self):
        return self.raw.nm

    @property
    def description(self):
        return self.raw.no

    @property
    def completed_at(self):
        return self.raw.cp

    @property
    def shared(self):
        return self.raw.shared

    @property
    def parent(self):
        return self.raw.parent

    @property
    def children(self):
        ch = self.raw.ch
        if ch is None:
            ch = self.raw.ch = []

        return ch

    @property
    def parentid(self):
        return self.parent.projectid

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

        return ("{clsname}(projectid={id!r}, last_modified={last_modified!r}, "
            "name={name!r}, children={children!r}, description={description!r}"
            "{_completed_at}{_shared}, parent={parent})").format(
            clsname = type(self).__name__,
            projectid = self.projectid,
            last_modified = self.last_modified,
            name = self.name,
            children = self.children,
            description = self.description,
            _completed_at = vif(raw.cp, ", cp={!r}".format(raw.cp), ""),
            _shared = vif(raw.shared, ", shared={!r}".format(raw.shared), ""),
            parent = vif(raw.parent, "...", None),
        )

    def copy(self):
        # TODO: support fast copy by copy module?
        return type(self).from_json(self.to_json(), parent=self.parent)

    def insert(self, index, node):
        if node.parent is not None:
            _raise_found_node_parent(node)

        self.children.insert(index, node)
        node.parent = self

    def __bool__(self):
        return len(self) > 0

    def __len__(self):
        return len(self.raw.ch) if self.raw.ch else 0

    def __contains__(self, item):
        if self.raw.ch is None:
            return False

        return item in self.children

    def __iter__(self):
        ch = self.raw.ch
        if ch is None:
            return iter(())

        return iter(ch)

    def __getitem__(self, item):
        ch = self.raw.ch
        if not isinstance(item, slice):
            if ch is None:
                raise IndexError(item)

        return ch[item]

    def pretty_print(self, *, stream=None, indent=0):
        if stream is None:
            stream = sys.stdout

        INDENT_SIZE = 2
        p = lambda *args: print(" "*indent + " ".join(args), file=stream)

        is_empty_root = self.projectid == DEFAULT_ROOT_NODE_ID and not self.name and indent == 0
        if is_empty_root:
            p("[*]", "Home")
        else:
            p("[%s]" % (self.raw.cp and "-" or " ",), self.name, "{%s} " % self.projectid)

        for line in self.raw.no.splitlines():
            p(line)

        indent += INDENT_SIZE
        for child in self:
            child.pretty_print(indent=indent)

    @classmethod
    def from_json(cls, data, parent=None):
        data = data.copy()

        ch = data.get("ch")
        if ch is not None:
            new_ch = []
            for child in ch:
                child = cls.from_json(child)
                new_ch.append(child)
            data["ch"] = new_ch

        info = WFRawNode.from_vaild_json(data)
        info.parent = parent
        return cls(info)

    def to_json(self):
        return self.raw.to_json()

    @classmethod
    def from_void(cls, uuid=None):
        return cls(uuid or cls.generate_uuid())

    generate_uuid = staticmethod(_utils.generate_uuid)


class WF_WeakNode(WFNode):
    __slots__ = []
    
    # virtual attribute: _wf

    def __getattr__(self, item):
        if not item.startswith("_") and item in dir(WFOperationCollection):
            return functools.partial(getattr(self._wf, item), self)

        raise AttributeError(item)

    @WFNode.name.setter
    def name(self, name):
        self.edit(name, None)
        self.raw.nm = name

    @WFNode.description.setter
    def description(self, description):
        self.edit(None, description)
        self.raw.no = description

    @property
    def completed_at(self):
        # TODO: convert wf's timestamp to py's timestamp
        convert = lambda x: x
        return convert(self.raw.cp)

    @completed_at.setter
    def completed_at(self, completed_at):
        completed_at = self.complete(completed_at)
        self.raw.cp = completed_at

    @WFNode.completed_at.setter
    def is_completed(self, is_completed):
        if is_completed:
            self.raw.cp = self.complete()
        else:
            self.uncomplete()
            self.raw.cp = None

    # TODO: allow shared modify?
    #@property
    #def shared(self):
    #    return self.raw.shared

#class WFOperationEngine():
#    "Use yield for operation, and undo?"
#    pass