import uuid
from core.credit_card import CreditCard, CardType
from core.account import Account

class Customer:
    @staticmethod
    def generate_customer_id():
        return str(uuid.uuid4())

    def __init__(self, name, email):
        self.customer_id = self.generate_customer_id()
        self.name = name
        self.email = email
        self.credit_cards = []
        self.accounts = []

    def add_credit_card(self, card_type: CardType):
        """Añade y activa una nueva tarjeta de crédito"""
        card = CreditCard(card_type, self.customer_id)
        card.activate_card()
        self.credit_cards.append(card)
        return card
    
    def remove_credit_card(self, card_number: str) -> bool:
        self.credit_cards = [c for c in self.credit_cards 
                        if c.card_number != card_number]
        return True

    def get_cards_summary(self) -> list:
        return [str(card) for card in self.credit_cards]

    def link_account(self, account: Account) -> bool:
        """Vincula una cuenta al cliente con validación de propiedad"""
        if account.customer_id != self.customer_id:
            raise ValueError("La cuenta no pertenece a este cliente")
        
        if account not in self.accounts:
            self.accounts.append(account)
        return True
