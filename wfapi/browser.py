# -*- coding: utf-8 -*-

import functools
from urllib.parse import urlencode, urljoin

import requests

from . import config

__all__ = ["DefaultBrowser", "RequestsBrowser"]


def get_default_workflowy_url(base_url):
    if base_url is None:
        return config.DEFAULT_WORKFLOWY_URL

    return base_url


class Browser:
    def __init__(self, base_url=None):
        self.base_url = get_default_workflowy_url(base_url)

    def open(self, url, _raw=False, _query=None, **kwargs):
        raise NotImplementedError

    def set_cookie(self, name, value):
        raise NotImplementedError

    def __getitem__(self, url):
        return functools.partial(self.open, url)

    def reset(self):
        # TODO: support reset cookies?
        pass


class RequestsBrowser(Browser):
    def __init__(self, base_url=None):
        super().__init__(base_url=base_url)
        self.session = requests.Session()

    def open(self, url, _raw=False, _query=None, **kwargs):
        url = urljoin(self.base_url, url)

        data = None
        if kwargs:
            data = urlencode(kwargs).encode()

        method = 'POST' if data else 'GET'

        res = self.session.request(
            method=method,
            url=url,
            params=_query,
            data=data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )

        content = res.json() if not _raw else res.content.decode('utf-8', 'replace')

        return res, content

    def set_cookie(self, name, value):
        self.session.cookies.set(name, value)


DefaultBrowser = RequestsBrowser
