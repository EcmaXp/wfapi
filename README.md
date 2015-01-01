wfapi
=====

Workflowy's Dirty & Unoffical API for Python3.

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
wf = wfapi.Workflowy(...)
node = wf.create(wf.root)
wf.edit(node, "Something")

# weak mode
wf = wfapi.WeakWorkflowy(...)
node = wf.root.create()
node.edit("Something")
```

Login Example
```python
# login by password
wfapi.Workflowy(username="username", password="password")

# or session id (no second argument)
wfapi.Workflowy(sessionid="sessionid")

# or just use shared note is good idea
# if https://workflowy.com/s/abcABC1234 is access url
wfapi.Workflowy("abcABC1234")

# if want to logged state and use shared note
wfapi.Workflowy("abcABC1234", username="username", password="password")
```

Node operations
```python
wf = wfapi.WeakWorkflowy(...)

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

assert self[subnode3.projectid] is subnode3

for node in self:
  node.projectid # UUID-like str or "None"(DEFAULT_ROOT_NODE_ID)
  node.last_modified # last modified time.
  node.name # name
  node.children # children (or just iter node)
  node.description # description
  node.completed_at # complete marking time (or None)
  node.completed # [READ-ONLY] boolean value for completed.
  node.shared # [UNSTABLE] shared infomation
  node.parent # parent node (or None, that is root node)

# transaction make execute command fast, support rollback yet.
with wf.transaction():
  for i in range(10):
    subnode3.create()

# also nested transaction are suppported, with thread safe.
with wf.transaction():
  with wf.transaction():
    # just delete node
    subnode3.delete()

# just print tree;
wf.root.pretty_print()
# or node.pretty_print()
```
