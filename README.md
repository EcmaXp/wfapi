wfapi
=====

Workflowy's Unofficial API for Python3.

Note: This library is *UNSTABLE*.
I suggest use this api with shared note for limit view.

Example
=======


Basic Example
```python
from wfapi import *

wf = Workflowy(...)
node = wf.root.create()
node.edit("Something")
```

Login Example
```python
from wfapi import *

# login by password
Workflowy(username="username", password="password")

# or session id (no second argument)
Workflowy(sessionid="sessionid")

# or just use shared note is good idea
# if https://workflowy.com/s/abcABC1234 is access url
Workflowy("abcABC1234")

# if want to logged state and use shared note
Workflowy("abcABC1234", username="username", password="password")
```

Node operations
```python
from wfapi import *

wf = Workflowy(...)

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
assert subnode2 == node
assert subnode3.parent == node

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

assert self[subnode3.projectid].raw is subnode3.raw

for node in self:
  node.projectid # UUID-like str or "None"(DEFAULT_ROOT_NODE_ID)
  node.last_modified # last modified time in python or workflowy time
  node.name # name
  node.children # children
  node.description # description
  node.completed_at # complete marking time in python or workflowy time (or None)
  node.completed # [READ-ONLY?] boolean value for completed.
  # node.shared
  node.parent # parent node (or None, that is root node)

# just print tree;
wf.root.pretty_print()
# or node.pretty_print()
```

Transaction example (only commit is supported)
```python
from wfapi import *

wf = Workflowy(...)

# transaction make execute command fast. (but there is no rollback)
with wf.transaction():
  for i in range(10):
    subnode3.create()

# threadsafe nested transactions is NOT suppported.
with wf.transaction():
  with wf.transaction():
    # just delete node
    subnode3.delete()
```
