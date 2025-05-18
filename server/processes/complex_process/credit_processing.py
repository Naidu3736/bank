def process_credit_purchase(bank, card_number: str, amount: float, merchant: str) -> bool:
    """Wrapper para bank.process_credit_purchase()"""
    return bank.process_credit_purchase(card_number, amount, merchant)