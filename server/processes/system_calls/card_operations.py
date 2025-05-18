from core.card import CardType

def create_debit_card(bank, account_number: str, card_type: CardType) -> str:
    """Wrapper para bank.issue_debit_card()"""
    try:
        return bank.issue_debit_card(account_number, card_type).card_number
    except ValueError:
        raise ValueError("No se pudo crear tarjeta débito")

def create_credit_card(bank, customer_id: str, card_type: CardType) -> str:
    """Wrapper para bank.issue_credit_card()"""
    try:
        return bank.issue_credit_card(customer_id, card_type).card_number
    except ValueError:
        raise ValueError("No se pudo crear tarjeta crédito")

def activate_card(bank, card_number: str) -> bool:
    """Wrapper para card.activate_card() (se mantiene igual)"""
    with bank.locks.cards_lock:
        card = bank.card_registry.get(card_number)
        if card:
            card.activate_card()
            return True
        return False

def block_card(bank, card_number: str) -> bool:
    """Wrapper para bank.block_card()"""
    return bank.block_card(card_number)

def get_card_type(bank, card_number: str) -> CardType:
    """Wrapper para consulta directa"""
    with bank.locks.cards_lock:
        card = bank.card_registry.get(card_number)
        return card.type if card else None