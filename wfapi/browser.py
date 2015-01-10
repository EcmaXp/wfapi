# -*- coding: utf-8 -*-
import threading
from contextlib import closing
from http.client import HTTPConnection, HTTPSConnection
from http.cookiejar import Cookie, CookieJar
from urllib.error import HTTPError
from urllib.parse import urljoin, urlencode, urlparse
from urllib.request import build_opener, HTTPCookieProcessor, Request, \
    HTTPErrorProcessor
import functools
import json


__all__ = ["DefaultBrowser", "BaseBrowser", "BuiltinBrowser", "FastBrowser"]


class BaseBrowser():
    def __init__(self, base_url):
        self.base_url = base_url

    def open(self, url, *, _raw=False, _query=None, **kwargs):
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

    def open(self, url, *, _raw=False, _query=None, **kwargs):
        full_url = urljoin(self.base_url, url)
        if _query is not None:
            full_url += "?" + urlencode(_query)
        
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

    def open(self, url, *, _raw=False, _query=None, **kwargs):
        full_url = urljoin(self.base_url, url)
        if _query is not None:
            full_url += "?" + urlencode(_query)

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


DefaultBrowser = FastBrowser
