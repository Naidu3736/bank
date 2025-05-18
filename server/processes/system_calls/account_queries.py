def get_balance(bank, account_number: str) -> float:
    with bank.locks.accounts_lock:
        account = bank.accounts.get(account_number)
        return account.balance if account else None

def validate_nip(bank, account_number: str, nip: str) -> bool:
    with bank.locks.accounts_lock:
        account = bank.accounts.get(account_number)
        return account.validate_nip(nip) if account else False