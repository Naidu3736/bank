from multiprocessing import Lock, Semaphore
from typing import Optional
import os

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

    def __str__(self):
        return f"Lock(name={self.name}, owner_pid={self._owner_pid}, state={'acquired' if self.acquired else 'free'})"

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

class ResourceSemaphore:
    """Semaforo para gestionar recursos limitados (Tellers/Advisors)"""
    def __init__(self, max_workers: int, name: str, tracker=None):
        self.semaphore = Semaphore(max_workers)
        self.name = name
        self.tracker = tracker
        self._waiting_pids = set()

    def acquire(self, pid: Optional[int] = None):
        pid = pid or os.getpid()
        if self.tracker:
            available = self.semaphore._value  # Acceder al contador interno
            self.tracker.update_lock(
                self.name,
                owner_pid=pid,
                state=f"waiting (slots: {available})"  # <- Más detalle
            )

    def release(self, pid: Optional[int] = None):
        pid = pid or os.getpid()
        self.semaphore.release()
        if self.tracker:
            self.tracker.update_lock(self.name, owner_pid=-1, state="free")

    def __str__(self):
        return f"Lock(name={self.name}, owner_pid={self._owner_pid}, state={'acquired' if self.acquired else 'free'})"

class BankLocks:
    def __init__(self, process_tracker=None):
        # Semaforos para recursos
        self.tellers_sem = ResourceSemaphore(
            max_workers=4,  # Ejemplo: 4 tellers máximo
            name="tellers_pool",
            tracker=process_tracker
        )
        
        self.advisors_sem = ResourceSemaphore(
            max_workers=2,  # Ejemplo: 2 advisors máximo
            name="advisors_pool",
            tracker=process_tracker
        )
        
        # Locks tradicionales para datos
        self.accounts_lock = TrackedLock("accounts_lock", process_tracker)
        self.customers_lock = TrackedLock("customers_lock", process_tracker)
        self.cards_lock = TrackedLock("cards_lock", process_tracker)