# -*- coding: utf-8 -*-

import json
import weakref
from weakref import WeakValueDictionary

from .const import DEFAULT_ROOT_NODE_ID
from .context import WFContext
from .error import WFRuntimeError
from .node import Node
from .quota import VoidQuota, SharedQuota, DefaultQuota
from .tools import attrdict, uncapdict, generate_uuid

__all__ = ["Project", "ProjectManager"]


# TODO: support auxiliaryProjectTreeInfos, mainProjectTreeInfo
#       in technical, auxiliaryProjectTreeInfo == mainProjectTreeInfo
# TODO: not only shared node. but also main project.
# TODO: embedded support in here, and node's support are in node.embedded


class Project():
    def __init__(self, workflowy, ptree):
        self.context = WFContext(workflowy, weakref.proxy(self))
        self.status = attrdict()
        self.quota = VoidQuota()

        self.data = WeakValueDictionary()
        self.root = None
        self.cache = {}

        self.init(ptree)

    def __contains__(self, item):
        if isinstance(item, Node):
            item = item.projectid

        return item in self.cache

    def __getitem__(self, projectid):
        return self.node_from_raw(self.cache[projectid])

    def init(self, ptree):
        # TODO: support auxiliaryProjectTreeInfos for embbed node.
        s = self.status
        s.update(uncapdict(ptree))

        s.most_recent_operation_transaction_id = \
            s.pop("initial_most_recent_operation_transaction_id")

        s.polling_interval = \
            s.pop("initial_polling_interval_in_ms") / 1000

        s.is_shared = s.get("share_type") is not None

        self.quota = (SharedQuota if "over_quota" in s else DefaultQuota)()
        self.quota.update(s)

        self.update_root(
            s.pop("root_project"),
            s.pop("root_project_children"),
        )

    def update_root(self, root_project, root_project_children):
        self.root = self.new_root_node(root_project, root_project_children)
        cache = self.cache

        # TODO: how to cache parent?

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

    def new_void_node(self, projectid=None):
        return Node(self.context, {'id': projectid if projectid else generate_uuid()})

    def node_from_raw(self, raw):
        return Node(self.context, raw)

    def _walk(self, raw=None):
        if raw is None:
            raw = self.root.raw

        yield raw

        ch = raw.get("ch")
        if ch is not None:
            walk = self._walk
            for child in ch:
                yield from walk(child)

    def add_node(self, node, recursion=True, update_quota=True):
        NotImplemented
        added_nodes = 1

        if update_quota:
            self.quota += added_nodes

        self.cache[node.projectid] = node.raw

    def remove_node(self, node, recursion=False, update_quota=True):
        NotImplemented
        removed_nodes = 1

        if update_quota:
            self.quota -= removed_nodes

    def update_by_pushpoll(self, res):
        # like workflowy.update_by_pushpollsub
        error = res.get("error")
        if error:
            raise WFRuntimeError(error)

        s = self.status
        s.most_recent_operation_transaction_id = \
            res.new_most_recent_operation_transaction_id

        if res.get("need_refreshed_project_tree"):
            self._refresh_project_tree()
            # XXX how to execute operation after refresh project tree? no idea.

        s.polling_interval = res.new_polling_interval_in_ms / 1000
        self.quota.update(res)

        data = json.loads(res.server_run_operation_transaction_json)
        return data

    def _refresh_project_tree(self):
        # TODO: refreshing project must keep old node if uuid are same.
        # TODO: must check root are shared. (share_id and share_type will help)

        raise NotImplementedError

    @property
    def pretty_print(self):
        return self.root.pretty_print


class ProjectManager():
    def __init__(self, workflowy):
        self.wf = workflowy
        self.main = None
        self.sub = []

    def clear(self):
        self.main = None
        self.sub[:] = []

    def init(self, main_ptree, auxiliary_ptrees):
        self.main = self.build_project(main_ptree)

        for ptree in auxiliary_ptrees:
            project = self.build_project(ptree)
            self.sub.append(project)

        return self.main

    def __iter__(self):
        yield self.main
        for project in self.sub:
            yield project

    def build_project(self, ptree):
        return Project(self.wf, ptree)
