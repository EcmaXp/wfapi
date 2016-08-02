# -*- coding: utf-8 -*-
import functools
import re

# TODO: support search by workflowy's keyword

RE_SEARCH_QUOTED_QUERY = re.compile(r'(^|\s)(-?"[^"]*")($|\s)')


@functools.total_ordering
class BasePattern():
    #require_arg = True
    #require_note = False?
    
    priority = 0
    # sort in AndOP for fast calc in large ops.
    
    def __init__(self):
        raise NotImplementedError
    
    def match(self, node):
        raise NotImplementedError

    def __str__(self):
        return "<Unknown Pattern; {!r}>".format(self)

    def __lt__(self, x):
        return self.priority.__lt__(x.priority)

    def __gt__(self, x):
        return self.priority.__gt__(x.priority)

    def __eq__(self, x):
        return self.priority.__eq__(x.priority)
        
    def __ne__(self, x):
        return self.priority.__ne__(x.priority)


class Pattern(BasePattern):
    pass
    

class BitOperationPattern(BasePattern):
    # TODO: if BitPattern are given in patterns, raise error 
    #         because workflowy are not support nested bit operation?
    #         only support: OrOp(AndOp(...))
    pass


class WFQueryBasedOP(BitOperationPattern):
    __slots__ = ["nested_patterns"]
    
    def __init__(self, nested_patterns):
        self.nested_patterns = nested_patterns
        self._pattern = self._compile_pattern(self.nested_patterns)
    
    @classmethod
    def _compile_pattern(cls, nested_pattern):
        any_patterns = []
        for patterns in nested_pattern:
            any_patterns.append(AndOP(*patterns))
        
        return OrOP(*any_patterns)

    def match(self, node):
        return self._pattern.match(node)
        
    def __str__(self):
        return str(self._pattern)


class OrOP(BitOperationPattern):
    __slots__ = ["patterns"]
    
    def __init__(self, *patterns):
        self.patterns = list(patterns)
    
    def __str__(self):
        return " OR ".join(self.patterns)
    
    def match(self, node):
        for pattern in self.patterns:
            if pattern.match(node):
                return True
                
        return False


class AndOP(BitOperationPattern):
    __slots__ = ["patterns", "optimized_patterns"]
    
    def __init__(self, *patterns):
        self.patterns = list(patterns)
        self.optimized_patterns = self._optimize_patterns(self.patterns)

    @classmethod
    def _optimize_patterns(cls, patterns):
        optimized_patterns = sorted(patterns)
        
        if patterns == optimized_patterns:
            # less memory by less list, do reference copy now!
            optimized_patterns = patterns

        return optimized_patterns

    def __str__(self):
        return " ".join(self.patterns)

    def match(self, node):
        for pattern in self.optimized_patterns:
            if not pattern.match(node):
                return False
                
        return True


class NotOP(BitOperationPattern):
    __slots__ = ["pattern"]
    
    def __init__(self, pattern):
        self.pattern = pattern
    
    def match(self, node):
        return not self.pattern.match(node)


class IsCompletedPattern():
    pass


class BaseSearcher():
    def __init__(self, pattern):
        self.pattern = pattern

    def search(self, node, recursion=True):
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
        nested_patterns = cls.parse_query(query)
        compiled_patterns = cls.compile_patterns(nested_patterns)
        return compiled_patterns

    @classmethod
    def parse_query(cls, query):
        nested_patterns = []

        start = end = 0
        while query:
            m = RE_SEARCH_QUOTED_QUERY.match(query)
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
