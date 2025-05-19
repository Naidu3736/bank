from datetime import datetime
from core.turn import Turn
from typing import Optional, Dict, List

class Teller:
    def __init__(self, teller_id: str, bank):
        self.teller_id = teller_id
        self.bank = bank
        self.available = True
        self.current_turn: Optional[Turn] = None
        self.history: List[Dict] = []

    # ---- Operaciones Monetarias ----
    def deposit(self, account_number: str, amount: float) -> str:
        if not self.current_turn:
            return "Error: No hay turno asignado"
        success = self.bank.deposit(account_number, amount)
        if success:
            self._log_operation("DEPOSIT", amount, account_number)
            return f"Depósito exitoso: ${amount:.2f}"
        return "Error: Cuenta no encontrada o monto inválido"

    def withdraw(self, account_number: str, amount: float, nip: str) -> str:
        if not self.current_turn:
            return "Error: No hay turno asignado"
        success = self.bank.withdraw(account_number, amount, nip)
        if success:
            self._log_operation("WITHDRAW", amount, account_number)
            return f"Retiro exitoso: ${amount:.2f}"
        return "Error: Fondos insuficientes, NIP incorrecto o cuenta inválida"

    def transfer(self, source_acc: str, target_acc: str, amount: float, nip: str = None) -> str:
        if not self.current_turn:
            return "Error: No hay turno asignado"
        success = self.bank.transfer(source_acc, target_acc, amount, nip)
        if success:
            self._log_operation("TRANSFER", amount, f"{source_acc} → {target_acc}")
            return f"Transferencia exitosa: ${amount:.2f}"
        return "Error: Cuentas inválidas, fondos insuficientes o NIP incorrecto"

    def transfer_between_own_accounts(self, customer_id: str, source_acc: str, target_acc: str, amount: float) -> str:
        if not self.current_turn:
            return "Error: No hay turno asignado"
        success = self.bank.transfer_between_own_accounts(customer_id, source_acc, target_acc, amount)
        if success:
            self._log_operation("INTERNAL_TRANSFER", amount, f"{source_acc} → {target_acc}")
            return f"Transferencia entre cuentas propias exitosa: ${amount:.2f}"
        return "Error: Cuentas no pertenecen al cliente o datos inválidos"

    def process_debit_payment(self, card_number: str, amount: float, merchant: str, nip: str) -> str:
        if not self.current_turn:
            return "Error: No hay turno asignado"
        success = self.bank.process_debit_payment(card_number, amount, merchant, nip)
        if success:
            self._log_operation("DEBIT_PAYMENT", amount, f"Tarjeta {card_number} en {merchant}")
            return f"Pago con débito exitoso: ${amount:.2f}"
        return "Error: Tarjeta inválida, límite excedido o NIP incorrecto"

    def pay_credit_card(self, card_number: str, from_account: str, amount: float) -> str:
        if not self.current_turn:
            return "Error: No hay turno asignado"
        success = self.bank.pay_credit_card(card_number, from_account, amount)
        if success:
            self._log_operation("CREDIT_PAYMENT", amount, f"Tarjeta {card_number} desde {from_account}")
            return f"Pago a tarjeta de crédito exitoso: ${amount:.2f}"
        return "Error: Fondos insuficientes o datos inválidos"

    def block_card_emergency(self, card_number: str) -> str:
        success = self.bank.block_card(card_number)
        if success:
            self._log_operation("BLOCK_CARD", 0, f"Tarjeta {card_number}")
            return "Tarjeta bloqueada exitosamente"
        return "Error: Tarjeta no encontrada"

    # ---- Consultas Rápidas ----
    def check_balance(self, account_number: str) -> str:
        balance = self.bank.get_account_balance(account_number)
        return f"Saldo actual: ${balance:.2f}" if balance is not None else "Cuenta no encontrada"

    # ---- Métodos Internos ----
    def _log_operation(self, op_type: str, amount: float, details: str):
        self.history.append({
            "teller_id": self.teller_id,
            "operation": op_type,
            "amount": amount,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })

    def assign_turn(self, turn: Turn):
        self.current_turn = turn
        self.available = False

    def complete_turn(self):
        self.current_turn = None
        self.available = True