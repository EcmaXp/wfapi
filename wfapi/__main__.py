#!/usr/bin/env python3
from wfapi import *

def main():
    class DeamonWeakWorkflowy(WFMixinDeamon, WFMixinWeak, Workflowy):
        pass

    wf = DeamonWeakWorkflowy("hBYC5FQsDC")
    wf.start()

    with wf.transaction():
        if not wf.root:
            node = wf.root.create()
        else:
            node = wf.root[0]
            
        node.edit("hello")
        node.is_completed = False

    wf.pretty_print()
    wf.stop()
    
if __name__ == "__main__":
    main()