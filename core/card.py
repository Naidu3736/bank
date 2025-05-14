from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from enum import Enum
import random
import uuid

class CardType(Enum):
    NORMAL = "4"
    GOLD = "51"
    PLATINUM = "52"

class Card(ABC):
    def __init__(self, card_type: CardType):
        self.card_id = str(uuid.uuid4())
        self.type = card_type
        self.card_number = self.generate_card_number(card_type)
        self.ccv = random.randint(100, 999)
        self.expiration_date = datetime.now() + timedelta(days=365 * 5)
        self.active = False

    @staticmethod
    def generate_card_number(card_type):
        prefix = card_type.value
        return prefix + ''.join([str(random.randint(0, 9)) for _ in range(16 - len(prefix))])
    
    def is_expired(self) -> bool:
        return datetime.now() > self.expiration_date

    def activate_card(self):
        self.active = True

    def block_card(self):
        self.active = False

    def is_valid(self):
        return self.active and self.expiration_date > datetime.now()

    @abstractmethod
    def __str__(self):
        pass
