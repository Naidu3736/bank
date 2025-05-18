def execute(bank, card_number: str, amount: float, merchant: str, nip: str) -> bool:
    """Wrapper para bank.process_debit_payment() (si existiera)"""
    with bank.locks.cards_lock:
        card = bank.card_registry.get(card_number)
        if not isinstance(card, DebitCard) or not card.is_valid():
            return False

    return bank.process_debit_payment(card_number, amount, merchant, nip)