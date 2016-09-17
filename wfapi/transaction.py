# -*- coding: utf-8 -*-
import json
import time
from threading import Lock

from .error import WFTransactionError
from .operation import OPERATION_REGISTERED, UnknownOperation

__all__ = ["ServerTransaction", "ClientTransactions", "TransactionManager"]


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
        return self

    def __enter__(self):
        self.handle_enter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.handle_exit(error=True)
        else:
            self.handle_exit(error=False)

        return False


class ProjectBasedTransactions(BaseTransactions):
    __slots__ = ["project"]

    def __init__(self, wf, project):
        super().__init__(wf)
        self.project = project


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
        operation.pre_operation(self)
        self.operations.append(operation)

    def get_operations_json(self):
        operations = []
        for operation in self:
            operations.append(operation.get_client_operation(self))

        return operations

    def get_transaction_json(self):
        pstatus = self.project.status
        operations = self.get_operations_json()

        transaction = dict(
            most_recent_operation_transaction_id=
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
        self.tm.enter_transaction(self)

    def handle_exit(self, error):
        if error:
            return

        if self.is_executed:
            raise WFTransactionError("{!r} is already executed".format(self))

        super().handle_exit(error)
        self.tm.leave_transaction(self)


class ServerTransactions(ProjectBasedTransactions):
    def __init__(self, wf, project, client_timestamp):
        super().__init__(wf, project)
        self.client_timestamp = client_timestamp

    @classmethod
    def from_server(cls, wf, project, info):
        data = json.loads(info.server_run_operation_transaction_json)
        self = cls(wf, project, data["client_timestamp"])

        for op in data["ops"]:
            op.pop("server_data", None)
            # server_data are exists when server_info

            # TODO: change OPERATOR_COLLECTION?
            operator = OPERATION_REGISTERED.get(op["type"], UnknownOperation)
            operation = operator.from_server_operation_json(self, op)
            self.operations.append(operation)

        # info.concurrent_remote_operation_transactions => nested transactions

        return self

    def get_client_timestamp(self, current_time=None):
        assert current_time is None
        return self.client_timestamp


class TransactionManager():
    def __init__(self, wf):
        # [!] REF CYCLE
        import weakref
        self.wf = weakref.proxy(wf)
        # TODO: thread safe is invaild now..
        self.stack = []
        self.operations = []

    def new_transaction(self, project):
        pm = self.wf.pm
        assert project in pm

        return ClientTransactions(self.wf, self, project)

    def enter_transaction(self, transactions:ClientTransactions):
        self.stack.append(transactions)

    def leave_transaction(self, transactions:ClientTransactions):
        last_transaction = self.stack.pop(-1)
        assert transactions is last_transaction, (transactions, last_transaction)

        transactions.pre_operation()
        data = transactions.get_transaction_json()
        self.operations.append(data)

        if not self.stack:
            self.commit()

    def commit(self):
        data = self.wf.push_and_poll(self.operations)
        self.operations = []

        self._execute_server_transactions(data)

    def _execute_server_transactions(self, info):
        pm = self.wf.pm

        project_map = {}
        for project in pm:
            # main project's share_id is None
            share_id = project.status.get("share_id")
            assert share_id not in project_map
            project_map[share_id] = project

        for data in info:
            share_id = data.get("share_id")
            project = project_map[share_id]

            transactions = ServerTransactions.from_server(
                self.wf,
                project,
                data,
            )

            transactions.post_operation()

            for data in data.concurrent_remote_operation_transactions:
                print(data)
                pass
