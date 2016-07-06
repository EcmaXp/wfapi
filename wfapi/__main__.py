#!/usr/bin/env python3
from wfapi import *


class WeakWorkflowy(WFMixinWeak, Workflowy):
    pass


def main():
    global wf
    wf = WeakWorkflowy("hBYC5FQsDC")
    
    with wf.transaction():
        if not wf.root:
            node = wf.root.create()
        else:
            node = wf.root[0]

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

        assert wf[subnode3.projectid] is subnode3

        for node in wf:
            node.projectid  # UUID-like str or "None"(DEFAULT_ROOT_NODE_ID)
            node.last_modified  # last modified time.
            node.name  # name
            node.children  # children (or just iter node)
            node.description  # description
            node.completed_at  # complete marking time (or None)
            node.completed  # [READ-ONLY] boolean value for completed.
            node.shared  # [UNSTABLE] shared infomation
            node.parent  # parent node (or None, that is root node)

        if not wf.root:
            node = wf.root.create()
        else:
            node = wf.root[0]

        for ch in node:
            ch.delete()

    wf.pretty_print()
    
if __name__ == "__main__":
    main()
