def execute(bank, account_number: str, amount: float, source_reference: str = None) -> bool:
    """Wrapper para bank.deposit()"""
    return bank.deposit(account_number, amount, source_reference)