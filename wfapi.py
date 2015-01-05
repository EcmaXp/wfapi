#!/usr/bin/env python3
"""Workflowy Python3 API v{__version__}
{__project_url__} By {__author__}

Workflowy: Organize your brain.
But did you think about what if workflowy can access by API?

This module are provide many
"""

__project_url__ = "http://github.com/sigsrv/wfapi"
__author__ = "sigsrv (sigsrv@sigsrv.net)"

__version__ = "0.1.17-alpha"
# based on github commit count in 0.1
# https://www.python.org/dev/peps/pep-0396/
# http://semver.org/lang/ko/

__doc__ = __doc__.format_map(globals())

import copy
import functools
import json
import logging
import os
import random
import re
import string
import sys
import threading
import time
import uuid
import warnings
import weakref
from contextlib import closing, contextmanager
from http.client import HTTPConnection, HTTPSConnection
from http.cookiejar import Cookie, CookieJar
from pprint import pprint
from urllib.error import HTTPError
from urllib.parse import urljoin, urlencode, urlparse
from urllib.request import build_opener, HTTPCookieProcessor, Request, \
    HTTPErrorProcessor
from weakref import WeakValueDictionary

__all__ = ["Workflowy", "WeakWorkflowy"]

# TODO: Add more debug option and use logging module.
DETAIL_DEBUG = False

DEFAULT_WORKFLOWY_URL = "https://workflowy.com/"
DEFAULT_ROOT_NODE_ID = "None"

FEATURE_XXX_PRO_USER = False # it does nothing. just define more empty classes.
FEATURE_USE_FAST_REQUEST = True

DEFAULT_WORKFLOWY_CLIENT_VERSION = 14 # @ 2014-12-22
DEFAULT_WORKFLOWY_MONTH_QUOTA = 250


if DETAIL_DEBUG:
    # for debug.
    HTTPConnection.debuglevel = 1
    #import http.cookiejar
    #http.cookiejar._debug = print


@contextmanager
def debug_helper_with_json(info):
    if __debug__:
        try:
            yield
        except Exception:
            print()
            print("[ERROR] Error Raised!")
            # TODO?
            pprint(info)
            raise
    else:
        yield


class attrdict(dict):
    def __init__(self, *args, **kwargs):
          super().__init__(*args, **kwargs)
          self.__dict__ = self
          
    def steal(self, obj, key):
        value = obj[key]
        del obj[key]
        self.update(value)


class BaseBrowser():
    def __init__(self, base_url):
        self.base_url = base_url
        
    def open(self, url, *, _raw=False, **kwargs):
        raise NotImplementedError

    def set_cookie(self, name, value):
        raise NotImplementedError

    def __getitem__(self, url):
        return functools.partial(self.open, url)

    def reset(self):
        # TODO: support reset cookies?
        pass


class BuiltinBrowser(BaseBrowser):
    def __init__(self, base_url):
        super().__init__(base_url)
        self.cookie_jar = CookieJar()
        self.opener = build_opener(HTTPCookieProcessor(self.cookie_jar))

    def open(self, url, *, _raw=False, **kwargs):
        full_url = urljoin(self.base_url, url)
        data = urlencode(kwargs).encode()
        headers = {
            "Content-Type" : "application/x-www-form-urlencoded",
        }

        req = Request(full_url, data, headers)
        res = self.opener.open(req)

        with closing(res) as fp:
            content = fp.read()

        content = content.decode()

        if not _raw:
            # TODO: must not raise 404 error
            content = json.loads(content)

        return res, content

    def set_cookie(self, name, value):
        url = urlparse(self.base_url)
        cookie = Cookie(
            version=0,
            name=name,
            value=value,
            port=None,
            port_specified=False,
            domain=url.netloc,
            domain_specified=False,
            domain_initial_dot=False,
            path=url.path,
            path_specified=True,
            secure=False,
            expires=sys.maxsize,
            discard=False,
            comment=None,
            comment_url=None,
            rest={},
            rfc2109=False,
        )

        self.cookie_jar.set_cookie(cookie)


class FastBrowser(BaseBrowser):
    def __init__(self, base_url):
        super().__init__(base_url)
        parsed = urlparse(base_url)
        
        conn_class = {
            "http" : HTTPConnection,
            "https" : HTTPSConnection,
        }.get(parsed.scheme)

        assert conn_class is not None
        
        host, _, port = parsed.netloc.partition(":")
        port = int(port) if port else None
        
        self.addr = host, port
        self.conn_class = conn_class
        self.cookie_jar = CookieJar()
        self._safe = threading.local()

        self._not_opener = build_opener()
        
        for handler in self._not_opener.handlers:
            if isinstance(handler, HTTPErrorProcessor):
                self.error_handler = handler
                break
        else:
            raise RuntimeEror("Not exists HTTPErrorProcessor in urlopener")

    def get_connection(self):
        try:
            conn = self._safe.conn
        except AttributeError:
            conn = self.conn_class(*self.addr)
            self._safe.conn = conn
        
        return conn
        
    def open(self, url, *, _raw=False, **kwargs):
        full_url = urljoin(self.base_url, url)
        
        data = None
        if kwargs:
            data = urlencode(kwargs).encode()
        
        method = 'POST' if data else 'GET'
        
        headers = {
            "Content-Type" : "application/x-www-form-urlencoded",
            "Connection" : "keep-alive",
        }
        
        conn = self.get_connection()
        cookiejar = self.cookie_jar

        req = Request(full_url, data, headers)
        cookiejar.add_cookie_header(req)
        headers = req.headers
        headers.update(req.unredirected_hdrs)
        
        conn.request(method, full_url, data, headers)
        
        res = conn.getresponse()
        cookiejar.extract_cookies(res, req)
        
        # TODO: find reason why res.msg are equal with res.headers
        res.msg = res.reason # FAILBACK
        self.error_handler.http_response(req, res)

        with closing(res) as fp:
            content = fp.read()

        content = content.decode()
        
        if not _raw:
            content = json.loads(content)
        
        return res, content
    
    set_cookie = BuiltinBrowser.set_cookie


Browser = BuiltinBrowser
if FEATURE_USE_FAST_REQUEST:
    Browser = FastBrowser


class WFError(Exception):
    pass


class WFRuntimeError(Exception):
    pass


class WFLoginError(WFError):
    pass


class WFNodeError(WFError):
    pass


class WFOverflowError(WFError, OverflowError):
    pass



class WFBaseSharedInfo():
    pass


class WFURLSharedInfo():
    pass


class _WFNodeInfo():
    __slots__  = ["id", "lm", "nm", "ch", "no", "cp", "shared", "parent"]
    default_value = dict(lm=0, nm="", ch=None, no="", cp=None, shared=None, parent=None)
    _MAGIC_INIT = object()

    def __init__(self, magic=None):
        if magic is not self._MAGIC_INIT:
            raise RuntimeError("it must not inited by other code")

    @classmethod
    def from_vaild_json(cls, info):
        assert isinstance(info, dict)
        self = cls(cls._MAGIC_INIT)
        value = cls.default_value.copy()
        value.update(info)

        for k, v in value.items():
            setattr(self, k, v)

        return self

    def from_node_init(self, node, info):
        assert isinstance(info, dict)

        slot_map = WFNode.slot_map
        for k, v in info.items():
            setattr(node, slot_map.get(k), v)

    def to_json(self):
        info = {}
        for k in self.__slots__:
            v = getattr(self, k)
            info[k] = v

        del info["parent"]
        return info


class WFNode():
    __slots__  = ["info", "__weakref__"]

    # TODO: how to control slot info?
    slots = ["projectid", "last_modified", "name", "children", "description", "completed_at", "shared", "parent"]
    virtual_slots = ["parentid", "completed"]

    slot_map = dict(
        id = "projectid",
        lm = "last_modified",
        nm = "name",
        ch = "children",
        no = "description",
        cp = "completed_at",
        shared = "shared",
        parent = "parent",
    )

    def __init__(self, id:str, lm=0, nm="", ch=None, no="", cp=None, shared=None, parent=None):
        if isinstance(id, _WFNodeInfo):
            self.info = id
        else:
            self.info = _WFNodeInfo(_WFNodeInfo._MAGIC_INIT)
            self.info.from_node_init(self, dict(
                id = id, # UUID or "None"(DEFAULT_ROOT_NODE_ID)
                lm = lm, # Last modified time
                nm = nm, # name
                ch = ch, # children
                no = no, # description
                cp = cp, # Last completed time (or None)
                shared = shared, # shared infomation
                parent = parent, # parent node (or None)
            ))

    def __getitem__(self, name):
        alter_name = self.slot_map.get(name)
        if alter_name is not None:
            return getattr(self, alter_name)

    @property
    def projectid(self):
        return self.info.id

    @projectid.setter
    def projectid(self, projectid):
        if isinstance(projectid, uuid.UUID):
            projectid = str(projectid)

        self.info.id = projectid

    @property
    def parentid(self):
        return self.parent.projectid

    @property
    def last_modified(self):
        assert isinstance(self.info.lm, int)
        return self.info.lm

    @last_modified.setter
    def last_modified(self, lm):
        assert isinstance(lm, int)
        self.info.lm = lm

    @property
    def name(self):
        return self.info.nm

    @name.setter
    def name(self, name):
        self.info.nm = name

    @property
    def children(self):
        ch = self.info.ch
        if ch is None:
            ch = self.info.ch = []

        return ch

    @children.setter
    def children(self, childs):
        if hasattr(self.info, "ch"):
            # if already ch is exists, how to work?
            raise NotImplementedError
        elif childs is None:
            self.info.ch = None
        else:
            ch = self.info.ch = []
            for child in childs:
                if child.parent is not None:
                    self._raise_found_node_parent(node)

                child.parent = self
                ch.append(child)

    @children.deleter
    def children(self):
        self.info.ch = None

    @property
    def description(self):
        return self.info.no

    @description.setter
    def description(self, description):
        assert isinstance(description, str)
        self.info.no = description

    @description.deleter
    def description(self):
        self.info.no = None

    @property
    def completed_at(self):
        return self.info.cp

    @completed_at.setter
    def completed_at(self, at):
        if at is None:
            self.info.cp = None
        else:
            assert isinstance(at, (int, float))
            self.info.cp = int(at)

    @property
    def completed(self):
        return self.completed_at is not None

    @property
    def shared(self):
        return self.info.shared

    @shared.setter
    def shared(self, shared):
        self.info.shared = shared

    @shared.deleter
    def shared(self):
        self.info.shared = None

    @property
    def parent(self):
        return self.info.parent

    @parent.setter
    def parent(self, parent):
        assert isinstance(parent, WFNode) or parent is None, parent
        self.info.parent = parent

    @parent.deleter
    def parent(self):
        self.info.parent = None

    def __repr__(self):
        return "<{clsname}({id!r})>".format(clsname = type(self).__name__, id = self.projectid)

    def __str__(self):
        return "{clsname}(id={id!r}, lm={lm!r}, nm={nm!r}, ch={ch!r}, no={no!r}, cp={cp!r}{_shared}, parent={parent!r})".format(
            clsname = type(self).__name__,
            id = self.projectid,
            lm = self.last_modified,
            nm = self.name,
            ch = self.children,
            no = self.info.no,
            cp = self.info.cp,
            _shared = ", shared={!r}".format(self.info.shared) if self.info.shared is not None else "",
            parent = self.info.parent,
        )

    def copy(self):
        return copy.copy(self)

    def _raise_found_node_parent(self, node):
        raise WFNodeError("Already parent found.")
        # TODO: remove bad english. :(

    def insert(self, index, node):
        if node.parent is not None:
            self._raise_found_node_parent(node)

        self.children.insert(index, node)
        node.parent = self

    def __bool__(self):
        return len(self) > 0

    def __len__(self):
        return len(self.info.ch) if self.info.ch else 0

    def __contains__(self, item):
        if self.info.ch is None:
            return False

        return item in self.children

    def __iter__(self):
        ch = self.info.ch
        if ch is None:
            return iter(())

        return iter(ch)

    def __getitem__(self, item):
        ch = self.info.ch
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
            p("[%s]" % (self.info.cp and "-" or " ",), self.name, "{%s} " % self.projectid)

        for line in self.info.no.splitlines():
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

        info = _WFNodeInfo.from_vaild_json(data)
        info.parent = parent
        return cls(info)

    def to_json(self):
        return self.info.to_json()

    @classmethod
    def from_void(cls, uuid=None):
        return cls(uuid or cls.generate_uuid())

    @staticmethod
    def generate_uuid():
        return str(uuid.UUID(bytes=os.urandom(16)))


class WF_WeakNode(WFNode):
    __slots__ = []

    def __getattr__(self, item):
        if not item.startswith("_") and item in dir(WFOperationCollection):
            return functools.partial(getattr(self._wf, item), self)

        raise AttributeError(item)


#class WFOperationEngine():
#    "Use yield for operation, and undo?"
#    pass



OPERATION_REGISTERED = {}
class WFOperation():
    operation_name = NotImplemented
    _cached = None

    def __init__(self, node):
        if self.operation_name is NotImplemented:
            raise NotImplementedError("operation_name are NotImplemented.")

        self.node = node
        raise NotImplementedError
        # ?

    def __repr__(self):
        # const name?
        return "<WFOperation: %s; %r>" % (self.operation_name, vars(self))

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

    def get_undo_data(self, tr):
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

        OPERATION_REGISTERED[operation_name] = operation

        return operation

register_operation = WFOperation._register


class _WFUnknownOperation(WFOperation):
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
        return "<_WFUnknownOperation: %s; %r>" % (self.operation_name, self.data)

    def pre_operation(self, tr):
        pass

    def post_operation(self, tr):
        # TODO: how to warning?
        warnings.warn("Unknown %s operation detected." % self.operation_name)
        print(self)

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


@register_operation
class WF_EditOperation(WFOperation):
    operation_name = 'edit'

    def __init__(self, node, name=None, description=None):
        self.node = node
        self.name = name
        self.description = description

    def pre_operation(self, tr):
        assert tr.wf.nodemgr.check_exist_node(self.node)

    def post_operation(self, tr):
        node = self.node
        if self.name is not None:
            node.name = self.name

        if self.description is not None:
            node.description = self.description

    @classmethod
    def from_server_operation(cls, tr, node, name=None, description=None):
        return cls(node, name, description)

    def get_operation_data(self, tr):
        return dict(
            projectid = self.node.projectid,
            name = self.name,
            description = self.description,
        )

    def get_undo_data(self, tr):
        return dict(
            previous_name=self.node.name if self.name is not None else None,
            previous_description=self.node.description if self.description is not None else None,
        )


@register_operation
class WF_CreateOperation(WFOperation):
    operation_name = 'create'

    def __init__(self, parent, node, priority):
        self.parent = parent
        self.node = node
        self.priority = priority

    def pre_operation(self, tr):
        assert tr.wf.nodemgr.check_not_exist_node(self.node)

    def post_operation(self, tr):
        self.parent.insert(self.priority, self.node)
        tr.wf.add_node(self.node, update_quota=True)
        # TODO: more good way to management node.

    def get_operation_data(self, tr):
        return dict(
            projectid=self.node.projectid,
            parentid=self.parent.projectid,
            priority=self.priority,
        )

    def get_undo_data(self, tr):
        return {}

    @classmethod
    def prepare_server_operation_json(cls, tr, op):
        return op

    @classmethod
    def from_server_operation(cls, tr, projectid, parentid, priority):
        node = tr.wf.nodemgr.new_void_node(projectid)
        node.last_modified = tr.get_client_timestamp()
        parent = tr.wf[parentid]
        return cls(parent, node, priority)


class _WF_CompleteNodeOperation(WFOperation):
    operation_name = NotImplemented

    def __init__(self, node):
        self.node = node
        self.modified = None
        # modified will auto fill by get_operation_data

    def pre_operation(self, tr):
        assert tr.wf.nodemgr.check_exist_node(self.node)

    def post_operation(self, tr):
        self.node.completed_at

    def get_operation_data(self, tr):
        return dict(
            projectid = self.node.projectid,
        )

    def get_undo_data(self, tr):
        return dict(
            previous_completed=self.node.completed_at if self.node.completed_at is not None else False,
        )

    @classmethod
    def from_server_operation(cls, tr, node):
        return cls(node)


@register_operation
class WF_CompleteOperation(_WF_CompleteNodeOperation):
    operation_name = 'complete'

    def __init__(self, node):
        super().__init__(node)
        self.modified = None

    def pre_operation(self, tr):
        super().pre_operation(tr)
        if self.modified is None:
            self.modified = tr.get_client_timestamp()

    def post_operation(self, tr):
        super().post_operation(tr)
        self.node.completed_at = None


@register_operation
class WF_UncompleteOperation(_WF_CompleteNodeOperation):
    operation_name = 'uncomplete'

    def post_operation(self, tr):
        self.node.completed_at = None


@register_operation
class WF_DeleteOperation(WFOperation):
    operation_name = 'delete'

    def __init__(self, node):
        self.parent = node.parent
        self.node = node
        self.priority = self.parent.children.index(node)
        # TODO: more priority calc safety.

    def pre_operation(self, tr):
        assert tr.wf.nodemgr.check_exist_node(self.node)

    def post_operation(self, tr):
        node = self.node
        if self.parent:
            assert node in self.parent
            self.parent.children.remove(node)

        tr.wf.remove_node(node, recursion_delete=True)

    def get_operation_data(self, tr):
        return dict(
            projectid=self.node.projectid,
        )

    def get_undo_data(self, tr):
        return dict(
            parentid=self.parent.projectid,
            priority=self.priority,
        )


@register_operation
class WF_UndeleteOperation(WFOperation):
    operation_name = 'undelete'

    def __init__(self):
        raise NotImplementedError("Just don't do that. :P")


@register_operation
class WF_MoveOperation(WFOperation):
    operation_name = 'move'

    def __init__(self, parent, node, priority):
        self.parent = parent
        self.node = node
        self.priority = priority

    def pre_operation(self, tr):
        assert tr.wf.nodemgr.check_exist_node(self.node)
        if self.node.parent is None:
            raise WFNodeError("{!r} don't have parent. (possible?)".format(self.node))
        elif self.node not in self.node.parent:
            raise WFNodeError("{!r} not have {!r}".format(self.parent, self.node))

    def post_operation(self, tr):
        self.node.parent.remove(self.node)
        self.node.parent = self.parent
        self.parent.insert(self.priority, self.node)

    def get_operation_data(self, tr):
        return dict(
            projectid=self.node.projectid,
            parentid=self.parent.projectid,
            priority=self.priority,
        )

    def get_undo_data(self, tr):
        previous_priority = None
        if self.node in self.node.parent:
            previous_priority = self.node.parent.ch.index(self.node)

        return dict(
            previous_parentid=self.node.parent.projectid,
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


@register_operation
class WF_ShareOperation(WFOperation):
    operation_name = 'share'

    def __init__(self, node, share_type="url", write_permission=False):
        assert share_type == "url"
        self.node = node
        self.share_type = share_type
        self.write_permission = False

    def post_operation(self, tr):
        self.node.shared = None
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

@register_operation
class WF_UnshareOperation(WFOperation):
    operation_name = 'unshare'

    def __init__(self, node):
        self.node = node

    def pre_operation(self, tr):
        # TODO: should check node are shared?
        pass

    def post_operation(self, tr):
        self.node.shared = None

    def get_operation_data(self, tr):
        return dict(
            projectid=self.node.projectid,
        )

    get_undo_data = WF_ShareOperation.get_undo_data

    @classmethod
    def from_server_operation(cls, tr, node):
        return cls(node)


@register_operation
class WF_BulkCreateOperation(WFOperation):
    operation_name = 'bulk_create'
    NotImplemented

    # This operation does add node at one times.

    def __init__(self, parent, project_trees, starting_priority):
        self.parent = parent
        self.project_trees = project_trees
        self.starting_priority = starting_priority

    def pre_operation(self, tr):
        assert tr.wf.nodemgr.check_not_exist_node(self.project_trees)

    def post_operation(self, tr):
        self.parent.insert(self.starting_priority, self.project_trees)
        tr.wf.add_node(self.project_trees, update_child=True)

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
    def from_server_operation(cls, tr, parent, project_trees, starting_priority):
        project_trees = tr.wf.nodemgr.new_node_from_json(project_trees, parent=parent)
        return cls(parent, project_trees, starting_priority)


@register_operation
class WF_BulkMoveOperation(WFOperation):
    operation_name = 'bulk_move'
    NotImplemented


if FEATURE_XXX_PRO_USER:
    @register_operation
    class WF_AddSharedEmailOperation(WFOperation):
        operation_name = 'add_shared_email'
        NotImplemented


    @register_operation
    class WF_RemoveSharedEmailOperation(WFOperation):
        operation_name = 'remove_shared_email'
        NotImplemented


    @register_operation
    class WF_RegisterSharedEmailUserOperation(WFOperation):
        operation_name = 'register_shared_email_user'
        NotImplemented


    @register_operation
    class WF_MakeSharedSubtreePlaceholderOperation(WFOperation):
        operation_name = 'make_shared_subtree_placeholder'
        NotImplemented


class WFBaseTransaction():
    is_executed = False

    def __init__(self, wf):
        self.operations = []
        self.wf = wf

    def get_client_timestamp(self, current_time=None):
        raise NotImplementedError

    def push(self, operation):
        raise NotImplementedError

    def pre_operation(self):
        for operation in self:
            operation.pre_operation(self)

    def post_operation(self):
        for operation in self:
            operation.post_operation(self)

    def __iter__(self):
        return iter(self.operations)

    def __iadd__(self, other):
        self.push(other)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            return False

        self.commit()
        return False

    def commit(self):
        raise NotImplementedError

    def rollback(self):
        raise NotImplementedError


class WFServerTransaction(WFBaseTransaction):
    def __init__(self, wf, client_tr, client_timestamp):
        super().__init__(wf)
        self.client_timestamp = client_timestamp
        self.client_transaction = client_tr

    @classmethod
    def from_server_operations(cls, wf, client_tr, data):
        client_timestamp = data["client_timestamp"]
        self = cls(wf, client_tr, client_timestamp)

        client_operations = list(self.get_client_operations_json())
        def pop_client_operation():
            if client_operations:
                return client_operations.pop(0)

            return None

        current_client_operation = pop_client_operation()

        for op in data["ops"]:
            op.pop("server_data", None)
            # server_data are exists when server_info

            if current_client_operation == op:
                # is it safe?
                current_client_operation = pop_client_operation()
                continue

            # TODO: change OPERATOR_COLLECTION?
            operator = OPERATOR_COLLECTION.get(op["type"], _WFUnknownOperation)
            operation = operator.from_server_operation_json(self, op)
            self.push(operation)

        return self

    def get_client_operations_json(self):
        client_tr = self.client_transaction
        for operation in client_tr:
            yield operation.get_cached_operation(client_tr)
            # not get_client_operation

    def get_client_timestamp(self, current_time=None):
        assert current_time is None
        return self.client_timestamp

    def push(self, operation):
        self.operations.append(operation)

    def commit(self):
        with self.wf.transaction_lock:
            if self.is_executed:
                return

            self.pre_operation()
            self.post_operation()
            self.is_executed = True


class WFClientTransaction(WFBaseTransaction):
    IDENTIFY_TID = string.digits + string.ascii_letters

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tid = self.generate_tid()

    @classmethod
    def generate_tid(cls):
        return "".join(random.choice(cls.IDENTIFY_TID) for i in range(8))

    def get_client_timestamp(self, current_time=None):
        if current_time is None:
            current_time = time.time()

        return (current_time - self.wf.status.date_joined_timestamp_in_seconds) // 60

    def push(self, operation):
        # TODO: determine good position for pre_operation and post_operation
        # XXX: if pre_operation and post_operation in push_poll function, transaction are not work.
        operation.pre_operation(self)
        self.operations.append(operation)
        operation.post_operation(self)

    def get_operations_json(self):
        operations = []
        for operation in self:
            operations.append(operation.get_client_operation(self))

        return operations

    def get_transaction_json(self, operations=None):
        if operations is None:
            operations = self.get_operations_json()

        transaction = dict(
            most_recent_operation_transaction_id=self.wf.status.most_recent_operation_transaction_id,
            operations=operations,
        )

        # TODO: move shared project process code.
        status = self.wf.status
        if status.share_type is not None:
            assert status.share_type == "url"
            share_id = status.share_id
            transaction.update(
                share_id=share_id,
            )

        return [transaction]

    def commit(self):
        with self.wf.transaction_lock:
            if self.is_executed:
                return

            self.wf.execute_transaction(self)
            self.is_committed = True

            if self.wf.current_transaction is self:
                self.wf.current_transaction = None


class WFSimpleSubClientTransaction(WFClientTransaction):
    def __init__(self, wf, tr):
        self.wf = wf
        self.tr = tr

    @property
    def operations(self):
        return self.tr.operations

    def commit(self):
        # already operation are appended to main transaction.
        assert not self.tr.is_executed


class WFDeamonSubClientTransaction(WFSimpleSubClientTransaction):
    # TODO: Really need it?
    pass

    
class WFBaseQuota():
    def is_full(self):
        return self.used >= self.total

    def is_overflow(self):
        return self.used > self.total

    def handle_overflow(self):
        # It's NOT OK.
        raise NotImplementedError

    def handle_underflow(self):
        # It's OK.
        pass

    def __iadd__(self, other):
        self.used += other
        if self.is_overflow():
            self.handle_overflow()
        return self

    def __isub__(self, other):
        self.used -= other
        if self.is_underflow():
            self.handle_underflow()
        return self

    def is_full(self):
        return self.used >= self.total

    def is_overflow(self):
        return self.used > self.total

    def is_underflow(self):
        return self.used < 0


class WFQuota(WFBaseQuota):
    def __init__(self, used=0, total=DEFAULT_WORKFLOWY_MONTH_QUOTA):
        self.used = used
        self.total = total

    @classmethod
    def from_main_project(cls, info):
        return cls(info["itemsCreatedInCurrentMonth"], info["monthlyItemQuota"])

    def handle_overflow(self):
        raise WFOverflowError("monthly item quota reached.")


class WFSharedQuota(WFBaseQuota):
    MINIMAL = 0
    MAXIMUM = float('inf')

    def __init__(self, is_over=False):
        super().__init__(self.MINIMAL, self.MAXIMUM)
        self.is_over = is_over

    @property
    def is_over(self):
        return self.used == self.total

    @is_over.setter
    def is_over(self, is_over):
        self.used = self.MAXIMUM if is_over else self.MINIMAL

    def handle_overflow(self):
        raise WFOverflowError("monthly item quota reached in shared view.")


class BaseWorkflowy():
    NODE_CLASS = NotImplemented
    CLIENT_TRANSACTION_CLASS = NotImplemented
    SERVER_TRANSACTION_CLASS = NotImplemented
    CLIENT_SUBTRANSACTION_CLASS = NotImplemented

    def __init__(self):
        raise NotImplementedError

    def transaction(self):
        raise NotImplementedError


class WFBaseNodeManager():
    NODE_CLASS = NotImplemented


class WFNodeManager(WFBaseNodeManager):
    NODE_CLASS = WFNode

    def __init__(self):
        super().__init__()
        self.data = WeakValueDictionary()
        self.root = None

    def update_root(self, root_info):
        self.root = self.new_root_node(root_info)

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

    def new_root_node(self, info):
        root = info["rootProject"]
        child = info["rootProjectChildren"]
        if root is None:
            root = dict(id=DEFAULT_ROOT_NODE_ID)
        else:
            root.update(id=DEFAULT_ROOT_NODE_ID)
            # in shared mode, root will have uuid -(replace)> DEFAULT_ROOT_NODE_ID

        root.update(ch=child)
        root = self.new_node_from_json(root)
        self.add(root, update_child=True)
        return root


class WFOperationCollection():
    NODE_MANAGER_CLASS = WFNodeManager
    # TODO: add unsupported operation. (move, etc.)

    def edit(self, node, name=None, description=None):
        with self.transaction() as tr:
            tr += WF_EditOperation(node, name, description)

    def create(self, parent, priority=-1, *, node=None):
        priority_range = range(len(parent) + 1)

        try:
            priority = priority_range[priority]
        except IndexError:
            raise WFError("invalid priority are selected. (just use default value.)")

        node = self.nodemgr.new_void_node() if node is None else node
        with self.transaction() as tr:
            tr += WF_CreateOperation(parent, node, priority)

        return node

    def complete(self, node):
        with self.transaction() as tr:
            tr += WF_CompleteOperation(node)

    def uncomplete(self, node):
        with self.transaction() as tr:
            tr += WF_UncompleteOperation(node)

    def delete(self, node):
        with self.transaction() as tr:
            tr += WF_DeleteOperation(node)


class Workflowy(BaseWorkflowy, WFOperationCollection):
    CLIENT_TRANSACTION_CLASS = WFClientTransaction
    SERVER_TRANSACTION_CLASS = WFServerTransaction
    CLIENT_SUBTRANSACTION_CLASS = WFSimpleSubClientTransaction
    client_version = DEFAULT_WORKFLOWY_CLIENT_VERSION

    def __init__(self, share_id=None, *, sessionid=None, username=None, password=None):
        # XXX: SharedWorkflowy are required? or how to split shared and non-shared processing code.
        self._inited = False
        
        self.browser = self._init_browser()

        self.globals = attrdict()
        self.settings = attrdict()
        self.project_tree = attrdict()
        self.main_project = attrdict()
        self.status = attrdict()

        self.current_transaction = None
        self.transaction_lock = threading.RLock()

        self.nodemgr = self.NODE_MANAGER_CLASS()
        self.quota = WFQuota()

        if sessionid is not None or username is not None:
            username_or_sessionid = sessionid or username
            self.login(username_or_sessionid, password)

        self.init(share_id)

    # smart handler
    @contextmanager
    def smart_handle_init(self):
        try:
            yield
            self.handle_init()
        finally:
            pass

    @contextmanager
    def smart_handle_reset(self):
        try:
            self.handle_reset()
            yield
        finally:
            pass

    def handle_init(self):
        pass
    
    def handle_reset(self):
        pass

    def handle_logout(self):
        self.inited = False
        raise WFLoginError("Login Failure.")

    def reset(self):
        # TODO: give argument to _reset and smart handler?
        with self.smart_handle_reset():
            self._reset()

    def init(self, *args, **kwargs):
        # TODO: give argument to smart handler? (_init require argument!)
        with self.smart_handle_init():
            self._init(*args, **kwargs)

    @property
    def inited(self):
        return self._inited

    @inited.setter
    def inited(self, inited):
        if inited:
            self._inited = True
        else:
            self.reset()
            self._inited = False

    def _reset(self):
        self.handle_reset()
        self.browser.reset()

        self.globals.clear()
        self.settings.clear()
        self.project_tree.clear()
        self.main_project.clear()
        self.status.clear()

        self.current_transaction = None

        self.nodemgr.clear()
        self.quota = WFQuota()

    @classmethod
    def _init_browser(cls):
        browser = Browser(DEFAULT_WORKFLOWY_URL)
        return browser

    def print_status(self):
        pprint(vars(self), width=240)

    def transaction(self, *, force_new_transaction=False):
        with self.transaction_lock:
            if self.current_transaction is None:
                self.current_transaction = self.CLIENT_TRANSACTION_CLASS(self)
            else:
                return self.CLIENT_SUBTRANSACTION_CLASS(self, self.current_transaction)

            return self.current_transaction

    def login(self, username_or_sessionid, password=None, *, auto_init=True, use_ajax_login=True):
        home_content = None

        if password is None:
            session_id = username_or_sessionid
            self.browser.set_cookie("sessionid", session_id)
        else:
            username = username_or_sessionid
            if use_ajax_login:
                res, data = self.browser["ajax_login"](username=username, password=password)
                errors = data.get("errors")
                if errors:
                    # 'errors' or 'success'
                    raise WFLoginError("Login Failure.")
            else:
                res, data = self.browser["accounts/login/"](username=username, password=password, next="", _raw=True)
                home_content = data

        if auto_init:
            return self.init(home_content=home_content)

    _SCRIPT_TAG_REGEX = re.compile("".join([
        re.escape('<script type="text/javascript">'), "(.*?)", re.escape('</script>'),
    ]), re.DOTALL)

    _SCRIPT_VAR_REGEX = re.compile("".join([
        re.escape("var "), "(.*?)", re.escape(" = "), "(.*?|\{.*?\})", re.escape(";"), '$',
    ]), re.DOTALL | re.MULTILINE)

    @classmethod
    def _get_globals_by_home(cls, content):
        for source in cls._SCRIPT_TAG_REGEX.findall(content):
            if "(" in source:
                # function call found while parsing.
                continue

            for key, value in cls._SCRIPT_VAR_REGEX.findall(source):
                if value.startswith("'") and value.endswith("'"):
                    assert '"' not in value
                    value = '"{}"'.format(value[+1:-1])

                if key == "FIRST_LOAD_FLAGS" or key == "SETTINGS":
                    # TODO: non-standard json parse by demjson?
                    continue

                value = json.loads(value)
                yield key, value

    def _init(self, share_id=None, *, home_content=None):
        try:
            url = "get_initialization_data"
            info = dict(
                client_version=self.client_version,
            )

            if share_id is not None:
                info.update(share_id=share_id)

            info = urlencode(info)
            res, data = self.browser["get_initialization_data?" + info]()
        except HTTPError as e:
            if e.code == 404:
                self.handle_logout()
            else:
                # TODO: warp HTTPError? or in browser?
                raise

        if home_content is None:
            _, home_content = self.browser[""](_raw=True)
        self.globals.update(self._get_globals_by_home(home_content))

        data = attrdict(data)
        self.globals.update(data.globals)
        self.settings.update(data.settings)
        self.project_tree.steal(data, "projectTreeData")
        self.main_project.steal(self.project_tree, "mainProjectTreeInfo")
        self._status_update_by_main_project()
        self.nodemgr.update_root(self.main_project)
        self.handle_init()
        self.inited = True

    @property
    def root(self):
        return self.nodemgr.root

    def _status_update_by_main_project(self):
        status = self.status
        mp = self.main_project

        status.most_recent_operation_transaction_id = mp.initialMostRecentOperationTransactionId
        status.date_joined_timestamp_in_seconds = mp.dateJoinedTimestampInSeconds
        status.polling_interval = mp.initialPollingIntervalInMs / 1000
        status.is_readonly = mp.isReadOnly

        if mp.get("shareType"):
            status.share_type = mp.shareType
            status.share_id = mp.shareId
        else:
            status.share_type = None
            status.share_id = None

        # main_project also contains overQuota if shared.
        status.is_shared_quota = "overQuota" in mp

        if status.is_shared_quota:
            status.is_over_quota = mp.overQuota
        else:
            status.items_created_in_current_month = mp.itemsCreatedInCurrentMonth
            status.monthly_item_quota = mp.monthlyItemQuota

        self._quota_update()

    def _quota_update(self):
        status = self.status
        quota = self.quota

        if status.is_shared_quota:
            quota.is_over = status.is_over_quota
        else:
            quota.used = status.items_created_in_current_month
            quota.total = status.monthly_item_quota


    def __contains__(self, node):
        return node in self.nodemgr

    def __getitem__(self, node):
        return self.nodemgr[node]

    def __iter__(self):
        return iter(self.nodemgr)

    def add_node(self, node, update_child=True, update_quota=True):
        added_nodes = self.nodemgr.add(node, update_child=update_child)

        if update_quota:
            self.quota += added_nodes

    def remove_node(self, node, recursion_delete=False, update_quota=True):
        removed_nodes = self.nodemgr.remove(node, recursion_delete=recursion_delete)

        if update_quota:
            self.quota -= removed_nodes

    def _refresh_project_tree(self):
        nodes = self.nodes
        main_project = self.main_project
        root_project = self.root_project

        # TODO: refreshing project must keep old node if uuid are same.
        # TODO: must check root are shared. (share_id and share_type will help us.)

        raise NotImplementedError

    def execute_transaction(self, tr):
        push_poll_info = self._execute_client_transaction(tr)

        self._handle_errors_by_push_poll(push_poll_info)
        for data in self._status_update_by_push_poll(push_poll_info):
            self._execute_server_transaction(tr, data)

    def _execute_client_transaction(self, tr):
        data = tr.get_transaction_json()
        arguments = dict (
            client_id=self.project_tree.clientId,
            client_version=self.client_version,
            push_poll_id=tr.tid,
            push_poll_data=json.dumps(data),
        )

        if self.status.share_type is not None:
            # how to merge code with WFClientTransaction.get_transaction_json()
            assert self.status.share_type == "url"
            arguments.update(share_id=self.status.share_id)

        res, data = self.browser["push_and_poll"](**arguments)
        return data

    def _handle_errors_by_push_poll(self, data):
        error = data.get("error")
        if error:
            raise WFRuntimeError(error)

        logged_out = data.get("logged_out")
        if logged_out:
            raise WFLoginError("logout detected, don't share session with real user.")
        
    def _status_update_by_push_poll(self, data):
        results = data.get("results")
        if results is None:
            # TODO: raise error?
            return

        datas = []
        with debug_helper_with_json(data):
            for res in results:
                res = attrdict(res)
                self._status_update_by_push_poll_sub(res)

        return datas

    def _status_update_by_push_poll_sub(self, res):
        error = res.get("error")
        if error:
            raise WFRuntimeError(error)

        status = self.status
        status.most_recent_operation_transaction_id = \
            res.new_most_recent_operation_transaction_id
        datas.append(json.loads(res.server_run_operation_transaction_json))

        if res.get("need_refreshed_project_tree"):
            raise NotImplementedError
            self._refresh_project_tree()
            # XXX how to execute operation after refresh project tree? no idea.

        status.polling_interval = res.new_polling_interval_in_ms / 1000

        if status.is_shared_quota:
            status.is_over_quota = res.over_quota
        else:
            status.items_created_in_current_month = \
                res.items_created_in_current_month
            status.monthly_item_quota = res.monthly_item_quota

        self._quota_update()

    def _execute_server_transaction(self, tr, data):
        transaction = self.SERVER_TRANSACTION_CLASS.from_server_operations(self, tr, data)
        transaction.commit()


class WeakWorkflowy(Workflowy):
    NODE_MANAGER_CLASS = NotImplemented

    def __init__(self, *args, **kwargs):
        class _WFNode_(WF_WeakNode):
            __slots__ = []
            _wf = self

        class WFDynamicNodeManager(WFNodeManager):
            NODE_CLASS = _WFNode_

        self.NODE_MANAGER_CLASS = WFDynamicNodeManager
        super().__init__(*args, **kwargs)


class WFMixinDeamon(BaseWorkflowy):
    CLIENT_SUBTRANSACTION_CLASS = WFDeamonSubClientTransaction
    # TODO: new subtransaction class are push operation at commit time.
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue = self._new_queue()
        # INTERNAL: self.queue is internal value at this time.
        self.thread = self._new_thread()
        self.default_execute_wait = 5
        
    def _task():
        queue = self.queue
        # queue can be overflow
        
        with self.transaction_lock:
            while queue:
                self.queue.get_nowait()

            queue.put(0)
            # INTERNAL: start counter for task        

        while True:
            wait = self.default_execute_wait
            event = queue.get()
            if event is None:
                # STOP EVENT
                return
            
            time.sleep(wait)
            # TODO: how to sleep automation?
            # TODO: use some good schuler?

            with self.transaction_lock:
                current_transaction = self.current_transaction
                if not self.current_transaction.operations:
                    queue.put(event + wait)
                    continue
                
                if event >= self.status.default_execute_wait:
                    self.current_transaction = None
                    self.execute_transaction(current_transaction)
                    
                queue.put(0)
                # reset counter
    
    def execute_transaction(self, tr):
        # it's ok because lock is RLock!
        with self.transaction_lock:
            super().execute_transaction(tr)
    
    # TODO: auto start with inited var
    
    def _new_thread(self):
        return threading.Thread(target=self._task)
    
    def _new_queue(self):
        return queue.Queue()
    
    def start(self):
        self.thread.start()
    
    def stop(self):
        # send stop signal to thread.
        self.queue.put(None)
    
    def reset(self):
        super().reset
        
        self.stop()
        self.queue = self._new_queue()
        self.thread = self._new_thread()

def main():
    #class AutoWeakWorkflowy(WeakWorkflowy, WFMixinDeamon):
    #    pass

    wf = wfapi.WeakWorkflowy("hBYC5FQsDC")
    wf.start()

    with wf.transaction():
        if not wf.root:
            node = wf.root.create()
        else:
            node = wf.root[0]

        node.edit("Welcome Workflowy!", "Last Update: %i" % time.time())
        if not node:
            subnode = node.create()
        else:
            subnode = node[0]

        subnode.edit("Hello world!", "")
        subnode.complete()

    wf.root.pretty_print()

if __name__ == "__main__":
    main()