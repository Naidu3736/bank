from core.debit_card import DebitCard
from core.credit_card import CreditCard

def apply_credit_interest(bank):
    with bank._cards_lock:
        for card in bank.card_registry.values():
            if isinstance(card, CreditCard) and card.outstanding_balance > 0:
                card.apply_interest()

def reset_daily_limits(bank):
    with bank._cards_lock:
        for card in bank.card_registry.values():
            if isinstance(card, DebitCard):
                card.daily_spent = 0