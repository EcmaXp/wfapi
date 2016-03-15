# -*- coding: utf-8 -*-
from threading import Lock

from . import ClientTransaction, ServerTransaction
from .. import utils

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
