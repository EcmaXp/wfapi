# -*- coding: utf-8 -*-

class BaseSearcher():
    pass


class WFDefaultSearcher(BaseSearcher):
    # check document_view.js:9876
    def __init__(self, pattern):
        self.pattern = pattern
        

class WFSpecialSearcher(BaseSearcher):
    pass