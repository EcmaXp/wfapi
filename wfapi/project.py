import json
import time
import weakref
from contextlib import contextmanager
from datetime import datetime
from typing import Type

from .config import DEFAULT_ROOT_NODE_ID
from .error import WFRuntimeError, WFNodeNotFoundError
from .node import Node
from .operation import Operation, EditOperation, CreateOperation, CompleteOperation, UncompleteOperation, \
    DeleteOperation, OPERATION_REGISTERED
from .quota import Quota, VoidQuota, SharedQuota, DefaultQuota
from .tools import attrdict, uncapdict, generate_uuid

if False:
    from .workflowy import Workflowy

__all__ = ["Project"]


class Project:
    def __init__(self, workflowy, ptree):
        self.workflowy = workflowy  # type: Workflowy
        self.status = attrdict()
        self.quota = VoidQuota()  # type: Quota
        self.root = None
        self.cache = weakref.WeakValueDictionary()
        self.track = {}
        self.operations = []
        self.pending = {}
        self.transaction_level = 0

        self.init(ptree)

    def init(self, ptree):
        # TODO: support auxiliaryProjectTreeInfos for embbed node.
        s = self.status
        s.update(uncapdict(ptree))

        s.most_recent_operation_transaction_id = \
            s.pop("initial_most_recent_operation_transaction_id")

        s.polling_interval = \
            s.pop("initial_polling_interval_in_ms") / 1000

        s.is_shared = s.get("share_type") is not None

        self.quota = SharedQuota() if "over_quota" in s else DefaultQuota()
        self.quota.update(s)

        root_project = s.pop("root_project")
        root_project_children = s.pop("root_project_children")
        self._update_root(root_project, root_project_children)

    def _refresh_project(self, ptree):
        self.init(ptree)

        removed = set()
        for projectid, node in self.cache.items():
            if projectid in self.track:
                path = self.find_path(projectid)
                raw = self.resolve_path(path)
                node.raw = raw
            else:
                # TODO: if node.raw is None, raise error if possible (in Node class)
                node.raw = None
                removed.add(projectid)

        for projectid in removed:
            self.cache.pop(projectid, None)

    def _reset_track(self):
        self.track.clear()

        for parentid, projectid in self._travalse_child(None, self.root.raw):
            self.track[projectid] = parentid

    def _travalse_child(self, parentid, raw):
        projectid = raw["id"]
        yield parentid, projectid

        ch = raw.get("ch")
        if ch is not None:
            for child in ch:
                yield from self._travalse_child(projectid, child)

    def _update_root(self, root_project, root_project_children):
        root = {} if root_project is None else root_project

        root.update(
            # in shared mode, root will have uuid -(replace)> DEFAULT_ROOT_NODE_ID
            id=DEFAULT_ROOT_NODE_ID,

            ch=root_project_children,
        )

        self.root = self.new_node(root)
        self._reset_track()

    def new_node(self, raw=None, projectid=None):
        if raw is None:
            raw = {
                'id': generate_uuid() if projectid is None else projectid,
            }

        node = Node(self, raw)

        if node.projectid in self.track:
            self.cache[node.projectid] = node

        return node

    def find_path(self, projectid):
        seq = []

        while projectid:
            seq.append(projectid)
            projectid = self.track[projectid]

        seq = seq[::-1]
        if not seq:
            raise WFNodeNotFoundError(projectid)

        return seq

    def resolve_path(self, path):
        raw = self.root.raw
        for projectid in path:
            assert 'ch' in raw
            for child in raw['ch']:
                if child['id'] == projectid:
                    raw = child
                    break

        return raw

    def find_parent(self, node: Node) -> Node:
        return self.find_node(node.parentid)

    def find_node(self, projectid, raw=None) -> Node:
        node = self.cache.get(projectid)
        if node is not None:
            return node

        if raw is None:
            path = self.find_path(projectid)
            raw = self.resolve_path(path)

        return self.new_node(raw)

    def find_child(self, node: Node):
        ch = node.raw.get('ch')
        if not ch:
            return

        for child in ch:
            yield self.find_node(child['id'], raw=child)

    def add_node(self, node: Node, parent: Node, update_quota=True):
        cnt = 0
        for cnt, (parentid, projectid) in enumerate(self._travalse_child(parent.projectid, node.raw), 1):
            self.track[projectid] = parentid

        if update_quota:
            self.quota += cnt

    def remove_node(self, node: Node, update_quota=True):
        cnt = 0
        for cnt, (_, projectid) in enumerate(self._travalse_child(node.projectid, node.raw), 1):
            del self.track[projectid]

            node = self.cache.pop(projectid, None)
            if node is not None:
                node.raw = None

        if update_quota:
            self.quota -= cnt

    def update_by_pushpoll(self, res):
        error = res.get("error")
        if error:
            raise WFRuntimeError(error)

        s = self.status
        s.most_recent_operation_transaction_id = \
            res.new_most_recent_operation_transaction_id

        if res.get("need_refreshed_project_tree"):
            self._refresh_project_tree()

        s.polling_interval = res.new_polling_interval_in_ms / 1000
        self.quota.update(res)

        data = json.loads(res.server_run_operation_transaction_json)
        return data

    def _refresh_project_tree(self):
        # TODO: must check root are shared. (share_id and share_type will help)
        self.workflowy.init()

    @contextmanager
    def transaction(self):
        if self.operations is None:
            self.operations = []

        self.transaction_level += 1

        try:
            yield self.operations
        finally:
            self.transaction_level -= 1

        if not self.transaction_level:
            self.commit()

    def commit(self):
        operations = []
        for op in self.operations[:]:  # type: Operation
            op.pre_operation()
            op_json = op.get_operation()
            op_json["client_timestamp"] = self.get_client_timestamp()
            op_json["undo_data"] = op.get_undo()
            operations.append(op_json)
            self.operations.remove(op)

        transaction = dict(
            most_recent_operation_transaction_id=
            self.status.most_recent_operation_transaction_id,
            operations=operations,
        )

        if self.status.is_shared:
            assert self.status.share_type == "url"
            transaction.update(
                share_id=self.status.share_id,
            )

        transactions = [transaction]

        response = self.workflowy._push_and_poll(transactions)
        for result in response['results']:
            error = result.get('error')
            if error:
                raise WFRuntimeError(error)

            server_run_operation_transaction_json = result['server_run_operation_transaction_json']
            server_run_operation_transaction = json.loads(server_run_operation_transaction_json)
            for op_json in server_run_operation_transaction['ops']:
                op_cls: Type[Operation] = OPERATION_REGISTERED[op_json['type']]
                op = op_cls.from_server_operation(self, op_json['data'])
                op.post_operation()

    def op_edit(self, node, name=None, description=None):
        with self.transaction() as tr:
            tr.append(EditOperation(self, node, name=name, description=description))

    def op_create(self, node, priority=-1, child=None):
        if child is None:
            child = self.new_node()

        with self.transaction() as tr:
            tr.append(CreateOperation(self, node, child=child, priority=priority))

        return child

    def op_complete(self, node, modified=None):
        with self.transaction() as tr:
            tr.append(CompleteOperation(self, node, modified=modified))

    def op_uncomplete(self, node):
        with self.transaction() as tr:
            tr.append(UncompleteOperation(self, node))

    def op_delete(self, node):
        with self.transaction() as tr:
            tr.append(DeleteOperation(self, node))

    def op_search(self, node, pattern):
        # pattern is very complex.
        # http://blog.workflowy.com/2012/09/25/hidden-search-operators/
        raise NotImplementedError("search is not implemented yet.")

    def get_client_timestamp(self, current_time=None):
        if current_time is None:
            current_time = time.time()

        return current_time - self.status.date_joined_timestamp_in_seconds

    def get_python_timestamp(self, client_timestamp):
        current_timestamp = self.status.date_joined_timestamp_in_seconds + client_timestamp
        return datetime.fromtimestamp(current_timestamp)

    def find_pending(self, projectid):
        node = self.pending.get(projectid)
        if node is not None:
            return node

        return self.new_node(projectid=projectid)

    def walk(self):
        return self.root.walk()

    def __contains__(self, item):
        if isinstance(item, Node):
            item = item.projectid

        return item in self.track

    def __getitem__(self, projectid):
        return self.find_node(projectid)

    def __len__(self):
        return len(self.track)
