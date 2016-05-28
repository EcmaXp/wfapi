Workflowy Python3 API
=====================
Note: This api is *UNSTABLE*.

Workflowy: Organize your brain.
But did you think about what if workflowy can access by API?

This module provide api for workflowy with python3.

You can add node, edit, complete, or uncomplete, etc.

Example
-------
Normal `Workflowy` and `WeakWorkflowy`(require new class) are different.
```python
from wfapi import *

# normal mode
wf = Workflowy(...)
node = wf.create(wf.root)
wf.edit(node, "Something")

# weak mode
class WeakWorkflowy(WFMixinWeak, Workflowy):
    pass

wf = WeakWorkflowy(...)
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

Deamon (+ Weak) Example
```python
from wfapi import *

class DeamonWeakWorkflowy(WFMixinDeamon, WFMixinWeak, Workflowy):
    pass

wf = DeamonWorkflowy(...)
wf.start()
node = wf.create(wf.root)
node.edit("Something")
wf.stop()
```

Node operations
```python
from wfapi import *
class WeakWorkflowy(Workflowy):
    pass

wf = WeakWorkflowy(...)

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

# just print tree;
wf.root.pretty_print()
# or node.pretty_print()
```

Transaction example (only commit are supported)
```python
from wfapi import *
class WeakWorkflowy(WFMixinWeak, Workflowy):
    pass

wf = WeakWorkflowy(...)

# transaction make execute command fast, support rollback yet.
with wf.transaction():
  for i in range(10):
    subnode3.create()

# also nested transaction are suppported, with thread safe.
with wf.transaction():
  with wf.transaction():
    # just delete node
    subnode3.delete()
```