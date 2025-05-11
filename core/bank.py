from typing import Dict
from core.transaction import Transaction, TransactionType
from core.account import Account

class Bank:
    def __init__(self):
        self.accounts: Dict[str, Account] = {}  # Diccionario de cuentas

    def add_account(self, account: Account):
        """Añade una cuenta al banco."""
        self.accounts[account.account_id] = account

    def deposit(self, account_id: str, amount: float) -> bool:
        """Deposita dinero en una cuenta existente."""
        if account_id not in self.accounts:
            return False
        
        account = self.accounts[account_id]
        account.balance += amount
        account.transaction_history.append(
            Transaction(TransactionType.DEPOSIT, amount)
        )
        return True

    def transfer(self, source_id: str, target_id: str, amount: float) -> bool:
        """Transfiere dinero entre cuentas."""
        # Verifica que ambas cuentas existan
        if source_id not in self.accounts or target_id not in self.accounts:
            return False

        source = self.accounts[source_id]
        target = self.accounts[target_id]

        # Verifica saldo suficiente
        if source.balance < amount:
            return False

        # Ejecuta la transferencia
        source.balance -= amount
        target.balance += amount

        # Registra transacciones
        source.transaction_history.append(
            Transaction(TransactionType.TRANSFER, amount, target_id)
        )
        target.transaction_history.append(
            Transaction(TransactionType.DEPOSIT, amount, source_id)
        )
        return True