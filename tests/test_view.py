from wfapi import Workflowy


def test_print(session: Workflowy):
    session.pretty_print()
