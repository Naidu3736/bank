from datetime import datetime
from core.card import CardType
from core.credit_card import CreditCard
from core.debit_card import DebitCard

class Turn:
    _prefix_counters = {
        "C": 1,    # Cliente no registrado
        "AZ": 1,   # Cliente normal (débito/crédito)
        "VIP": 1   # Cliente VIP (crédito premium)
    }

    def __init__(self, service_type: str, customer=None, card=None, created_at=None):
        """
        service_type: str - Tipo de atención ('teller' o 'advisor')
        customer: Customer o None
        card: Card (opcional)
        """
        self.service_type = service_type.lower()  # 'teller' o 'advisor'
        self.customer_id = customer.customer_id if customer else "INVITADO"
        self.priority = self._determine_priority(card)
        self.prefix = self._priority_to_prefix(self.priority)
        self.turn_id = f"{self.prefix}{Turn._prefix_counters[self.prefix]:03}"
        Turn._prefix_counters[self.prefix] += 1

        self.created_at = created_at or datetime.now()
        self.attended = False

    def _determine_priority(self, card):
        if not card:
            return 3  # No tiene tarjeta = baja prioridad

        if isinstance(card, CreditCard):
            if card.card_type in (CardType.PLATINUM, CardType.GOLD):
                return 1  # VIP
            return 2  # Crédito común

        elif isinstance(card, DebitCard):
            return 2  # Medio

        return 3  # Otro caso raro

    def _priority_to_prefix(self, priority):
        return {
            3: "C",    # Cliente nuevo o sin tarjeta
            2: "AZ",   # Cliente medio
            1: "VIP"   # Cliente importante
        }[priority]

    def mark_as_attended(self):
        self.attended = True

    def __lt__(self, other):
        if self.priority == other.priority:
            return self.created_at < other.created_at
        return self.priority < other.priority

    def __str__(self):
        status = "Atendido" if self.attended else "Pendiente"
        return (f"Turno {self.turn_id} - Cliente: {self.customer_id} - "
                f"Prioridad: {self.priority} - Servicio: {self.service_type.capitalize()} - {status}")
