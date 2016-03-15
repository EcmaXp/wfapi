# -*- coding: utf-8 -*-
import re

from .pattern import *

__all__ = ["DefaultSearcher", "Searcher", "SpecialSearcher"]

_REGEX_SEARCH_QUOTED_QUERY = re.compile(r'(^|\s)(-?"[^"]*")($|\s)')


class BaseSearcher():
    def __init__(self, pattern):
        self.pattern = pattern
    
    def search(self, node, *, recursion=True):
        pattern = self.pattern
        
        if recursion:
            for node, childs in node.fast_walk():
                if pattern.match(node):
                    yield node
        else:
            if pattern.match(node):
                yield node

class Searcher(BaseSearcher):
    pass


class DefaultSearcher(BaseSearcher):
    # check document_view.js:9876
    def __init__(self, query):
        self.query = query
        super().__init__(self.process_query(query))
        
    @classmethod
    def process_query(cls, query):
        nested_patterns = self.parse_query(query)
        compiled_patterns = self.compile_patterns(nested_patterns)
        return compile_patterns
        
    @classmethod
    def parse_query(cls, query):
        nested_patterns = []
        
        start = end = 0
        while query:
            m = _REGEX_SEARCH_QUOTED_QUERY.match(query)
            if not m:
                break
            
            start, end = m.span()
            nested_patterns += filter(None, query[:start].split())
            nested_patterns.append(m.group(1))
            query = query[end:]
        
        nested_patterns += filter(None, query[end:].split())
        return nested_patterns

    @classmethod
    def compile_patterns(cls, nested_patterns):
        return WFQueryBasedOP(nested_patterns)
