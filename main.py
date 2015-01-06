# import wfapi

class WFRawNode():
    def __init__(self, *a, **b):
        print("init is called with {} and {}".format(a, b))
    
    def __new__(cls):
        raise RuntimeError("it must not inited by user code")
    
    @classmethod
    def test(cls, *a, **b):
        x = super().__new__(cls)
        x.__init__()

print(WFRawNode.test(t=3))

def main():
    class AutoWeakWorkflowy(WeakWorkflowy, WFMixinDeamon):
        pass

    wf = wfapi.WeakWorkflowy("hBYC5FQsDC")
    wf.start()

    with wf.transaction():
        if not wf.root:
            node = wf.root.create()
        else:
            node = wf.root[0]

        node.edit("Welcome Workflowy!", "Last Update: %i" % time.time())
        if not node:
            subnode = node.create()
        else:
            subnode = node[0]

        subnode.name = "Hello world!"
        subnode.is_completed = not subnode.is_completed

    wf.pretty_print()
    
if __name__ == "__main__":
    main()