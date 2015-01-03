#!/usr/bin/env python3
import time
a=time.time()
import wfapi
b=time.time()
print(b-a)

def main():
    wf = wfapi.WeakWorkflowy("hBYC5FQsDC")
    # https://workflowy.com/s/hBYC5FQsDC

    with wf.transaction():
        if not wf.root:
            node = wf.root.create()
        else:
            node = wf.root[0]

        node.edit("Welcome Workflowy!", "Last Update: %i" % time.time())
        if not node:
            subnode = node.create()
            subnode.edit("Hello world!")
            subnode.complete()
        else:
            subnode = node[0]

    wf.root.pretty_print()

if __name__ == "__main__":
    main()