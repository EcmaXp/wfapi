#! -*- coding: utf-8 -*-
raise NotImplementedError

# TODO: provide api for ignore html tag when search or etc.
# TODO: remove invaild tag after node load, but touched/readed only.


class HTMLTag():
    tag_name = NotImplemented


class Link(HTMLTag):
    tag_name = "a"

    
class Bold(HTMLTag):
    tag_name = "b"


class Italic(HTMLTag):
    tag_name = "i"


class Underline(HTMLTag):
    tag_name = "u"


def escape():
    pass

def filter_unsafe():
    # TODO: ?
    pass