from datetime import datetime
from typing import List, Dict, Optional
from core.card import CardType
from core.credit_card import CreditCard
from core.debit_card import DebitCard
from core.customer import Customer

class Turn:
    _prefix_counters = {
        "C": 1,    # Cliente no registrado
        "AZ": 1,   # Cliente normal (débito/crédito)
        "VIP": 1   # Cliente VIP (crédito premium)
    }

    def __init__(
        self,
        customer: Optional[Customer] = None,
        card: Optional[CreditCard or DebitCard] = None,
        operations: Optional[List[Dict]] = None,
        created_at: Optional[datetime] = None,
        turn_id: Optional[str] = None,
        priority: Optional[int] = None
    ):
        """
        Args:
            customer: Objeto Customer (opcional)
            card: Tarjeta asociada (opcional)
            operations: Lista de operaciones a realizar
            created_at: Fecha de creación (opcional)
            turn_id: ID personalizado (opcional)
            priority: Prioridad personalizada (opcional)
        """
        self.customer = customer
        self.card = card
        self.operations = operations or []
        
        # Configurar prioridad
        if priority is not None:
            self.priority = priority
        else:
            self.priority = self._determine_priority(card)
        
        # Generar ID de turno
        if turn_id:
            self.turn_id = turn_id
        else:
            self.prefix = self._priority_to_prefix(self.priority)
            self.turn_id = f"{self.prefix}{Turn._prefix_counters[self.prefix]:03}"
            Turn._prefix_counters[self.prefix] += 1
        
        self.created_at = created_at or datetime.now()
        self.attended = False
        self.status = "pending"  # pending, in_progress, completed, failed
        self.service_type = None  # Se establecerá al ser atendido

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

    def add_operation(self, operation_type: str, **kwargs):
        """Añade una operación al turno"""
        operation = {"type": operation_type, **kwargs}
        self.operations.append(operation)

    def assign_service_type(self, service_type: str):
        """Asigna el tipo de servicio cuando el turno es atendido"""
        self.service_type = service_type.lower()

    def mark_as_attended(self):
        self.attended = True
        self.status = "completed"

    def mark_as_failed(self):
        self.attended = True
        self.status = "failed"

    def mark_in_progress(self):
        self.status = "in_progress"

    def __lt__(self, other):
        """Comparación para ordenar por prioridad y tiempo de creación"""
        if self.priority == other.priority:
            return self.created_at < other.created_at
        return self.priority < other.priority

    def __str__(self):
        status = "Atendido" if self.attended else "Pendiente"
        service_type = self.service_type.capitalize() if self.service_type else "No asignado"
        return (f"Turno {self.turn_id} - Cliente: {self.customer.customer_id if self.customer else 'INVITADO'} - "
                f"Prioridad: {self.priority} - Servicio: {service_type} - {status} - "
                f"Operaciones: {len(self.operations)}")