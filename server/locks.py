from multiprocessing import Lock
import os
import threading

class TrackedLock:
    def __init__(self, name: str):
        self._lock = Lock()
        self.name = name
        self.acquired = False

    def acquire(self, blocking=True, timeout=None):
        acquired = self._lock.acquire(blocking, timeout)
        if acquired:
            self.acquired = True
        return acquired

    def release(self):
        if self.acquired:
            self._lock.release()
            self.acquired = False

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

class BankLocks:
    def __init__(self):
        self.accounts_lock = TrackedLock("accounts_lock")
        self.customers_lock = TrackedLock("customers_lock")
        self.cards_lock = TrackedLock("cards_lock")
        self.turn_queue_lock = TrackedLock("turn_queue_lock")
        self.teller_pool_lock = TrackedLock("teller_pool_lock")