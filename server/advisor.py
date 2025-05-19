from datetime import datetime
from typing import List, Dict, Optional
from core.card import CardType
from core.customer import Customer
from core.account import Account

class Advisor:
    def __init__(self, advisor_id: str, bank):
        self.advisor_id = advisor_id
        self.bank = bank
        self.history: List[Dict] = []

    # ---- Gestión de Clientes ----
    def create_customer(self, name: str, email: str) -> str:
        try:
            customer = self.bank.add_customer(name, email)
            self._log_operation("CREATE_CUSTOMER", f"Cliente {customer.customer_id}")
            return f"Cliente creado: {customer.customer_id}"
        except ValueError as e:
            return f"Error: {str(e)}"

    def delete_customer(self, customer_id: str) -> str:
        success = self.bank.delete_customer(customer_id)
        if success:
            self._log_operation("DELETE_CUSTOMER", f"Cliente {customer_id}")
            return "Cliente eliminado exitosamente"
        return "Error: Cliente no encontrado"

    # ---- Gestión de Cuentas ----
    def open_account(self, customer_id: str, initial_balance: float = 0, nip: str = None) -> str:
        try:
            account = self.bank.add_account(customer_id, initial_balance, nip)
            self._log_operation("OPEN_ACCOUNT", f"Cuenta {account.account_number}")
            return f"Cuenta abierta: {account.account_number}"
        except ValueError as e:
            return f"Error: {str(e)}"

    def close_account(self, account_number: str) -> str:
        success = self.bank.close_account(account_number)
        if success:
            self._log_operation("CLOSE_ACCOUNT", f"Cuenta {account_number}")
            return "Cuenta cerrada exitosamente"
        return "Error: Cuenta no encontrada"

    def link_account(self, account_number: str, customer_id: str) -> str:
        success = self.bank.link_account_to_customer(account_number, customer_id)
        if success:
            self._log_operation("LINK_ACCOUNT", f"Cuenta {account_number} a cliente {customer_id}")
            return "Cuenta vinculada exitosamente"
        return "Error: Datos inválidos"

    # ---- Gestión de Tarjetas ----
    def issue_debit_card(self, account_number: str, card_type: CardType) -> str:
        try:
            card = self.bank.issue_debit_card(account_number, card_type)
            self._log_operation("ISSUE_DEBIT_CARD", f"Tarjeta {card.card_number}")
            return f"Tarjeta débito emitida: {card.card_number}"
        except ValueError as e:
            return f"Error: {str(e)}"

    def issue_credit_card(self, customer_id: str, card_type: CardType) -> str:
        try:
            card = self.bank.issue_credit_card(customer_id, card_type)
            self._log_operation("ISSUE_CREDIT_CARD", f"Tarjeta {card.card_number}")
            return f"Tarjeta crédito emitida: {card.card_number}"
        except ValueError as e:
            return f"Error: {str(e)}"

    def deactivate_card(self, card_number: str) -> str:
        try:
            success = self.bank.deactivate_card(card_number)
            if success:
                self._log_operation("DEACTIVATE_CARD", f"Tarjeta {card_number}")
                return "Tarjeta desactivada exitosamente"
            return "Error al desactivar tarjeta"
        except ValueError as e:
            return f"Error: {str(e)}"

    # ---- Consultas Detalladas ----
    def get_customer_info(self, customer_id: str) -> Dict:
        accounts = self.bank.get_customer_accounts(customer_id)
        cards = self.bank.get_credit_cards(customer_id)
        return {
            "accounts": [acc.account_number for acc in accounts],
            "credit_cards": [card.card_number for card in cards]
        }

    def get_account_statement(self, account_number: str, days: int = 30) -> Dict:
        return self.bank.generate_account_statement(account_number, days)

    def get_transaction_history(self, account_number: str, limit: int = 10) -> List[Dict]:
        transactions = self.bank.get_account_transactions(account_number, limit)
        return [{
            "date": str(t.timestamp),
            "amount": t.amount,
            "type": t.transaction_type.name,
            "description": t.description or ""
        } for t in transactions]

    def get_card_information(self, card_number: str) -> Dict:
        info = self.bank.get_credit_card_info(card_number)
        if not info:
            return {"error": "Tarjeta no encontrada"}
        return info

    # ---- Métodos Internos ----
    def _log_operation(self, op_type: str, details: str):
        self.history.append({
            "advisor_id": self.advisor_id,
            "operation": op_type,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })