def create_account(bank, customer_id: str, initial_balance: float, nip: str) -> str:
    """Wrapper para bank.add_account()"""
    account = bank.add_account(customer_id, initial_balance, nip)
    return account.account_number

def link_account_to_customer(bank, account_number: str, customer_id: str) -> bool:
    """Wrapper para bank.link_account_to_customer()"""
    return bank.link_account_to_customer(account_number, customer_id)

def close_account(bank, account_number: str) -> bool:
    """Wrapper para bank.close_account()"""
    return bank.close_account(account_number)

def fast_deposit(bank, account_number: str, amount: float) -> bool:
    """Versión simplificada para depósitos directos (efectivo)"""
    with bank.locks.accounts_lock:
        account = bank.accounts.get(account_number)
        if not account:
            return False
        account.balance += amount
        return True