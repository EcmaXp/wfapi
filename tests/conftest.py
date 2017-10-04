import pytest

from wfapi import Workflowy


@pytest.fixture(scope="module")
def session():
    return Workflowy("hBYC5FQsDC")
