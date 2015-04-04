# -*- coding: utf-8 -*-
#raise NotImplementedError
from .quota import *
from ..node.manager import *
from ..utils import uncapdict, uncapword, attrdict
import re

__all__ = ["BaseProject", "Project"]

class BaseProject(NodeManagerInterface):
    NODE_MANAGER_CLASS = NotImplemented
    
    def __init__(self, ptree, *, pm):
        raise NotImplementedError


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
        from pprint import pprint
        pprint(s)
        
        if None:
            s.most_recent_operation_transaction_id
            s.date_joined_timestamp_in_seconds
            s.polling_interval
            
            # TODO: support is_readonly attribute!
            s.is_read_only
            
            s.date_joined_timestamp_in_seconds
            s.items_created_in_current_month

        s.most_recent_operation_transaction_id = \
            s.initial_most_recent_operation_transaction_id
        del s.initial_most_recent_operation_transaction_id
        
        s.polling_interval = \
            s.initial_polling_interval_in_ms / 1000
        del s.initial_polling_interval_in_ms
        
        s.is_shared = s.get("share_type") is not None
        
        self.quota = (SharedQuota if s.get("over_quota") else DefaultQuota)()
        self.quota.update(s)

        self.nodemgr.update_root(
            s.root_project,
            s.root_project_children,
        )
        
        del s.root_project
        del s.root_project_children

    def __contains__(self, node):
        return node in self.nodemgr

    def __getitem__(self, node):
        return self.nodemgr[node]

    def __iter__(self):
        return iter(self.nodemgr)

    def add_node(self, node, recursion=True, update_quota=True):
        added_nodes = self.nodemgr.add(node, recursion=recursion)

        if update_quota:
            self.quota += added_nodes

    def remove_node(self, node, recursion=False, update_quota=True):
        removed_nodes = self.nodemgr.remove(node, recursion=recursion)

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
