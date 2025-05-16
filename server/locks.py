from threading import Lock

class BankLocks:
    def __init__(self):
        self.accounts_lock = Lock()
        self.customers_lock = Lock()
        self.cards_lock = Lock()
        self.turn_queue_lock = Lock()
        self.teller_pool_lock = Lock()