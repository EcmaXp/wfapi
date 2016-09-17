#!/usr/bin/env python3
from wfapi import *


def main():
    global wf
    wf = Workflowy("hBYC5FQsDC")

    with wf.transaction():
        node = wf.root[0]
        node.name = "hello"
        node.description = "world3"

    wf.pretty_print()

if __name__ == "__main__":
    main()
