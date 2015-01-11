# -*- coding: utf-8 -*-
raise NotImplementedError
from .quota import *
from .nodemgr import *

__all__ = ["WFBaseProject", "WFProject"]

class WFBaseProject(WFNodeManagerInterface):
    NODE_MANAGER_CLASS = NotImplemented

# TODO: support auxiliaryProjectTreeInfos, mainProjectTreeInfo
#       in technical, auxiliaryProjectTreeInfo == mainProjectTreeInfo
# TODO: not only shared node. but also main project.

class WFProject(WFBaseProject):
    NODE_MANAGER_CLASS = WFNodeManager
    
    def __init__(self, project_info):
        self.status = attrdict()
        self.nodemgr = nodemgr
        #self.root = nodemgr.<new_root>?
        self.quota = WFVoidQuota()

        self.update(project_info)

    @property
    def root(self):
        return self.nodemgr.root

    def update_by_init(self, project_info):
        # TODO: support auxiliaryProjectTreeInfos for embbed node.
        s = self.status
        p = project_info

        s.most_recent_operation_transaction_id = p.initialMostRecentOperationTransactionId
        s.date_joined_timestamp_in_seconds = p.dateJoinedTimestampInSeconds
        s.polling_interval = p.initialPollingIntervalInMs / 1000

        # TODO: support is_readonly attribute!
        s.is_readonly = p.isReadOnly

        if p.get("shareType"):
            s.share_type = p.shareType
            s.share_id = p.shareId
        else:
            s.share_type = None
            s.share_id = None

        # project_info also contains overQuota if shared.
        s.is_shared_quota = "overQuota" in p
        # refrash quota class

        if s.is_shared_quota:
            s.is_over_quota = p.overQuota
        else:
            s.items_created_in_current_month = p.itemsCreatedInCurrentMonth
            s.monthly_item_quota = p.monthlyItemQuota

        # TODO: dynamic status update by split by cap char
        # example) itemsCreatedInCurrentMonth -> items_created_in_current_month

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

    def update_quota(self):
        status = self.status
        quota = self.quota

        if status.is_shared_quota:
            quota.is_over = status.is_over_quota
        else:
            quota.used = status.items_created_in_current_month
            quota.total = status.monthly_item_quota
    
    def update_by_status(self):
        self.project_tree.steal(data, "projectTreeData")
        self.main_project.steal(self.project_tree, "mainProjectTreeInfo")
        self._status_update_by_main_project()
        self.nodemgr.update_root(
            root_project=self.main_project.pop("rootProject"),
            root_project_children=self.main_project.pop("rootProjectChildren"),
        )
    
    def update_by_pushpoll(self, res):
        #error = res.get("error")
        #if error:
        #    raise WFRuntimeError(error)
        # already handled by workflowy's <split_update_from_pushpoll>

        status = self.status
        status.most_recent_operation_transaction_id = \
            res.new_most_recent_operation_transaction_id

        if res.get("need_refreshed_project_tree"):
            raise NotImplementedError
            self._refresh_project_tree()
            # XXX how to execute operation after refresh project tree? no idea.

        status.polling_interval = res.new_polling_interval_in_ms / 1000

        if status.is_shared_quota:
            if not isinstance(self.quota, WFSharedQuota):
                self.quota = WFSharedQuota()
            status.is_over_quota = res.over_quota
        else:
            if not isinstance(self.quota, WFQuota):
                self.quota = WFQuota()
            
            status.items_created_in_current_month = \
                res.items_created_in_current_month
            status.monthly_item_quota = res.monthly_item_quota

        self._quota_update()

        data = json.loads(res.server_run_operation_transaction_json)
        return data
    
    def _refresh_project_tree(self):
        nodes = self.nodes
        main_project = self.main_project
        root_project = self.root_project

        # TODO: refreshing project must keep old node if uuid are same.
        # TODO: must check root are shared. (share_id and share_type will help us.)

        raise NotImplementedError
    
    def <transaction>(self):
        # execute transaction...
        pass