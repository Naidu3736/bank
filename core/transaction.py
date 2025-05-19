from enum import Enum
from datetime import datetime, timedelta
import uuid

class TransactionType(Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"
    PAYMENT = "payment"

class Transaction:
    def __init__(self, account_id: str, amount: float, transaction_type: TransactionType,
                 card_number: str = None, description: str = None,
                 source_reference: str = None, is_cash: bool = False):
        self.transaction_id = str(uuid.uuid4())
        self.account_id = account_id
        self.amount = amount
        self.type = transaction_type
        self.timestamp = datetime.now()
        self.card_number = card_number
        self.description = description
        self.source_reference = source_reference
        self.is_cash = is_cash

    def is_recent(self, days: int) -> bool:
        """Determina si la transacción es reciente (dentro de X días)"""
        return datetime.now() - self.timestamp < timedelta(days=days)

    def __str__(self):
        return (f"{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')} - "
                f"{self.type.name}: ${self.amount:.2f}")