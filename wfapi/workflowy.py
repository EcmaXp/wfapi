import json
import sys
from contextlib import contextmanager
from typing import List

from .browser import DefaultBrowser, Browser
from .config import DEFAULT_WORKFLOWY_CLIENT_VERSION
from .error import WFLoginError
from .node import Node
from .parse import get_globals_from_home
from .project import Project
from .tools import attrdict, generate_tid

__all__ = ["Workflowy"]


class Workflowy:
    client_version = DEFAULT_WORKFLOWY_CLIENT_VERSION

    def __init__(self, share_id=None, sessionid=None, username=None, password=None, browser: Browser = None):
        self.share_id = share_id
        self.browser = DefaultBrowser() if browser is None else browser
        self.globals = attrdict()
        self.settings = attrdict()
        self.user_id = None
        self.main = None  # type: Project
        self.sub = []  # type: List[Project]

        if sessionid is not None or username is not None:
            username_or_sessionid = sessionid or username
            self.login(username_or_sessionid, password)

        self.init()

    @property
    def root(self) -> Node:
        """
        Access the main project's root node.

        :return: main project root node
        :rtype: wfapi.node.Node
        """
        return self.main.root

    def login(self, username_or_sessionid, password=None, use_ajax_login=True):
        """
        Login the workflowy website by username/password or sessionid (from cookies)

        :param username_or_sessionid: username or session id
        :param password: if password provied, try login with username/password.
        :param use_ajax_login: login by ajax method
        """
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
                    self.handle_login_failed()
            else:
                res, data = self.browser["accounts/login/"](
                    username=username, password=password, next="", _raw=True)

    def handle_login_failed(self):
        "handle login failed"
        raise WFLoginError()

    def handle_logout(self):
        "handle logout (default = raise the WFLoginError)"
        raise WFLoginError()

    def init(self):
        "Autometic called by __init__(), don't call directly until required."
        data = self._get_initialization_data()
        _, home_content = self.browser[""](_raw=True)

        self.globals.update(get_globals_from_home(home_content))
        self.globals.update(data["globals"])
        self.settings.update(data["settings"])

        self.user_id = int(self.globals['USER_ID'])

        ptree = data["projectTreeData"]
        self._build_projects_from_ptree(ptree)

        self.client_id = ptree["clientId"]

    def _build_projects_from_ptree(self, ptree):
        if self.main is None:
            self.main = Project(self, ptree["mainProjectTreeInfo"])
        else:
            self.main._refresh_project(ptree["mainProjectTreeInfo"])

        # TODO: _refresh_project on sub project
        for sub_ptree in ptree["auxiliaryProjectTreeInfos"]:
            self.sub.append(Project(self, sub_ptree))

    def _get_initialization_data(self):
        info = dict(
            client_version=self.client_version,
        )

        if self.share_id is not None:
            info.update(share_id=self.share_id)

        def get_initialization_data():
            try:
                _, data = self.browser["get_initialization_data"](_query=info)
                return data
            except Exception as e:
                raise WFLoginError from e

        try:
            return get_initialization_data()
        except WFLoginError:
            self.handle_logout()
            return get_initialization_data()

    def _push_and_poll(self, transaction):
        info = dict(
            client_id=self.client_id,
            client_version=self.client_version,
            push_poll_id=generate_tid(),
            push_poll_data=json.dumps(transaction),
            crosscheck_user_id=self.user_id,
        )

        mpstatus = self.main.status
        if mpstatus.get("share_type") is not None:
            assert mpstatus.share_type == "url"
            info.update(share_id=mpstatus.share_id)

        _, data = self.browser["push_and_poll"](**info)

        return data

    @contextmanager
    def transaction(self):
        """
        Start new transaction, contextmanager used.
        """
        with self.main.transaction() as tr:
            yield tr

    def pretty_print(self, stream=sys.stdout, indent=0):
        return self.root.pretty_print(stream=stream, indent=indent)
