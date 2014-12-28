wfapi
=====

"in Vacation. i coding it."

Workflowy's Unoffical Simple API for Python3.

No license, but created by @sigsrv.

Note: This api is *VERY UNSTABLE*. i suggest use this api with shared note for limit view.

Features:
* Something do with node.
* Access shared note.
* Support transaction (commit only -_-;)
* Easy use.
* Login and session

Support operation:
* create
* edit
* delete
* complete
* uncomplete

Not Support Yet:
* expend node
* undo
* refresh 
* rollback transaction
* deamon croller
* quota control
* pro features

Example
=======

Normal `Workflowy` and `WeakWorkflowy` are different.
```python
import wfapi

# normal mode
wf = wfapi.Workflowy()
wf.login(...)
node = wf.create(wf.root)
wf.edit(node, "Something")

# weak mode
wf = wfapi.WeakWorkflowy()
wf.login(...)
node = wf.root.create()
node.edit("Something")
```

Login Example
```python
# login by password
wf.login("username", "password")

# or session id (no second argument)
wf.login("sessionid")'

# or just use shared note is good idea
# if https://workflowy.com/s/abcABC1234 is access url
wf.init("abcABC1234")

# if want to logged state and use shared note
wf.login(..., auto_init=False)
wf.init("abcABC1234")
```

Node operations
```python
wf = wfapi.WeakWorkflowy()
wf.login(...)

# create nodes
node = wf.root.create()
node2 = wf.root.create()
assert not node
assert node2 not in node

# node relation
subnode = node.create()
subnode2 = node.create()
subnode3 = node.create()
assert node
assert len(node) == 3
assert subnode2 in node
assert subnode3.parent is node

# node support iter
for some in node:
  if subnode == some:
    break
else:
  assert False

subnode.edit("Welcome")
subnode.delete()
assert len(node) == 1

# edit node and marked as complete
subnode2.edit("test")
subnode2.edit(description="Welcome")
subnode2.complete()

# edit node
subnode3.edit("test2")
subnode3.uncomplete()

# change later, like "self[node.id] is node"
assert self.nodes[subnode3.uuid] is subnode3

# change later, like "for node in self"
# this is internal, i will add node_manger later.
for node in self.nodes.values():
  node.id # UUID or "None"(DEFAULT_ROOT_NODE_ID)
  node.lm # last modify time.
  node.nm # name
  node.ch # children (can be None for memory, calling node.ready_ch() will give node.ch to list)
  node.no # description
  node.cp # complete marking time. (cp is None -> uncompleted, is not None -> completed)
  node.shared # shared infomation
  node.parent # parent node; root node don't have parent.

# transaction make execute command fast.
# support rollback yet.
with wf.transaction():
  for i in range(10):
    subnode3.create()

# just delete node
subnode3.delete()

# just print tree;
wf.root.pretty_print()
# or node.pretty_print()
```
