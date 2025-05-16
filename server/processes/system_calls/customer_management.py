from core.customer import Customer
from typing import Tuple

def create_customer(bank, name: str, email: str) -> Tuple[Customer, str]:
    """
    Proceso completo para crear un nuevo cliente:
    1. Genera un customer_id único
    2. Valida datos básicos
    3. Agrega al sistema bancario
    """
    if not name or not email:
        raise ValueError("Nombre y email son obligatorios")

    with bank._customers_lock:
        # Verifica si el email ya existe
        if any(cust.email == email for cust in bank.customers.values()):
            raise ValueError("Email ya registrado")

        customer = Customer(name, email)
        bank.customers[customer.customer_id] = customer
        return customer, customer.customer_id
    
def delete_customer(bank, customer_id: str) -> bool:
    """Elimina un cliente (llamada al sistema)"""
    with bank._customers_lock:
        if customer_id in bank.customers:
            del bank.customers[customer_id]
            return True
        return False