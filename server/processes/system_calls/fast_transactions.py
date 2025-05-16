def deposit(bank, account_number: str, amount: float) -> bool:
    """Depósito directo sin validaciones adicionales"""
    with bank._accounts_lock:
        account = bank.accounts.get(account_number)
        if account:
            account.balance += amount
            return True
        return False

def simple_transfer(bank, source_id: str, target_id: str, amount: float) -> bool:
    """Transferencia básica entre cuentas"""
    with bank._accounts_lock:
        if source_id not in bank.accounts or target_id not in bank.accounts:
            return False
        if bank.accounts[source_id].balance < amount:
            return False
        
        bank.accounts[source_id].balance -= amount
        bank.accounts[target_id].balance += amount
        return True