from multiprocessing import Lock
import os
import threading

class TrackedLock:
    def __init__(self, name: str,process_tracker):
        self._lock = Lock()
        self.name = name
        self.acquired = False
        self._pt = process_tracker

    def acquire(self, blocking=True, timeout=None):
        acquired = self._lock.acquire(blocking, timeout)
        if acquired:
            self.acquired = True
            # no habiamos llamado a update lock , y nunca se informaba al ProccessTracker
            self._pt.update_lock(
                lock_name=self.name,
                owner_pid=os.getpid(),
                state="acquired"
                )
        return acquired

    def release(self):
        if self.acquired:
            self._lock.release()
            self.acquired = False
            # aqui casi lo mismo nunca se informaba nada xd
            self._pt.update_lock(
                lock_name=self.name,
                owner_pid=None,
                 state="free"
            )


    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

class BankLocks:
    def __init__(self, process_tracker):
        self.accounts_lock      = TrackedLock("accounts_lock", process_tracker)
        self.customers_lock     = TrackedLock("customers_lock", process_tracker)
        self.cards_lock         = TrackedLock("cards_lock", process_tracker)
        self.turn_queue_lock    = TrackedLock("turn_queue_lock", process_tracker)
        self.teller_pool_lock   = TrackedLock("teller_pool_lock", process_tracker)