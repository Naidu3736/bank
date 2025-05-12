from enum import Enum
from datetime import datetime
import uuid

class TransactionType(Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"
    PURCHASE = "purchase"
    PAYMENT = "payment"

class Transaction:
    def __init__(self, account_id, amount, transaction_type, 
                 target_account_id=None, merchant=None, card_number=None):
        self.transaction_id = self._generator_transaction_id()    # Identificador de la transacción
        self.account_id = account_id    # Identificador de la cuenta de origen de la transacción
        self.amount = amount    # Cantidad a operar del saldo
        self.type = TransactionType(transaction_type)    # Tipo de transacción que se utilizara
        self.timestamp = datetime.now() # Hora en que realizo la transacción

        # Se asigna el id del receptor si y solo si es una transferencia
        self.target_account_id = target_account_id  if transaction_type == TransactionType.TRANSFER else None

        self.merchant = merchant
        self.card_number = card_number

    def _generator_transaction_id(self):
        return str(uuid.uuid4)