import pytest

from wfapi import WFMixinWeak, Workflowy


class WeakWorkflowy(Workflowy, WFMixinWeak):
    pass


@pytest.fixture(scope="module")
def session():
    return WeakWorkflowy("hBYC5FQsDC")
