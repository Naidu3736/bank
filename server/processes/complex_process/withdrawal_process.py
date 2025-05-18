def execute(bank, account_number: str, amount: float, nip: str) -> bool:
    """Wrapper para bank.withdraw()"""
    return bank.withdraw(account_number, amount, nip)