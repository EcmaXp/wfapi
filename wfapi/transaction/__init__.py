# -*- coding: utf-8 -*-
from .. import utils
from ..error import WFTransactionError
import time

__all__ = ["BaseTransaction", "ServerTransaction", "ClientTransaction",
    "SimpleSubClientTransaction", "DeamonSubClientTransaction"]

# TODO: Transaction must support splited projects!

class BaseTransaction():
    __slots__ = ["wf", "operations", "is_locked", "is_executed"]

    def __init__(self, wf):
        self.wf = wf
        self.operations = []
        self.is_executed = False
        self.is_locked = False

    def assert_pushable(self, operation=None):
        if not self.is_locked:
            return

        if operation is None:
            raise WFTransactionError("{!r} is locked".format(self))
        else:
            raise WFTransactionError("{!r} is locked, while push {!r}".format(self, operation))

    def get_client_timestamp(self, current_time=None):
        raise NotImplementedError

    def push(self, operation):
        raise NotImplementedError

    def pre_operation(self):
        for operation in self:
            operation.pre_operation(self)

    def post_operation(self):
        for operation in self:
            operation.post_operation(self)

    def handle_enter(self):
        pass
    
    def handle_exit(self, error):
        self.is_locked = True
        self.commit()

    def __iter__(self):
        return iter(self.operations)

    def __iadd__(self, other):
        self.push(other)

    def __enter__(self):
        self.handle_enter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.handle_exit(error=True)
            return False
        else:
            self.handle_exit(error=False)
        return False

    def commit(self):
        raise NotImplementedError

    def rollback(self):
        raise NotImplementedError


class ProjectBasedTransaction(BaseTransaction):
    __slots__ = ["project"]
    
    def __init__(self, wf, project):
        super().__init__(wf)
        self.project = project

    def handle_exit(self, error):
        self.is_locked = True
        if not self.is_executed:
            self.commit()
            self.is_executed = True

class ServerTransaction(ProjectBasedTransaction):
    def __init__(self, wf, project, client_tr, client_timestamp):
        super().__init__(wf, project)
        self.client_timestamp = client_timestamp
        self.client_transaction = client_tr

    @classmethod
    def from_server(cls, wf, project, client_tr, data):
        client_timestamp = data["client_timestamp"]
        self = cls(wf, project, client_tr, client_timestamp)

        client_operations = list(self.get_client_operations_json())
        def pop_client_operation():
            if client_operations:
                return client_operations.pop(0)

            return None

        current_client_operation = pop_client_operation()

        for op in data["ops"]:
            op.pop("server_data", None)
            # server_data are exists when server_info

            if current_client_operation == op:
                # is it safe?
                current_client_operation = pop_client_operation()
                continue

            # TODO: change OPERATOR_COLLECTION?
            operator = OPERATOR_COLLECTION.get(op["type"], _UnknownOperation)
            operation = operator.from_server_operation_json(self, op)
            self.push(operation)

        return self

    def get_client_operations_json(self):
        client_tr = self.client_transaction
        for operation in client_tr:
            yield operation.get_cached_operation(client_tr)
            # not get_client_operation

    def get_client_timestamp(self, current_time=None):
        assert current_time is None
        return self.client_timestamp

    def push(self, operation):
        self.assert_pushable(operation)
        self.operations.append(operation)

    def commit(self):
        self.pre_operation()
        self.post_operation()


class ClientTransaction(ProjectBasedTransaction):
    def __init__(self, wf, project):
        super().__init__(wf, project)
        self.level = 0
    
    def get_client_timestamp(self, current_time=None):
        if current_time is None:
            current_time = time.time()

        pstatus = self.project.status
        # TODO: use workflowy.timestamp!
        return (current_time - pstatus.date_joined_timestamp_in_seconds) // 60

    def push(self, operation):
        # TODO: determine good position for pre_operation and post_operation
        # XXX: if pre_operation and post_operation in push_poll function, transaction are not work.
        self.assert_pushable(operation)

        operation.pre_operation(self)
        self.operations.append(operation)
        operation.post_operation(self)

    def get_operations_json(self):
        operations = []
        for operation in self:
            operations.append(operation.get_client_operation(self))

        return operations

    def get_transaction_json(self, operations=None):
        pstatus = self.project.status
        
        if operations is None:
            operations = self.get_operations_json()

        transaction = dict(
            most_recent_operation_transaction_id = 
                pstatus.most_recent_operation_transaction_id,
            operations=operations,
        )
        
        if pstatus.is_shared:
            assert pstatus.share_type == "url"
            transaction.update(
                share_id=pstatus.share_id,
            )

        return transaction

    def handle_enter(self):
        self.level += 1

    def handle_exit(self, error):
        self.level -= 1
        if self.level == 0:
            if self.is_executed:
                raise WFTransactionError("{!r} is already executed".format(self))

            super().handle_exit(error)

    def commit(self):
        return self.get_transaction_json()


class SimpleSubClientTransaction(ClientTransaction):
    def __init__(self, wf, tr):
        self.wf = wf
        self.tr = tr

    @property
    def operations(self):
        return self.tr.operations

    def commit(self):
        # already operation are appended to main transaction.
        assert not self.tr.is_executed


class DeamonSubClientTransaction(SimpleSubClientTransaction):
    # TODO: Really need it?
    pass
