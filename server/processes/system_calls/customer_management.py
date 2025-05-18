from typing import Tuple

def create_customer(bank, name: str, email: str) -> Tuple[Customer, str]:
    """Wrapper para bank.add_customer()"""
    try:
        customer = bank.add_customer(name, email)
        return customer, customer.customer_id
    except ValueError as e:
        raise ValueError(str(e))
    
def delete_customer(bank, customer_id: str) -> bool:
    """Wrapper para bank.delete_customer()"""
    return bank.delete_customer(customer_id)