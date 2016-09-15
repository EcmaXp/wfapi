import weakref
from .workflowy import BaseWorkflowy
from .operation import OperationCollection


class WFContext(OperationCollection):
    def __init__(self, workflowy:BaseWorkflowy, project):
        self.workflowy = workflowy
        self.project = weakref.ref(project)

    def transaction(self):
        return self.workflowy.transaction(self.context)
