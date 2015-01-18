# -*- coding: utf-8 -*-

class WFBaseSearcher():
    pass


class WFDefaultSearcher(WFBaseSearcher):
    # check document_view.js:9876
    def __init__(self, pattern):
        self.pattern = pattern
        

class WFSpecialSearcher(WFBaseSearcher):
    pass