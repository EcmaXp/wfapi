import wfapi
import time

def main():
    wf = wfapi.WeakWorkflowy()
    wf.login("050986bf381acc21e56dc3ca59c2c18b")
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

    wf.root.pretty_print()

if __name__ == "__main__":
    main()
