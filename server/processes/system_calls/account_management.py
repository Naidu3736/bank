def create_account(bank, customer_id: str, initial_balance: float, nip: str) -> bool:
    """Wrapper para bank.add_account()"""
    try:
        bank.add_account(customer_id, initial_balance, nip)
        return True
    except ValueError:
        return False
    
def close_account(bank, account_number: str) -> bool:
    """Wrapper para bank.close_account()"""
    return bank.close_account(account_number)