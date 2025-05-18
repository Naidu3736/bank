from core.credit_card import CreditCard

def check_credit_limit(bank, card_number: str) -> float:
    with bank.locks.cards_lock:
        card = bank.card_registry.get(card_number)
        if isinstance(card, CreditCard):
            return card.available_credit
        return 0.0

def check_balance(bank, card_number: str) -> float:
    with bank.locks.cards_lock:
        card = bank.card_registry.get(card_number)
        if isinstance(card, CreditCard):
            return card.outstanding_balance
        return 0.0

def is_card_active(bank, card_number: str) -> bool:
    with bank.locks.cards_lock:
        card = bank.card_registry.get(card_number)
        return card.is_valid() if card else False