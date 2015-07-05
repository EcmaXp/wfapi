#!/usr/bin/env python3
from wfapi import *

def main():
    class WeakWorkflowy(WFMixinWeak, Workflowy):
        pass

    wf = WeakWorkflowy("hBYC5FQsDC")
    
    with wf.transaction():
        if not wf.root:
            node = wf.root.create()
        else:
            node = wf.root[0]
            
        node.edit("hello")
        node.is_completed = False
        node2 = node.create()

    wf.pretty_print()
    
if __name__ == "__main__":
    main()