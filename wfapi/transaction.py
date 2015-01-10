# -*- coding: utf-8 -*-
from . import utils as _utils
import time


class WFBaseTransaction():
    is_executed = False

    def __init__(self, wf):
        self.operations = []
        self.wf = wf

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

    def __iter__(self):
        return iter(self.operations)

    def __iadd__(self, other):
        self.push(other)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            return False

        self.commit()
        return False

    def commit(self):
        raise NotImplementedError

    def rollback(self):
        raise NotImplementedError


class WFServerTransaction(WFBaseTransaction):
    def __init__(self, wf, client_tr, client_timestamp):
        super().__init__(wf)
        self.client_timestamp = client_timestamp
        self.client_transaction = client_tr

    @classmethod
    def from_server_operations(cls, wf, client_tr, data):
        client_timestamp = data["client_timestamp"]
        self = cls(wf, client_tr, client_timestamp)

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
            operator = OPERATOR_COLLECTION.get(op["type"], _WFUnknownOperation)
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
        self.operations.append(operation)

    def commit(self):
        with self.wf.transaction_lock:
            if self.is_executed:
                return

            self.pre_operation()
            self.post_operation()
            self.is_executed = True


class WFClientTransaction(WFBaseTransaction):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tid = self.generate_tid()

    generate_tid = staticmethod(_utils.generate_tid)

    def get_client_timestamp(self, current_time=None):
        if current_time is None:
            current_time = time.time()

        return (current_time - self.wf.status.date_joined_timestamp_in_seconds) // 60

    def push(self, operation):
        # TODO: determine good position for pre_operation and post_operation
        # XXX: if pre_operation and post_operation in push_poll function, transaction are not work.
        operation.pre_operation(self)
        self.operations.append(operation)
        operation.post_operation(self)

    def get_operations_json(self):
        operations = []
        for operation in self:
            operations.append(operation.get_client_operation(self))

        return operations

    def get_transaction_json(self, operations=None):
        if operations is None:
            operations = self.get_operations_json()

        transaction = dict(
            most_recent_operation_transaction_id=self.wf.status.most_recent_operation_transaction_id,
            operations=operations,
        )

        # TODO: move shared project process code.
        status = self.wf.status
        if status.share_type is not None:
            assert status.share_type == "url"
            share_id = status.share_id
            transaction.update(
                share_id=share_id,
            )

        return [transaction]

    def commit(self):
        with self.wf.transaction_lock:
            if self.is_executed:
                return

            self.wf.execute_transaction(self)
            self.is_committed = True

            if self.wf.current_transaction is self:
                self.wf.current_transaction = None


class WFSimpleSubClientTransaction(WFClientTransaction):
    def __init__(self, wf, tr):
        self.wf = wf
        self.tr = tr

    @property
    def operations(self):
        return self.tr.operations

    def commit(self):
        # already operation are appended to main transaction.
        assert not self.tr.is_executed


class WFDeamonSubClientTransaction(WFSimpleSubClientTransaction):
    # TODO: Really need it?
    pass
