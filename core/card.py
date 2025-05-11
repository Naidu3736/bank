from enum import Enum
import random

class CardType(Enum):
    NORMAL = "4"
    GOLD =  "51"
    PLATINUM = "52"

def generate_card_number(card_type: CardType):
    """Genera un número de tarjeta válido según su tipo (16 dígitos)"""
    prefix = card_type.value
    remaining_length = 16 - len(prefix)
    card_number = prefix + ''.join([str(random.randint(0, 9)) for _ in range(remaining_length)])
    return card_number
