from core.card import CardType
from core.debit_card import DebitCard
from core.credit_card import CreditCard

def create_debit_card(bank, account_number: str, card_type: CardType) -> str:
    """Crea tarjeta débito (llamada al sistema)"""
    with bank._accounts_lock:
        account = bank.accounts.get(account_number)
        if not account:
            raise ValueError("Cuenta no existe")

    with bank._cards_lock:
        card = account.add_debit_card(card_type)
        bank.card_registry[card.card_number] = card
        return card.card_number

def create_credit_card(bank, customer_id: str, card_type: CardType) -> str:
    """Crea tarjeta crédito (llamada al sistema)"""
    with bank._customers_lock:
        customer = bank.customers.get(customer_id)
        if not customer:
            raise ValueError("Cliente no existe")

    with bank._cards_lock:
        card = customer.add_credit_card(card_type)
        bank.card_registry[card.card_number] = card
        return card.card_number

def activate_card(bank, card_number: str) -> bool:
    """Activa una tarjeta (llamada al sistema)"""
    with bank._cards_lock:
        card = bank.card_registry.get(card_number)
        if card:
            card.activate_card()
            return True
        return False

def block_card(bank, card_number: str) -> bool:
    """Bloqueo inmediato de tarjeta"""
    with bank._cards_lock:
        card = bank.card_registry.get(card_number)
        if card:
            card.block_card()
            return True
        return False

def get_card_type(bank, card_number: str) -> CardType:
    """Consulta rápida de tipo de tarjeta"""
    with bank._cards_lock:
        card = bank.card_registry.get(card_number)
        return card.type if card else None