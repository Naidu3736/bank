from core.account import Account

def create_account(bank, customer_id: str, initial_balance: float, nip: str) -> bool:
    with bank._customers_lock:
        if customer_id not in bank.customers:
            return False

    with bank._accounts_lock:
        account = Account(customer_id, initial_balance, nip)
        bank.accounts[account.account_number] = account
        bank.customers[customer_id].link_account(account)
        return True
    
def close_account(bank, account_number: str) -> bool:
    """Elimina una cuenta (llamada al sistema)"""
    with bank._accounts_lock:
        if account_number in bank.accounts:
            del bank.accounts[account_number]
            return True
        return False