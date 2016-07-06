# -*- coding: utf-8 -*-
import json
import time
from threading import Lock

from .base import BaseTransaction, BaseTransactionManager
from .error import WFTransactionError
from .operation import OPERATION_REGISTERED, UnknownOperation

__all__ = ["ServerTransaction", "ClientTransaction",
    "SimpleSubClientTransaction", "DeamonSubClientTransaction",
           "TransactionManager"]

# TODO: Transaction must support splited projects!
# TODO: change method name like execute_server_transaction


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

    def commit(self):
        raise NotImplementedError

    def rollback(self):
        raise NotImplementedError


class ServerTransaction(ProjectBasedTransaction):
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


class ClientTransaction(ProjectBasedTransaction):
    def __init__(self, wf, tm, project):
        super().__init__(wf, project)
        self.tm = tm
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
            self.tm.callback_out(self)

    def commit(self):
        return self.get_transaction_json()

    def rollback(self):
        raise NotImplementedError


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

    def rollback(self):
        raise NotImplementedError


class DeamonSubClientTransaction(SimpleSubClientTransaction):
    # TODO: Really need it?
    pass


class TransactionManager(BaseTransactionManager):
    def __init__(self, wf):
        self.wf = wf
        self.lock = Lock()
        self.current_transactions = {}

    def clear(self):
        raise NotImplementedError

    def commit(self):
        with self.lock:
            transactions = self._execute_current_client_transactions()
            transactions = self.wf.push_and_poll(transactions, from_tm=True)
            self._execute_server_transactions(transactions)

    def new_transaction(self, project):
        pm = self.wf.pm
        assert project in pm

        with self.lock:
            ctrs = self.current_transactions

            tr = ctrs.get(project)
            if tr is None:
                ctrs[project] = tr = ClientTransaction(self.wf, self, project)

            return tr

    def callback_out(self, tr):
        old_tr = self.current_transactions[tr.project]
        assert tr is old_tr
        if tr.level > 0:
            return

        for tr in self.current_transactions.values():
            if tr.level > 0:
                break
        else:
            self.commit()
            self.current_transactions.clear()

    def _execute_current_client_transactions(self):
        transactions = []
        for project, transaction in self.current_transactions.items():
            transactions.append(transaction.commit())

        return transactions

    def _execute_server_transactions(self, transactions):
        pm = self.wf.pm

        project_map = {}
        for project in pm:
            # main project's share_id is None
            share_id = project.status.get("share_id")
            assert share_id not in project_map
            project_map[share_id] = project

        ctrs = self.current_transactions
        for transaction in transactions:
            share_id = transaction.get("share_id")
            project = project_map[share_id]

            client_transaction = ctrs.get(project)
            if client_transaction is None:
                # What if just don't give shared transaction
                #  workflowy don't give changed result?
                print("workflowy give transaction even if not commit transaction", project, client_transaction, transactions)
                assert False

            server_transaction = ServerTransaction.from_server(
                self.wf,
                project,
                client_transaction,
                transaction,
            )

            server_transaction.commit()
