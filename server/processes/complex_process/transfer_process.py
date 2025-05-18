from core.transaction import Transaction, TransactionType

def execute(bank, source_id: str, target_id: str, amount: float, nip: str = None) -> bool:
    """Wrapper para bank.transfer()"""
    return bank.transfer(source_id, target_id, amount, nip)