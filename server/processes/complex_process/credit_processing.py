from core.transaction import Transaction, TransactionType
from core.credit_card import CreditCard

def process_credit_purchase(bank, card_number: str, amount: float, merchant: str) -> bool:
    with bank._cards_lock:
        card = bank.card_registry.get(card_number)
        if not isinstance(card, CreditCard) or not card.is_valid():
            return False

        try:
            card.make_purchase(amount)
            # Registrar transacción en la cuenta vinculada si es necesario
            return True
        except ValueError:
            return False