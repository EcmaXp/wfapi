# -*- coding: utf-8 -*-
import json
import time
from threading import Lock

from .error import WFTransactionError
from .operation import OPERATION_REGISTERED, UnknownOperation

#__all__ = ["ServerTransaction", "ClientTransaction",
#           "TransactionManager"]


class BaseTransactions():
    def __init__(self, wf):
        self.wf = wf # wf -> pj??
        self.operations = []
        self.is_executed = False

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
        if not self.is_executed:
            self.is_executed = True

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


class ProjectBasedTransactions(BaseTransactions):
    __slots__ = ["project"]

    def __init__(self, wf, project):
        super().__init__(wf)
        self.project = project


class ServerTransactions(ProjectBasedTransactions):
    def __init__(self, wf, project, client_tr, client_timestamp):
        super().__init__(wf, project)
        self.client_timestamp = client_timestamp
        self.client_transaction = client_tr

    @classmethod
    def from_server(cls, wf, project, client_tr, data):
        # TODO: find reason why wrapped?
        data = json.loads(data.server_run_operation_transaction_json)

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
            operator = OPERATION_REGISTERED.get(op["type"], UnknownOperation)
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

    def rollback(self):
        raise AssertionError("rollback are not supported")


class ClientTransactions(ProjectBasedTransactions):
    def __init__(self, wf, tm, project):
        super().__init__(wf, project)
        self.tm = tm
    
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

        # TODO: DO NOT APPLY POST_OPERATION?
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
        self.tm.enter_transactions(self)

    def handle_exit(self, error):
        if self.is_executed:
            raise WFTransactionError("{!r} is already executed".format(self))

        super().handle_exit(error)
        self.tm.leave_transactions(self)


class TransactionManager():
    def __init__(self, wf):
        # [!] REF CYCLE
        import weakref
        self.wf = weakref.proxy(wf)
        # TODO: thread safe is invaild now..
        self.stack = []
        self.operations = []

    def commit(self):
        self.wf.push_and_poll(self.operations)
        self.operations = []

    def new_transaction(self, project):
        pm = self.wf.pm
        assert project in pm

        return ClientTransactions(self, project)

    def enter_transaction(self, transactions:ClientTransactions):
        self.tm.stack.append(self)

    def leave_transaction(self, transactions:ClientTransactions):
        last_transaction = self.stack.pop()
        assert transactions is last_transaction

        data = transactions.get_operations_json()
        self.operations.append(data)

        if not self.stack:
            self.commit()

    def _execute_server_transactions(self, data):
        pm = self.wf.pm

        project_map = {}
        for project in pm:
            # main project's share_id is None
            share_id = project.status.get("share_id")
            assert share_id not in project_map
            project_map[share_id] = project

        for transaction in data:
            share_id = transaction.get("share_id")
            project = project_map[share_id]

            server_transaction = ServerTransactions.from_server(
                self.wf,
                project,
                transaction,
            )

            server_transaction.commit()
