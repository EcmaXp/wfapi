wfapi
=====

Workflowy's Unofficial API for Python3.

This library is ***UNSTABLE!*** (sorry)

```python3
# create nodes
node = session.root.create()
node2 = session.root.create()
assert not node
assert node2 not in node

# node relation
subnode = node.create()
subnode2 = node.create()
subnode3 = node.create()
assert node
assert len(node) == 3
assert subnode2.parent == node
assert subnode3.parent == node

# node support iter
for some in node:
    if subnode == some:
        break
else:
    assert False

subnode.edit("Welcome")
subnode.delete()
assert len(node) == 2

# edit node and marked as complete
subnode2.edit("test")
subnode2.edit(description="Welcome")
subnode2.complete()

# edit node
subnode3.edit("test2")
subnode3.uncomplete()

assert session.main[subnode3.projectid].raw is subnode3.raw

nodes = {node, node2, subnode2, subnode3}

for node in session.root.walk():
    node.projectid  # UUID-like str or "None"(DEFAULT_ROOT_NODE_ID)
    node.last_modified  # last modified time in python or workflowy time
    node.name  # name
    node.children  # children
    node.description  # description
    node.completed_at  # complete marking time in python or workflowy time (or None)
    node.is_completed  # [READ-ONLY?] boolean value for completed.
    node.shared
    node.parent  # parent node (or None, that is root node)

# just print tree;
session.root.pretty_print()
# or node.pretty_print()

with session.transaction():
    for node in nodes:
        node.delete()
```
