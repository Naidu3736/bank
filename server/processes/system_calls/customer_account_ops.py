from typing import List

def get_customer_accounts(bank, customer_id: str) -> List[str]:
    """Wrapper para bank.get_customer_accounts()"""
    accounts = bank.get_customer_accounts(customer_id)
    return [acc.account_number for acc in accounts]

def transfer_between_own_accounts(bank, customer_id: str, 
                                source_acc: str, target_acc: str, 
                                amount: float) -> bool:
    """Wrapper para bank.transfer_between_own_accounts()"""
    return bank.transfer_between_own_accounts(customer_id, source_acc, target_acc, amount)