import threading
from typing import Optional

class TrackedLock:
    """Lock con tracking completo para threading"""
    def __init__(self, name: str, process_tracker=None):
        self._lock = threading.Lock()  # Lock real de threading
        self.name = name
        self.process_tracker = process_tracker
        self._owner_pid = -1
        self._is_acquired = False  # Track manual del estado

    def acquire(self, blocking=True, timeout=None):
        """Adquiere el lock con tracking"""
        thread_id = threading.get_ident()
        if self.process_tracker:
            self.process_tracker.update_lock(
                self.name,
                owner_pid=thread_id,
                state="waiting"
            )
        
        # Llamada real al acquire del Lock
        if timeout is not None:
            acquired = self._lock.acquire(blocking, timeout)
        else:
            acquired = self._lock.acquire(blocking)
        
        if acquired:
            self._owner_pid = thread_id
            self._is_acquired = True
            if self.process_tracker:
                self.process_tracker.update_lock(
                    self.name,
                    owner_pid=thread_id,
                    state="acquired"
                )
        return acquired

    def release(self):
        """Libera el lock con tracking"""
        if self._is_acquired:
            try:
                self._lock.release()  # Llamada real al release
                self._owner_pid = -1
                self._is_acquired = False
                if self.process_tracker:
                    self.process_tracker.update_lock(
                        self.name,
                        owner_pid=-1,
                        state="released"
                    )
            except Exception as e:
                if self.process_tracker:
                    self.process_tracker.update_lock(
                        self.name,
                        owner_pid=threading.get_ident(),
                        state=f"release_error: {str(e)}"
                    )
                raise

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

class ResourceSemaphore:
    def __init__(self, max_workers: int, name: str, tracker=None):
        self._semaphore = threading.Semaphore(max_workers)
        self.name = name
        self.tracker = tracker
        self.max_workers = max_workers
        self._available = max_workers
        self._lock = threading.Lock()  # Para proteger el acceso a _available

    def acquire(self, blocking=True, timeout=None):
        thread_id = threading.get_ident()
        
        # Actualizar estado antes de adquirir
        if self.tracker:
            self.tracker.update_semaphore(
                name=self.name,
                owner_pid=thread_id,
                state="waiting",
                available=self._available
            )
        
        acquired = self._semaphore.acquire(blocking, timeout)
        
        if acquired:
            with self._lock:
                self._available -= 1
            if self.tracker:
                self.tracker.update_semaphore(
                    name=self.name,
                    owner_pid=thread_id,
                    state="acquired",
                    available=self._available
                )
        return acquired

    def release(self):
        with self._lock:
            self._available += 1
            if self._available > self.max_workers:
                self._available = self.max_workers
                
        if self.tracker:
            self.tracker.update_semaphore(
                name=self.name,
                owner_pid=-1,
                state="released",
                available=self._available
            )
        self._semaphore.release()

class BankLocks:
    """Gestión centralizada de locks con tracking para threading"""
    def __init__(self, process_tracker=None):
        # Semáforos para recursos
        self.tellers_sem = ResourceSemaphore(
            max_workers=4,
            name="tellers_pool",
            tracker=process_tracker
        )
        
        self.advisors_sem = ResourceSemaphore(
            max_workers=2,
            name="advisors_pool",
            tracker=process_tracker
        )
        
        # Locks para estructuras de datos
        self.accounts_lock = TrackedLock("accounts_lock", process_tracker)
        self.customers_lock = TrackedLock("customers_lock", process_tracker)
        self.cards_lock = TrackedLock("cards_lock", process_tracker)
        self.turn_queue_lock = TrackedLock("turn_queue_lock", process_tracker)