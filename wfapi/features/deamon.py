# -*- coding: utf-8 -*-
import queue
import threading
import time
from ..workflowy import BaseWorkflowy
from ..transaction import WFSimpleSubClientTransaction

__all__ = ["WFMixinDeamon"]


class WFDeamonSubClientTransaction(WFSimpleSubClientTransaction):
    # TODO: Really need it?
    pass


class WFMixinDeamon(BaseWorkflowy):
    CLIENT_SUBTRANSACTION_CLASS = WFDeamonSubClientTransaction
    # TODO: new subtransaction class are push operation at commit time.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue = self._new_queue()
        # INTERNAL: self.queue is internal value at this time.
        self.thread = self._new_thread()
        self.default_execute_wait = 5

    def _task(self):
        queue = self.queue
        # queue can be overflow

        with self.transaction_lock:
            while not queue.empty():
                queue.get_nowait()
                queue.task_done()

            queue.put(0)
            # INTERNAL: start counter for task

        while True:
            wait = self.default_execute_wait
            event = queue.get()

            if event is None:
                # STOP EVENT
                while not queue.empty():
                    queue.get_nowait()
                    queue.task_done()
                    # TODO: warning not queued event?
                    # TODO: just new stop flag?

                queue.task_done()
                # for stop event.
                return

            time.sleep(wait)
            # TODO: how to sleep automation?
            # TODO: use some good schuler?

            with self.transaction_lock:
                current_transaction = self.current_transaction
                if current_transaction is None:
                    with self.transaction() as current_transaction:
                        pass

                if not current_transaction.operations:
                    queue.put(event + wait)
                    queue.task_done()
                    continue

                if event >= self.status.default_execute_wait:
                    self.current_transaction = None
                    self.execute_transaction(current_transaction)

                queue.put(0)
                queue.task_done()
                # reset counter

    def execute_transaction(self, tr):
        # it's ok because lock is RLock!
        with self.transaction_lock:
            super().execute_transaction(tr)

    # TODO: auto start with inited var

    def _new_thread(self):
        thread = threading.Thread(target=self._task)
        thread.daemon = True
        return thread

    def _new_queue(self):
        return queue.Queue()

    def start(self):
        self.thread.start()

    def stop(self):
        # TODO: handle many case for threading
        # send stop signal to thread.
        self.queue.put(None)
        self.thread.join()
        # TODO: what if queue are not empty?
        
    def reset(self):
        super().reset()

        self.stop()
        self.queue = self._new_queue()
        self.thread = self._new_thread()
