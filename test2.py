import re

t = """
b = {}, n = Class.extend({
init: function (E) {
function J(V) {
    V = V.split(/\s+/);
    for (var U = 0; U < V.length; U++) {
        var T = V[U];
        T.length > 0 && L.push(T)
    }
}
"""

_REGEX_SEARCH_QUOTED_QUERY = re.compile(r'(^|\s)(-?"[^"]*")($|\s)')

class BaseSearcher():
    pass


class DefaultSearcher(BaseSearcher):
    # check document_view.js:9876
    def __init__(self, query):
        self.query = query
        self.pattern = self.compile_patterns(self.parse_query(query))
        
    @classmethod
    def parse_query(cls, query):
        nested_patterns = []
        
        start = end = 0
        while query:
            r = _REGEX_SEARCH_QUOTED_QUERY.match(query)
            if not r:
                break
            
            start, end = r.span()
            nested_patterns += filter(None, query[:start].split())
            nested_patterns.append(r.group(1))
            query = query[end:]
        
        nested_patterns += filter(None, query[end:].split())
        return nested_patterns

    @classmethod
    def compile_patterns(cls, nested_patterns):
        return WFQueryBasedOP(nested_patterns)

    def search(self, node, *, recursion=True, as_flat=True):
        pattern = self.pattern
        
        for subnode, childs in node.walk():
            if pattern.match(subnode):
                yield subnode

r = DefaultSearcher.parse_query("hello -is:completed #test #test432")
print(list(r))    
    
x = """
for (var L = [], K = RegExp('(^|\\s)(-?"[^"]*")($|\\s)', "g"), D = 0;;) {
    var G = K.exec(E);
    if (G == null) break;
    var F = G[0],
        N = G[2];
    G = G.index;
    J(E.substring(D, G));
    L.push(N);
    D = G + F.length
}
J(E.substring(D));
D = E.length > 0 && E.charAt(E.length - 1).match(/\s/) !== null;
F = [];
K = [F];
for (N = 0; N < L.length; N++) {
    var Q = L[N];
    if (Q === "OR") {
        F = [];
        K.push(F)
    } else {
        G = false;
        if (Q.charAt(0) === "-") {
            G = true;
            Q = Q.substring(1);
            if (Q.length === 0) continue
        }
        var W = Q.length >= 2 && Q.charAt(0) === '"' && Q.charAt(Q.length - 1) === '"';
        if (!(W && Q.length === 2)) {
            Q = Q.toLowerCase();
            if (W) {
                Q = Q.substring(1, Q.length - 1);
                Q = new P(Q)
            } else if (utils.isPrefixMatch(Q, "last-changed:")) {
                Q = Q.split(":")[1];
                Q = new B(Q)
            } else if (utils.isPrefixMatch(Q, "completed:")) {
                Q = Q.split(":")[1];
                Q = new C(Q)
            } else Q = Q === "is:shared" ? new H : Q === "is:complete" ? new I : Q === "is:embedded" ? new M : Q === "has:note" ? new O : new A(Q, N === L.length - 1 && !D);
            if (G) Q = new x(Q);
            F.push(Q)
        }
    }
}
"""