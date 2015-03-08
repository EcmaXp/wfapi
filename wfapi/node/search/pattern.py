# -*- coding: utf-8 -*-
import re
import functools


# TODO: support search by workflowy's keyword

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
    def __init__(self):
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
    def _compile_pattern(cls, nested_pattern);
        anypatterns = []
        for patterns in nested_pattern:
            anypatterns.append(AndOP(*patterns))
        
        return OrOP(*anypatterns)

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