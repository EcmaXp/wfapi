import weakref
from .operation import OperationCollection


class WFContext(OperationCollection):
    def __init__(self, workflowy, project):
        self.workflowy = workflowy
        self.project = project

    def transaction(self):
        return self.workflowy.transaction(self.project)
