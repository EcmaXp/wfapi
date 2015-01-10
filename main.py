#!/usr/bin/env python3
import wfapi
import time
import getpass

def main():
    class AutoWeakWorkflowy(wfapi.WFMixinDeamon, wfapi.WeakWorkflowy):
        pass

    wf = AutoWeakWorkflowy("hBYC5FQsDC")
    wf.start()

    with wf.transaction():
        if not wf.root:
            node = wf.root.create()
        else:
            node = wf.root[0]
            
        node.edit("<a href='javascript: alert(32);'>test</a><p>test2</p>")
        node.is_completed = False

    wf.pretty_print()
    wf.stop()
    
if __name__ == "__main__":
    main()