from core.transaction import TransactionType

def process_payment(bank, account_number, amount, card_number=None):
    """Procesa un pago o depósito"""
    if card_number:
        return bank.process_credit_payment(card_number, amount)
    else:
        return bank.deposit(account_number, amount)