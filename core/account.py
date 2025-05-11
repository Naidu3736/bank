from hashlib import sha256
from core.card import Card
import re  # Para validación de formato

class Account:
    def __init__(self, account_number, customer_id, initial_balance=0, nip=None):
        self.account_number = account_number
        self.customer_id = customer_id
        self.balance = initial_balance
        self.nip_hash = self._hash_nip(nip) if nip else None
        self.cards = []
        self.nip_attempts = 0  # Contador de intentos fallidos
        self.is_locked = False  # Bloqueo por seguridad
        self.transaction_history = []
    
    def add_card(self, card : Card):
        card.acccount_id = self.account_number
        self.cards.append(card)
        
    
    def add_transaction(self, transaction):
        self.transaction_history.append(transaction)