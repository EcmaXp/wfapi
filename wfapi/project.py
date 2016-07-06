# -*- coding: utf-8 -*-
import json

from .base import BaseProject
from .error import WFRuntimeError
from .node import NodeManager
from .quota import *
from .utils import attrdict, uncapdict

__all__ = ["Project", "ProjectManager"]


# TODO: support auxiliaryProjectTreeInfos, mainProjectTreeInfo
#       in technical, auxiliaryProjectTreeInfo == mainProjectTreeInfo
# TODO: not only shared node. but also main project.
# TODO: embedded support in here, and node's support are in node.embedded


class Project(BaseProject):
    NODE_MANAGER_CLASS = NodeManager
    
    def __init__(self, ptree, *, pm):
        self.status = attrdict()
        # [!] Cycle reference
        self.nodemgr = self.NODE_MANAGER_CLASS(self)
        self.quota = VoidQuota()
        self.pm = pm
        self.init(ptree)

    @property
    def wf(self):
        return self.pm.wf

    @property
    def root(self):
        return self.nodemgr.root

    def init(self, ptree):
        # TODO: support auxiliaryProjectTreeInfos for embbed node.
        s = self.status
        s.update(uncapdict(ptree))

        s.most_recent_operation_transaction_id = \
            s.initial_most_recent_operation_transaction_id
        del s.initial_most_recent_operation_transaction_id
        
        s.polling_interval = \
            s.initial_polling_interval_in_ms / 1000
        del s.initial_polling_interval_in_ms
        
        s.is_shared = s.get("share_type") is not None
        
        self.quota = (SharedQuota if "over_quota" in s else DefaultQuota)()
        self.quota.update(s)

        self.nodemgr.update_root(
            s.root_project,
            s.root_project_children,
        )
        
        del s.root_project
        del s.root_project_children

    def __contains__(self, projectid):
        return node in self.nodemgr

    def __getitem__(self, projectid):
        return self.nodemgr[projectid]

    def _find_node(self, projectid):
        def walk(node, parent=[]):
            for child in node:
                node = walk(child)
                if node is not None:
                    return node


        return walk(self.root.raw)

    def __iter__(self):
        return iter(self.nodemgr)

    def add_node(self, node, recursion=True, update_quota=True):
        NotImplemented
        added_nodes = 1

        if update_quota:
            self.quota += added_nodes

    def remove_node(self, node, recursion=False, update_quota=True):
        NotImplemented
        removed_nodes = 1

        if update_quota:
            self.quota -= removed_nodes

    @property
    def pretty_print(self):
        return self.nodemgr.pretty_print
    
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
        nodes = self.nodes
        main_project = self.main_project
        root_project = self.root_project

        # TODO: refreshing project must keep old node if uuid are same.
        # TODO: must check root are shared. (share_id and share_type will help us.)

        raise NotImplementedError
    
    def transaction(self):
        return self.wf.new_transaction(self)


class ProjectManager():
    MAIN_PROJECT_CLASS = Project
    PROJECT_CLASS = Project

    def __init__(self, wf):
        self.wf = wf
        self.main = None
        self.sub = []

    def clear(self):
        self.main = None
        self.sub[:] = []

    def init(self, main_ptree, auxiliary_ptrees):
        self.main = self.build_main_project(main_ptree)

        for ptree in auxiliary_ptrees:
            project = self.build_project(ptree)
            self.sub.append(project)

        return self.main

    def __iter__(self):
        yield self.main
        for project in self.sub:
            yield project

    def build_main_project(self, ptree):
        return self.MAIN_PROJECT_CLASS(ptree, pm=self)

    def build_project(self, ptree):
        return self.PROJECT_CLASS(ptree, pm=self)
