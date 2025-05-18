def apply_credit_interest(bank):
    """Wrapper para bank.apply_monthly_interest()"""
    bank.apply_monthly_interest()

def reset_daily_limits(bank):
    with bank.locks.cards_lock:
        for card in bank.card_registry.values():
            if isinstance(card, DebitCard):
                card.daily_spent = 0