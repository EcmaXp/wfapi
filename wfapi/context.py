from .operation import OperationCollection

if False:
    from .workflowy import Workflowy
    from .project import Project

class WFContext(OperationCollection):
    def __init__(self, workflowy, project):
        self.workflowy = workflowy # type: Workflowy
        self.project = project # type: Project

    def transaction(self):
        return self.workflowy.transaction(self.project)
