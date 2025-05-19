from multiprocessing import Lock
import os
import threading

class TrackedLock:
    def __init__(self, name: str, process_tracker=None):
        self._lock = Lock()
        self.name = name
        self.acquired = False
        self.process_tracker = process_tracker
        self._owner_pid = -1
        self._waiting_processes = set()

    def acquire(self, blocking=True, timeout=None):
        pid = os.getpid()
        if self.process_tracker:
            self.process_tracker.update_lock(
                self.name, 
                owner_pid=pid, 
                state="waiting"
            )
            self._waiting_processes.add(pid)
            
        acquired = self._lock.acquire(blocking, timeout)
        
        if acquired:
            self.acquired = True
            self._owner_pid = pid
            if pid in self._waiting_processes:
                self._waiting_processes.remove(pid)
            if self.process_tracker:
                self.process_tracker.update_lock(
                    self.name,
                    owner_pid=pid,
                    state="acquired"
                )
        return acquired

    def release(self):
        if self.acquired:
            self._lock.release()
            self.acquired = False
            self._owner_pid = -1
            if self.process_tracker:
                self.process_tracker.update_lock(
                    self.name,
                    owner_pid=-1,
                    state="free"
                )

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

class BankLocks:
    def __init__(self, process_tracker=None):
        self.accounts_lock = TrackedLock("accounts_lock", process_tracker)
        self.customers_lock = TrackedLock("customers_lock", process_tracker)
        self.cards_lock = TrackedLock("cards_lock", process_tracker)
        self.turn_queue_lock = TrackedLock("turn_queue_lock", process_tracker)
        self.teller_pool_lock = TrackedLock("teller_pool_lock", process_tracker)