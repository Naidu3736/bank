from datetime import datetime
from core.card import CardCategory, CardType  # Asegúrate de importar bien esto

class Turn:
    _prefix_counters = {
        "C": 1,    # No cliente o sin tarjeta
        "AZ": 1,   # Débito básica
        "VIP": 1   # Crédito premium
    }

    def __init__(self, customer=None, card=None, created_at=None):
        self.customer_id = customer.customer_id if customer else "INVITADO"
        self.priority = self._determine_priority(card)
        self.prefix = self._priority_to_prefix(self.priority)
        self.turn_id = f"{self.prefix}{Turn._prefix_counters[self.prefix]:03}"
        Turn._prefix_counters[self.prefix] += 1

        self.created_at = created_at or datetime.now()
        self.attended = False


    def _determine_priority(self, card):
        if not card:
            return 3  # No tarjeta, prioridad baja
    	
        # Si la tarjeta es de credito
        if card.category == CardCategory.CREDIT:
            # Alta prioridad para platinum y gold
            if card.card_type in (CardType.PLATINUM, CardType.GOLD):
                return 1
            # Prioridad media para tarjetas de crédito normales
            return 2
        # Si la tarjeta es de débito, prioridad media
        elif card.category == CardCategory.DEBIT:
            return 2

        # En dado caso de no ser cliente del banco
        return 3


    def _priority_to_prefix(self, priority):
        return {
            3: "C",
            2: "AZ",
            1: "VIP"
        }[priority]

    # Marca que el turno como atendido
    def mark_as_attended(self):
        self.attended = True

    # Métodos necesarios para la cola de prioridad, y tal vez la cosola de eventos
    def __lt__(self, other):
        if self.priority == other.priority:
            return self.created_at < other.created_at
        return self.priority < other.priority

    def __str__(self):
        status = "Atendido" if self.attended else "Pendiente"
        return f"Turno {self.turn_id} - Cliente: {self.customer_id} - Prioridad: {self.priority} - {status}"
