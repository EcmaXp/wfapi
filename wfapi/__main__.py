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

        for ch in node:
            ch.delete()

    wf.pretty_print()
    
if __name__ == "__main__":
    main()
