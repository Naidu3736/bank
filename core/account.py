from hashlib import sha256
from core.credit_card import DebitCard, CardType  # Ahora usamos DebitCard directamente

class Account:
    def __init__(self, account_number, customer_id, initial_balance=0, nip=None):
        self.account_number = account_number
        self.customer_id = customer_id
        self.balance = initial_balance
        self.nip_hash = self._hash_nip(nip) if nip else None
        self.debit_cards = []
        self.nip_attempts = 0
        self.is_locked = False
        self.transaction_history = []

    def _hash_nip(self, nip):
        """Hashea el NIP para almacenamiento seguro"""
        return sha256(nip.encode()).hexdigest()

    def add_debit_card(self, card_type: CardType):
        """Añade una tarjeta de débito a la cuenta"""
        card = DebitCard(card_type, self.account_number)
        card.activate_card()
        self.debit_cards.append(card)
        return card

    def add_transaction(self, transaction):
        self.transaction_history.append(transaction)

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
