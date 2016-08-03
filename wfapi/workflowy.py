# -*- coding: utf-8 -*-
"""Provide Workflowy access

>>> Workflowy("")

"""

import json

from .base import BaseWorkflowy
from .browser import DefaultBrowser
from .const import DEFAULT_WORKFLOWY_CLIENT_VERSION
from .error import WFLoginError, WFRuntimeError
from .operation import OperationCollection
from .project import ProjectManager
from .tools import get_globals_from_home
from .transaction import TransactionManager
from .utils import attrdict, pprint, capture_http404, generate_tid

__all__ = ["Workflowy"]


class Workflowy(BaseWorkflowy, OperationCollection):
    client_version = DEFAULT_WORKFLOWY_CLIENT_VERSION

    def __init__(self, share_id=None, sessionid=None,
                 username=None, password=None):
        self._inited = False

        # TODO: proxy self for remove leak
        self.browser = DefaultBrowser()
        self.globals = attrdict()
        self.settings = attrdict()
        self.pm = ProjectManager(self)
        self.tm = TransactionManager(self)

        if sessionid is not None or username is not None:
            username_or_sessionid = sessionid or username
            self.login(username_or_sessionid, password)

        self.init(share_id)

    @property
    def root(self):
        return self.pm.main.root

    def _reset(self):
        self.handle_reset()
        self.browser.reset()

        self.globals.clear()
        self.settings.clear()

        self.pm.clear()
        self.tm.clear()

    def __contains__(self, node):
        return node in self.pm.main

    def __getitem__(self, node):
        return self.pm.main[node]

    def __iter__(self):
        return iter(self.pm.main)

    def add_node(self, node, recursion=True, update_quota=True):
        self.pm.main.add_node(node, recursion=recursion,
                              update_quota=update_quota)

    def remove_node(self, node, recursion=False, update_quota=True):
        self.pm.main.remove_node(node, recursion=recursion,
                                 update_quota=update_quota)

    def print_status(self):
        pprint(vars(self), width=240)

    def _login_failed(self):
        self.inited = False
        raise WFLoginError("Login Failure.")

    def handle_logout(self):
        self._login_failed()

    def login(self, username_or_sessionid, password=None,
              auto_init=True, use_ajax_login=True):
        home_content = None

        if password is None:
            session_id = username_or_sessionid
            self.browser.set_cookie("sessionid", session_id)
        else:
            username = username_or_sessionid
            if use_ajax_login:
                res, data = self.browser["ajax_login"](username=username,
                                                       password=password)
                errors = data.get("errors")
                if errors:
                    # 'errors' or 'success'
                    self._login_failed()
            else:
                res, data = self.browser["accounts/login/"](
                    username=username, password=password, next="", _raw=True)
                home_content = data

        if auto_init:
            return self.init(home_content=home_content)

    def _get_initialization_data(self, share_id=None):
        info = dict(
            client_version=self.client_version,
        )

        if share_id is not None:
            info.update(share_id=share_id)

        def get_initialization_data():
            with capture_http404(WFLoginError):
                _, data = self.browser["get_initialization_data"](_query=info)
                return data

        try:
            return get_initialization_data()
        except WFLoginError:
            self.handle_logout()
            return get_initialization_data()

    def _init(self, share_id=None, home_content=None):
        data = self._get_initialization_data(share_id=share_id)

        if home_content is None:
            _, home_content = self.browser[""](_raw=True)
        self.globals.update(get_globals_from_home(home_content))

        data = attrdict(data)
        self.globals.update(data.globals)
        self.settings.update(data.settings)

        ptree = data["projectTreeData"]
        self.pm.init(
            ptree["mainProjectTreeInfo"],
            ptree["auxiliaryProjectTreeInfos"],
        )

        self.client_id = ptree["clientId"]
        self.handle_init()
        self.inited = True

    def transaction(self, project=None, force_new_transaction=False):
        assert not force_new_transaction
        if project is None:
            project = self.pm.main

        return self.tm.new_transaction(project)

    def new_transaction(self, project):
        return self.transaction(project)

    def _refresh_project_tree(self):
        # nodes = self.nodes
        # main_project = self.pm.main_project
        # root_project = self.root_project

        # TODO refreshing project must keep old node if uuid are same.
        # TODO must check root are shared (share_id and share_type will help)

        raise NotImplementedError

    def push_and_poll(self, transactions=None, from_tm=False):
        assert from_tm is True
        if transactions is None:
            transactions = []

        info = self._push_and_poll(transactions)
        self._handle_errors_by_push_and_poll(info)

        if not from_tm:
            return self.tm._execute_server_transactions(info)

        return map(attrdict, info.get("results", []))

    def _push_and_poll(self, transactions):
        info = dict(
            client_id=self.client_id,
            client_version=self.client_version,
            push_poll_id=generate_tid(),
            push_poll_data=json.dumps(transactions),
        )

        mpstatus = self.pm.main.status
        if mpstatus.get("share_type") is not None:
            assert mpstatus.share_type == "url"
            info.update(share_id=mpstatus.share_id)

        _, data = self.browser["push_and_poll"](**info)
        return data

    def _handle_errors_by_push_and_poll(self, data):
        error = data.get("error")
        if error:
            raise WFRuntimeError(error)

        logged_out = data.get("logged_out")
        if logged_out:
            raise WFLoginError("logout detected, don't share "
                               "session with real user.")

    def pretty_print(self):
        self.pm.main.pretty_print()

        # TODO: sub project?
        for project in self.pm:
            if self.pm.main == project:
                continue

            project.pretty_print()
