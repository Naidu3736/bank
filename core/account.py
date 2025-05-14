from hashlib import sha256
import random
from core.debit_card import DebitCard, CardType

class Account:
    def __init__(self, customer_id, initial_balance=0, nip=None):
        self.account_number = self._generate_account_number()  # Genera un número de cuenta automáticamente
        self.customer_id = customer_id
        self.balance = initial_balance
        self.nip_hash = self._hash_nip(nip) if nip else None  # El NIP se pasa directamente al crear la cuenta
        self.debit_cards = []
        self.nip_attempts = 0
        self.is_locked = False
        self.transaction_history = []

    def _generate_account_number(self):
        """Genera un número de cuenta aleatorio de 10 dígitos"""
        return str(random.randint(1000000000, 9999999999))

    def _hash_nip(self, nip):
        """Hashea el NIP para almacenamiento seguro"""
        if nip and len(nip) == 4 and nip.isdigit():
            return sha256(nip.encode()).hexdigest()
        else:
            raise ValueError("El NIP debe ser de 4 dígitos numéricos.")
    
    def add_debit_card(self, card_type: CardType):
        """Añade una tarjeta de débito a la cuenta"""
        card = DebitCard(card_type, self.account_number)
        card.activate_card()
        self.debit_cards.append(card)
        return card

    def add_transaction(self, transaction):
        self.transaction_history.append(transaction)

    def unlock_account(self):
        self.is_locked = False
        self.nip_attempts = 0

    def get_balance(self):
        return self.balance
    
    def get_transaction_history(self) -> list:
        return [f"{t.timestamp}: {t.type} - ${t.amount}" for t in self.transaction_history]
    
    def get_cards_summary(self) -> list:
        return [str(card) for card in self.debit_cards]

    def validate_nip(self, nip):
        """Valida el NIP proporcionado"""
        if self.is_locked:
            return False
        if sha256(nip.encode()).hexdigest() == self.nip_hash:
            self.nip_attempts = 0
            return True
        self.nip_attempts += 1
        if self.nip_attempts >= 3:
            self.is_locked = True
        return False
