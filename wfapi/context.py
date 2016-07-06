import weakref
from .base import BaseWorkflowy, BaseTransaction, BaseProject
from .project import BaseProject
from .transaction import BaseTransaction

# TODO: assign activated context.
class WFContext():
    def __init__(self, workflowy:BaseWorkflowy, project:BaseProject):
        self.workflowy = workflowy
        self.project = weakref.ref(project)
        self.transactions = []

    def push_transaction(self, transaction:BaseTransaction):
        pass
