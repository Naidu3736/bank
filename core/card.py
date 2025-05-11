from datetime import datetime, timedelta
from enum import Enum
import random

class CardCategory(Enum):
    DEBIT = "debit"
    CREDIT = "credit"

class CardType(Enum):
    NORMAL = "4"
    GOLD =  "51"
    PLATINUM = "52"

class Card:
    # Diccionario de beneficios por tipo de tarjeta
    _BENEFITS = {
        CardType.NORMAL: {
            CardCategory.DEBIT: {"fee": 0.02, "daily_limit": 5000, "cashback": 0.01},
            CardCategory.CREDIT: {"fee": 0.03, "credit_limit": 10000, "interest_rate": 0.05}
        },
        CardType.GOLD: {
            CardCategory.DEBIT: {"fee": 0.01, "daily_limit": 10000, "cashback": 0.02},
            CardCategory.CREDIT: {"fee": 0.02, "credit_limit": 20000, "interest_rate": 0.04}
        },
        CardType.PLATINUM: {
            CardCategory.DEBIT: {"fee": 0.0, "daily_limit": 20000, "cashback": 0.03},
            CardCategory.CREDIT: {"fee": 0.01, "credit_limit": 50000, "interest_rate": 0.03}
        }
    }

    @staticmethod
    def generate_card_number(card_type):
        """Genera un número de tarjeta válido según su tipo (16 dígitos)"""
        prefix = card_type.value
        remaining_length = 16 - len(prefix)
        card_number = prefix + ''.join([str(random.randint(0, 9)) for _ in range(remaining_length)])
        return card_number

    def __init__(self, card_type: CardType, category: CardCategory, account_id=None):
        self.account_id = account_id
        self.type = card_type
        self.category = category  # Categoría (Débito o Crédito)
        self.card_number = self.generate_card_number(card_type)
        self.ccv = random.randint(100, 999)  # CVV de 3 cifras
        self.expiration_date = datetime.now() + timedelta(days=365 * 5)
        self.active = False  # Empezamos desactivada
        self.benefits = self._BENEFITS[card_type][category]

    def activate_card(self):
        """Activa la tarjeta."""
        self.active = True

    def block_card(self):
        """Bloquea la tarjeta."""
        self.active = False

    def is_valid(self):
        """Verifica si la tarjeta es válida (activa y no expiró)."""
        return self.active and self.expiration_date > datetime.now()

    def __str__(self):
        return f"{self.card_number[:4]}-****-****-{self.card_number[-4:]}, Exp: {self.expiration_date.date()}, CVV: ***"

