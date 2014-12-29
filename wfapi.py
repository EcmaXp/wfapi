import copy
import functools
import json
import os
import random
import string
import sys
import threading
import time
import uuid
import warnings
import weakref
from contextlib import closing
from http.cookiejar import Cookie, CookieJar
from pprint import pprint
from urllib.error import HTTPError
from urllib.parse import urljoin, urlencode, urlparse
from urllib.request import build_opener, HTTPCookieProcessor, Request

__all__ = ["Workflowy", "WeakWorkflowy"]

DEFAULT_WORKFLOWY_URL = "https://workflowy.com/"
DEFAULT_ROOT_NODE_ID = "None"
FEATURE_XXX_PRO_USER = False
FEATURE_XXX_QUOTA = False
# Change FEATURE_XXX_PRO_USER are does nothing. just define more empty classes only.
DEFAULT_WORKFLOWY_CLIENT_VERSION = 14
# At 2014-12-22.

OPERATOR_COLLECTION = {}
# WFOperation collection.

def gen_uuid():
    return str(uuid.UUID(bytes=os.urandom(16)))

IDENTIFY_TID = string.digits + string.ascii_letters
def gen_tid():
    # TODO: make this
    return "".join(random.choice(IDENTIFY_TID) for i in range(8))


class Browser():
    def __init__(self, base_url):
        self.cookie_jar = CookieJar()
        self.opener = build_opener(HTTPCookieProcessor(self.cookie_jar))
        self.base_url = base_url

    def open(self, url, *, _is_json=True, _raw=False, **kwargs):
        url = urljoin(self.base_url, url)
        data = urlencode(kwargs).encode()
        headers = {
            "Content-Type" : "application/x-www-form-urlencoded",
        }

        req = Request(url, data, headers)
        res = self.opener.open(req)

        with closing(res) as fp:
            content = fp.read()

        content = content.decode()

        if not _raw:
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

    def __getitem__(self, url):
        return functools.partial(self.open, url)


class attrdict(dict):
    def __init__(self, *args, **kwargs):
          super().__init__(*args, **kwargs)
          self.__dict__ = self


class WFError(Exception):
    pass


class WFLoginError(WFError):
    pass


class WFNodeError(WFError):
    pass


class WFOverflowError(WFError, OverflowError):
    pass


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

        return self._empty_data_filter(operation)

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

        return operation

    def get_default_undo_data(self):
        return dict(previous_last_modified=self.node.lm)

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
            op.data["node"] = tr.wf.nodes[projectid]
            # if not exist node, raise error?

        return op

    @classmethod
    def from_server_operation(cls, tr, **data):
        raise NotImplementedError

    def execute(self, tr):
        self.pre_operation(tr)
        self.post_operation(tr)


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


class WF_EditOperation(WFOperation):
    operation_name = 'edit'

    def __init__(self, node, name=None, description=None):
        self.node = node
        self.name = name
        self.description = description

    def pre_operation(self, tr):
        tr.wf.check_exist_node(self.node)

    def post_operation(self, tr):
        node = self.node
        if self.name is not None:
            node.nm = self.name

        if self.description is not None:
            node.no = self.description

    @classmethod
    def from_server_operation(cls, tr, node, name=None, description=None):
        return cls(node, name, description)

    def get_operation_data(self, tr):
        return dict(
            projectid = self.node.id,
            name = self.name,
            description = self.description,
        )

    def get_undo_data(self, tr):
        return dict(
            previous_name=self.node.nm if self.name is not None else None,
            previous_description=self.node.no if self.description is not None else None,
        )


class WF_CreateOperation(WFOperation):
    operation_name = 'create'

    def __init__(self, parent, node, priority):
        self.parent = parent
        self.node = node
        self.priority = priority

    def pre_operation(self, tr):
        tr.wf.check_not_exist_node(self.node)

    def post_operation(self, tr):
        self.parent.insert(self.priority, self.node)
        tr.wf.add_node(self.node)
        # TODO: more good way to management node.

    def get_operation_data(self, tr):
        return dict(
            projectid=self.node.id,
            parentid=self.parent.id,
            priority=self.priority,
        )

    def get_undo_data(self, tr):
        return {}

    @classmethod
    def prepare_server_operation_json(cls, tr, op):
        return op

    @classmethod
    def from_server_operation(cls, tr, projectid, parentid, priority):
        node = tr.wf.new_void_node(projectid)
        node.lm = tr.get_client_timestamp()
        parent = tr.wf.nodes[parentid]
        return cls(parent, node, priority)


class _WF_CompleteNodeOperation(WFOperation):
    operation_name = NotImplemented

    def __init__(self, node):
        self.node = node
        self.modified = None
        # modified will auto fill by get_operation_data

    def pre_operation(self, tr):
        tr.wf.check_exist_node(self.node)

    def post_operation(self, tr):
        pass

    def get_operation_data(self, tr):
        return dict(
            projectid = self.node.id,
        )

    def get_undo_data(self, tr):
        return dict(
            previous_completed=self.node.cp if self.node.cp is not None else False,
        )

    @classmethod
    def from_server_operation(cls, tr, node):
        return cls(node)


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
        self.node.cp = None


class WF_UncompleteOperation(_WF_CompleteNodeOperation):
    operation_name = 'uncomplete'

    def post_operation(self, tr):
        self.node.cp = None


class WF_DeleteOperation(WFOperation):
    operation_name = 'delete'

    def __init__(self, node):
        self.parent = node.parent
        self.node = node

        self.parent.ready_ch()
        self.priority = self.parent.ch.index(node)
        # TODO: more priority calc safety.

    def pre_operation(self, tr):
        tr.wf.check_exist_node(self.node)

    def post_operation(self, tr):
        node = self.node
        if self.parent:
            assert node in self.parent
            self.parent.ch.remove(node)

        tr.wf.remove_node(node, recursion_delete=True)

    def get_operation_data(self, tr):
        return dict(
            projectid=self.node.id,
        )

    def get_undo_data(self, tr):
        return dict(
            parentid=self.parent.id,
            priority=self.priority,
        )


class WF_UndeleteOperation(WFOperation):
    operation_name = 'undelete'

    def __init__(self):
        raise NotImplementedError("Just don't do that. :P")


class WF_MoveOperation(WFOperation):
    operation_name = 'move'

    def __init__(self, parent, node, priority):
        self.parent = parent
        self.node = node
        self.priority = priority

    def pre_operation(self, tr):
        tr.wf.check_exist_node(self.node)
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
            projectid=self.node.id,
            parentid=self.parent.id,
            priority=self.priority,
        )

    def get_undo_data(self, tr):
        previous_priority = None
        if self.node in self.node.parent:
            previous_priority = self.node.parent.ch.index(self.node)

        return dict(
            previous_parentid=self.node.parent.id,
            previous_priority=previous_priority,
        )

    @classmethod
    def prepare_server_operation_json(cls, tr, op):
        op = super().prepare_server_operation_json(tr, op)
        op.data["node"] = tr.wf.nodes[op.data.pop("projectid")]
        op.data["parent"] = tr.wf.nodes[op.data.pop("parentid")]
        return op

    @classmethod
    def from_server_operation(cls, tr, node, parent, priority):
        return cls(parent, node, priority)


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
            projectid=self.node.id,
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
            projectid=self.node.id,
        )

    get_undo_data = WF_ShareOperation.get_undo_data

    @classmethod
    def from_server_operation(cls, tr, node):
        return cls(node)


class WF_BulkCreateOperation(WFOperation):
    operation_name = 'bulk_create'
    NotImplemented
    
    # This operation does add node at one times.
    
    def __init__(self, parent, project_trees, starting_priority):
        self.parent = parent
        self.project_trees = project_trees
        self.starting_priority = starting_priority

    def pre_operation(self, tr):
        tr.wf.check_not_exist_node(self.project_trees)

    def post_operation(self, tr):
        self.parent.insert(self.starting_priority, self.project_trees)
        tr.wf.add_node(self.project_trees, update_child=True)

    def get_operation_data(self, tr):
        return dict(
            parentid=self.parent.id,
            project_trees=self.project_trees.to_json(),
            starting_priority=self.starting_priority,
        )

    def get_undo_data(self, tr):
        return {}

    @classmethod
    def prepare_server_operation_json(cls, tr, op):
        op = super().prepare_server_operation_json(tr, op)
        op.data["project_trees"] = json.loads(op.data.pop("project_trees")])
        op.data["parent"] = tr.wf.nodes[op.data.pop("parentid")]
        return op

    @classmethod
    def from_server_operation(cls, tr, parent, project_trees, starting_priority):
        project_trees = tr.wf.NODE_CLASS.from_json(project_trees, parent=parent)
        return cls(parent, project_trees, starting_priority)


class WF_BulkMoveOperation(WFOperation):
    operation_name = 'bulk_move'
    NotImplemented
    

if FEATURE_XXX_PRO_USER:
    class WF_AddSharedEmailOperation(WFOperation):
        operation_name = 'add_shared_email'
        NotImplemented


    class WF_RemoveSharedEmailOperation(WFOperation):
        operation_name = 'remove_shared_email'
        NotImplemented


    class WF_RegisterSharedEmailUserOperation(WFOperation):
        operation_name = 'register_shared_email_user'
        NotImplemented


    class WF_MakeSharedSubtreePlaceholderOperation(WFOperation):
        operation_name = 'make_shared_subtree_placeholder'
        NotImplemented

class WFBaseNode():
    # this class for fixing weakref for WF_WNode.
    # http://stackoverflow.com/questions/24407874/inherit-class-with-weakref-in-slots
    __slots__  = ["id", "lm", "nm", "ch", "no", "cp", "shared", "parent", "__weakref__"]

class WFNode(WFBaseNode):
    __slots__ = []

    def __init__(self, id, lm=0, nm="", ch=None, no="", cp=None, shared=None, parent=None):
        if isinstance(id, uuid.UUID):
            id = str(id)

        self.id = id # UUID or "None"(DEFAULT_ROOT_NODE_ID)
        self.lm = lm # ?
        self.nm = nm # key
        self.ch = ch # children
        self.no = no # content
        self.cp = cp # complete marking time. (cp is None -> uncompleted, is not None -> completed)
        self.shared = shared
        self.parent = parent

        for child in self:
            assert child.parent is None
            child.parent = self

    def __repr__(self):
        return "<WFNode({id!r})>".format(clsname = type(self).__name__, id = self.id)

    def __str__(self):
        return "{clsname}(id={id!r}, lm={lm!r}, nm={nm!r}, ch={ch!r}, no={no!r}, cp={cp!r}{_shared})".format(
            clsname = type(self).__name__,
            id = self.id,
            lm = self.lm,
            nm = self.nm,
            ch = self.ch,
            no = self.no,
            cp = self.cp,
            _shared = ", shared={!r}".format(self.shared) if self.shared is not None else "",
        )

    def ready_ch(self):
        "put list to ch. only internal use."

        if self.ch is None:
            self.ch = []

    def copy(self):
        # shortcut.
        return copy.copy(self)

    def insert(self, index, node):
        if node.parent is not None:
            raise WFNodeError("not allow copy child, use api.")
            # TODO: remove bad english. :(

        self.ready_ch()
        self.ch.insert(index, node)
        node.parent = self

    def __bool__(self):
        return len(self) > 0

    def __len__(self):
        return len(self.ch) if self.ch else 0

    def __contains__(self, item):
        if not self.ch:
            return False

        return item in self.ch

    def __iter__(self):
        if not self.ch:
            return iter(())

        return iter(self.ch)

    def __getitem__(self, item):
        if not isinstance(item, slice):
            if not self.ch:
                raise IndexError(item)

        return self.ch[item]

    def pretty_print(self, *, stream=None, indent=0):
        if stream is None:
            stream = sys.stdout

        INDENT_SIZE = 2
        p = lambda *args: print(" "*indent + " ".join(args), file=stream)

        is_empty_root = self.id == DEFAULT_ROOT_NODE_ID and not self.nm and indent == 0
        if is_empty_root:
            p("[*]", "Home")
        else:
            p("[%s]" % (self.cp and "-" or " ",), self.nm, "{%s} " % self.id)

        for line in self.no.splitlines():
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

        if parent:
            data["parent"] = parent

        return cls(**data)
        
    def to_json(self):
        # def __init__(self, id, lm=0, nm="", ch=None, no="", cp=None, shared=None, parent=None):
        ret = dict(
            id=self.id
            lm=self.lm
            nm=self.nm,
        )

        ch = []
        for node in self:
            ch.append(node.to_json())
        
        if ch:
            ret.update(ch=ch)
        
        if self.no:
            ret.update(no=self.no)

        if self.cp is not None:
            ret.update(cp=self.cp)

        if self.shared is not None:
            ret.update(shared=self.shared)
            
        # parent will be ignore.
        
        return ret

    @classmethod
    def from_root(cls, info):
        root = info["rootProject"]
        child = info["rootProjectChildren"]
        if root is None:
            root = dict(id=DEFAULT_ROOT_NODE_ID)
        else:
            root.update(id=DEFAULT_ROOT_NODE_ID)
            # if workflowy in shared mode, root will have uuid.
            # XXX: no way to keep root.id without change many code.

        root.update(ch=child)
        root = cls.from_json(root)
        return root

    @classmethod
    def from_void(cls, uuid=None):
        return cls(uuid or gen_uuid())

class WF_WeakNode(WFNode):
    __slots__ = []

    def __getattr__(self, item):
        if not item.startswith("_") and item in dir(WFOperationCollection):
            return functools.partial(getattr(self._wf, item), self)

        raise AttributeError(item)

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
        # TODO: from_server_operations method-name is not good.
        client_timestamp = data["client_timestamp"]
        self = cls(wf, client_tr, client_timestamp)

        client_operations = self.get_client_operations_json()
        pop = (lambda: client_operations.pop(0) if client_operations else None)
        # TODO: change pop function.
        current_client_operation = pop()

        for op in data["ops"]:
            op.pop("server_data", None)
            # server_data are exists when server_info

            if current_client_operation == op:
                # is it safe?
                current_client_operation = pop()
                continue

            operator = OPERATOR_COLLECTION.get(op["type"], _WFUnknownOperation)
            operation = operator.from_server_operation_json(self, op)
            self.push(operation)

        return self

    def get_client_operations_json(self):
        ret = []

        client_tr = self.client_transaction
        for operation in client_tr:
            ret.append(operation.get_cached_operation(client_tr))
            # not get_client_operation

        return ret

    def get_client_timestamp(self, current_time=None):
        assert current_time is None
        return self.client_timestamp

    def push(self, operation):
        self.operations.append(operation)

    def commit(self):
        with self.wf.lock:
            if self.is_executed:
                return

            self.pre_operation()
            self.post_operation()
            self.is_executed = True


class WFClientTransaction(WFBaseTransaction):
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
        with self.wf.lock:
            if self.is_executed:
                return

            self.wf.execute_transaction(self)
            self.is_committed = True

            if self.wf.current_transaction is self:
                self.wf.current_transaction = None


class WFSubClientTransaction(WFClientTransaction):
    def __init__(self, wf, tr):
        self.wf = wf
        self.tr = tr

    @property
    def operations(self):
        return self.tr.operations

    def commit(self):
        # already operation are appended to main transaction.
        assert not self.tr.is_executed


if FEATURE_XXX_QUOTA:
    class WFQuota():
        # TODO: child update please.
        # XXX: Quota calc? simple,
        # <m> 매번 500개를 추가로 저장할 공간을 준다는 거에여
        # crazy!!!

        def __init__(self, itemsCreatedInCurrentMonth, monthlyItemQuota):
            self.used = itemsCreatedInCurrentMonth
            self.total = monthlyItemQuota

        @classmethod
        def from_main_project(cls, info):
            return cls(info["itemsCreatedInCurrentMonth"], info["monthlyItemQuota"])

        @classmethod
        def build_empty(cls):
            return cls(0, 0)

        def is_full(self):
            return self.used >= self.total

        def is_overflow(self):
            return self.used > self.total

        def __iadd__(self, other):
            self.used += other
            if self.is_overflow():
                raise WFOverflowError("monthly item quota reached.")
            return self

        def __isub__(self, other):
            self.used -= other
            if self.used < 0:
                warnings.warn("while calculate workflowy quota, underflow are detected.")
            return self


class BaseWorkflowy():
    NODE_CLASS = NotImplemented
    CLIENT_TRANSACTION_CLASS = NotImplemented
    SERVER_TRANSACTION_CLASS = NotImplemented
    CLIENT_SUBTRANSACTION_CLASS = NotImplemented

    def __init__(self):
        raise NotImplementedError

    def transaction(self):
        raise NotImplementedError

class WFOperationCollection():
    NODE_CLASS = WFNode

    # TODO: add expend node. (not operation.)
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

        # XXX: this class don't have workflowy, NODE_CLASS must have workflowy api? IDK...
        node = self.NODE_CLASS.from_void() if node is None else node
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

# XXX: SharedWorkflowy are required? or how to split shared and non-shared processing code.
class Workflowy(BaseWorkflowy, WFOperationCollection):
    CLIENT_TRANSACTION_CLASS = WFClientTransaction
    SERVER_TRANSACTION_CLASS = WFServerTransaction
    CLIENT_SUBTRANSACTION_CLASS = WFSubClientTransaction
    client_version = DEFAULT_WORKFLOWY_CLIENT_VERSION

    def __init__(self):
        self.browser = self._init_browser()
        self.globals = attrdict()
        self.settings = attrdict()
        self.project_tree = attrdict()
        self.main_project = attrdict()
        self.status = attrdict()
        self.root = None
        self.nodes = weakref.WeakValueDictionary()
        self.current_transaction = None
        self.inited = False
        self.lock = threading.RLock()

        if FEATURE_XXX_QUOTA:
            self.quota = WFQuota.build_empty()

    def clear(self):
        self.globals.clear()
        self.settings.clear()
        self.project_tree.clear()
        self.main_project.clear()
        self.status.clear()
        self.root = None
        self.nodes.clear()
        self.current_transaction = None
        self.inited = False

        if FEATURE_XXX_QUOTA:
            self.quota = WFQuota.build_empty()

    @classmethod
    def _init_browser(cls):
        browser = Browser(DEFAULT_WORKFLOWY_URL)
        return browser

    def print_status(self):
        pprint(vars(self), width=240)

    def transaction(self, *, force_new_transaction=False):
        with self.lock:
            if self.current_transaction is None:
                self.current_transaction = self.CLIENT_TRANSACTION_CLASS(self)
            else:
                # TODO: if running by deamon, just return sub transaction any call time.
                # TODO: support deamon.
                # TODO: new subtransaction class are push operation at commit time.
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

    @staticmethod
    def _get_globals_by_home(content):
        START_TAG = '<script type="text/javascript">'
        END_TAG = '</script>'

        while START_TAG in content:
            source, sep, content = content.partition(START_TAG)[2].partition(END_TAG)
            if "(" in source or ")" in source or not sep:
                # function call, or EOF found while parsing.
                continue

            for line in source.splitlines():
                line = line.strip()
                if not line:
                    continue

                key, sep, value = line.partition(" = ")
                if sep and key.startswith("var "):
                    key = key[len("var "):]
                    if value.endswith(";"):
                        value = value[:-len(";")]
                    else:
                        # TODO: support multi line config.
                        value = "null"
                else:
                    continue

                # XXX for MEDIA_URL.
                if value.startswith("'") and value.endswith("'"):
                    assert '"' not in value
                    value = '"{}"'.format(value[+1:-1])

                value = json.loads(value)
                yield key, value

    def init(self, share_id=None, *, home_content=None):
        try:
            url = "get_initialization_data"
            data = dict(
                client_version=self.client_version,
            )

            if share_id is not None:
                data.update(share_id=share_id)

            url += "?" + urlencode(data)
            res, data = self.browser[url]()
            # self.browser["get_initialization_data"]
        except HTTPError as e:
            if e.code == 404:
                self.inited = False
                raise WFLoginError("Login Failure.")
            else:
                raise

        self.clear()

        if home_content is None:
            _, home_content = self.browser[""](_raw=True)
        self.globals.update(self._get_globals_by_home(home_content))

        data = attrdict(data)
        self.globals.update(data.globals)
        self.settings.update(data.settings)
        self.project_tree.update(data.projectTreeData)
        self.main_project.update(self.project_tree.mainProjectTreeInfo)
        self._status_update_by_main_project()
        self.root = self.NODE_CLASS.from_root(self.main_project)
        self._root_optimize()
        self.inited = True

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

        if FEATURE_XXX_QUOTA:
            # main_project also contains overQuota if shared.
            status.items_created_in_current_month = mp.itemsCreatedInCurrentMonth
            status.monthly_item_quota = mp.monthlyItemQuota
            self._quota_update()


    if FEATURE_XXX_QUOTA:
        def _quota_update(self):
            status = self.status
            quota = self.quota
            quota.used = status.items_created_in_current_month
            quota.total = status.monthly_item_quota

    def _root_optimize(self):
        self.nodes.clear()

        nodes = self.nodes
        def deep(node):
            nodes[node.id] = node

            for child in node:
                deep(child)

        deep(self.root)

    def check_exist_node(self, node):
        original_node = self.nodes.get(node.id)
        if original_node is None:
            raise WFNodeError("{!r} is not exists.".format(node))
        elif original_node is not node:
            raise WFNodeError("{!r} is invalid node.".format(node))

    def check_not_exist_node(self, node):
        if node.id in self.nodes:
            raise WFNodeError("{!r} is already exists.".format(node))

    # TODO: make node manger.
    # TODO: add __getitem__, __contains__, etc.

    def new_void_node(self, uuid=None):
        return self.NODE_CLASS.from_void(uuid)

    def add_node(self, node, update_child=True):
        assert update_child is True
        self.check_not_exist_node(node)
        self.nodes[node.id] = node
        if update_child:
            for subnode in node:
                self.add_node(subnode)
        self.check_exist_node(node)

    def remove_node(self, node, recursion_delete=False):
        self.check_exist_node(node)
        if node.parent is not None:
            self.check_exist_node(node.parent)
            if node in node.parent:
                raise WFNodeError("node are still exists in parent node.")

        nodes = self.nodes
        if not recursion_delete:
            del node.parent
            del self.nodes[node.id]
        else:
            def deep(node):
                del node.parent
                del nodes[node.id]

                if node.ch:
                    child_nodes, node.ch = node.ch[:], None
                    for child in child_nodes:
                        deep(child)

            deep(node)

        self.check_not_exist_node(node)

    def _handle_errors_by_push_poll(self, data):
        error = data.get("error")
        if error:
            raise WFError(error)

        logged_out = data.get("logged_out")
        if logged_out:
            raise WFLoginError("logout detected, don't share session with real user.")

    def _status_update_by_push_poll(self, data):
        results = data.get("results")
        if results is None:
            return

        datas = []
        for res in results:
            res = attrdict(res)
            status = self.status
            status.most_recent_operation_transaction_id = res.new_most_recent_operation_transaction_id
            datas.append(json.loads(res.server_run_operation_transaction_json))

            if res.get("need_refreshed_project_tree"):
                raise NotImplementedError
                self._refresh_project_tree()
                # XXX how to execute operation after refresh project tree? no idea.

            if FEATURE_XXX_QUOTA:
                status.items_created_in_current_month = res.items_created_in_current_month
                status.monthly_item_quota = res.monthly_item_quota
                status.polling_interval = res.new_polling_interval_in_ms / 1000
                self._quota_update()

        return datas

    def _refresh_project_tree(self):
        nodes = self.nodes
        main_project = self.main_project
        root_project = self.root_project

        # TODO: refreshing project must keep old node if uuid are smae.
        # TODO: must check root are shared. (share_id and share_type will help us.)

        raise NotImplementedError

    def execute_transaction(self, tr):
        transaction_info = tr.get_transaction_json()
        push_poll_info = self._execute_client_transaction(transaction_info)

        self._handle_errors_by_push_poll(push_poll_info)
        for data in self._status_update_by_push_poll(push_poll_info):
            self._execute_server_transaction(tr, data)

    def _execute_client_transaction(self, data):
        arguments =dict (
            client_id=self.project_tree.clientId,
            client_version=self.client_version,
            push_poll_id=gen_tid(),
            push_poll_data=json.dumps(data),
        )

        if self.status.share_type is not None:
            # how to merge code with WFClientTransaction.get_transaction_json()
            assert self.status.share_type == "url"
            arguments.update(share_id=self.status.share_id)

        res, data = self.browser["push_and_poll"](**arguments)
        return data

    def _execute_server_transaction(self, tr, data):
        transaction = self.SERVER_TRANSACTION_CLASS.from_server_operations(self, tr, data)
        transaction.commit()


class WeakWorkflowy(Workflowy):
    NODE_CLASS = NotImplemented
    # NODE_CLASS will replace by __init__ function.

    def __init__(self):
        class _WFNode_(WF_WeakNode):
            __slots__ = []
            _wf = self

        self.NODE_CLASS = _WFNode_
        super().__init__()

def _collect_operation():
    for key, value in globals().items():
        if isinstance(value, type) and issubclass(value, WFOperation):
            if not key.startswith("_"):
                yield value.operation_name, value

OPERATOR_COLLECTION.update(_collect_operation())
del _collect_operation
