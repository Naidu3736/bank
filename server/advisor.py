from multiprocessing import Lock
from core.card import CardType
from server.processes.system_calls import (
    customer_management,
    account_management,
    card_operations
)

class Advisor:
    def __init__(self, bank):
        self.bank = bank
        self.lock = Lock()

    def create_customer(self, name: str, email: str) -> str:
        with self.lock:
            try:
                customer, _ = customer_management.create_customer(self.bank, name, email)
                return f"Cliente {customer.customer_id} creado"
            except ValueError as e:
                return f"Error: {str(e)}"

    def create_account(self, customer_id: str, nip: str) -> str:
        with self.lock:
            try:
                success = account_management.create_account(self.bank, customer_id, 0.0, nip)
                return "Cuenta creada" if success else "Error al crear cuenta"
            except ValueError as e:
                return f"Error: {str(e)}"

    def assign_debit_card(self, account_number: str, card_type: CardType) -> str:
        with self.lock:
            try:
                card_number = card_operations.create_debit_card(self.bank, account_number, card_type)
                return f"Tarjeta débito {card_number} asignada"
            except ValueError as e:
                return f"Error: {str(e)}"

    def close_account(self, account_number: str) -> str:
        with self.lock:
            success = account_management.close_account(self.bank, account_number)
            return f"Cuenta {account_number} cerrada" if success else "Cuenta no encontrada"