# -*- coding: utf-8 -*-
from .. import utils
from . import ClientTransaction, ServerTransaction
from threading import Lock

__all__ = ["BaseTransactionManager", "TransactionManager"]

# TODO: change method name like execute_server_transaction

class BaseTransactionManager():
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
            transactions = self.wf.push_and_poll(transactions)
            self._execute_server_transactions(transactions)

    def new_transaction(self, project):
        pm = self.wf.pm
        assert project in pm

        # TODO: 매커니즘
        #   Workflowy가 트랜잭션을 모으는 중이면, 주기
        #   Workflowy가 트랜잭션을 안모으는 중이면 이것만 커밋
        #   모은다는 것의 기준은 WFMixInDeamon의 상속 여부!
        #   만약 이미 이 프로젝트에 해당되는 트랜잭션이 있음에도
        #   중첩된 트랜잭션을 만드는 경우 단일된 하나의 트랜잭션으로 모으기
        #   !! 그러나 현재는 단일 트랜잭션 사용중 (오직 프로젝트 별로 분리)

        with self.lock:
            ctrs = self.current_transactions

            tr = ctrs.get(project)
            if tr is None:
                ctrs[project] = tr = ClientTransaction(self.wf, project)
            
            tr.level += 1
            return tr
            
    def _execute_current_client_transactions(self):
        transactions = []
        for project, transaction in self.current_transactions.items():
            transactions.append(transaction.commit())
        
        return transactions
    
    def _execute_server_transactions(self, transactions):
        pm = self.wf.pm
        
        project_map = {}
        for project in pm:
            # main project's shared_id is None
            shared_id = project.status.shared_id
            assert shared_id not in shared_map
            project_map[shared_id] = project
        
        ctrs = self.current_transactions
        for transaction in transactions:
            shared_id = transaction.get("shared_id")
            project = project_map[shared_id]
            
            client_transaction = ctrs.get(project)
            if client_transaction is None:
                # What if just don't give shared transaction
                #  workflowy don't give changed result?
                print("workflowy give transaction even if not commit transaction", project, client_transaction, transactions)
                assert False
            
            server_transaction = ServerTransaction.from_poll(
                self.wf,
                project,
                client_transaction,
                transaction,
            )
            
            server_transaction.commit()
            