from datetime import datetime
from typing import Any, List, Dict, Optional, Union
from enum import Enum, auto
from dataclasses import dataclass
from core.card import CardType
from core.credit_card import CreditCard
from core.debit_card import DebitCard
from core.customer import Customer

class TurnStatus(Enum):
    PENDING = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()

class ServiceType(Enum):
    TELLER = auto()
    ADVISOR = auto()

from enum import Enum, auto

class OperationType(Enum):
    # Operaciones monetarias
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"
    TRANSFER_BETWEEN_OWN = "transfer_between_own_accounts"
    
    # Operaciones de cuentas
    CREATE_ACCOUNT = "open_account"
    CLOSE_ACCOUNT = "close_account"
    GET_BALANCE = "get_account_balance"
    GET_TRANSACTIONS = "get_account_transactions"
    
    # Operaciones de clientes
    ADD_CUSTOMER = "add_customer"
    DELETE_CUSTOMER = "delete_customer"
    GET_ACCOUNTS = "get_customer_accounts"
    GET_BY_EMAIL = "get_customer_by_email"
    
    # Operaciones con tarjetas
    ISSUE_DEBIT_CARD = "issue_debit_card"
    ISSUE_CREDIT_CARD = "issue_credit_card"
    BLOCK_CARD = "block_card"
    DEACTIVATE_CARD = "deactivate_card"
    CREDIT_PAYMENT = "pay_credit_card"
    GET_CREDIT_CARD_INFO = "get_credit_card_info"
    GET_DEBIT_CARDS = "get_debit_cards"
    GET_CREDIT_CARDS = "get_credit_cards"
    GET_CARD_BALANCE = "get_card_balance"
    
    # Sistema
    GET_STATEMENT = "generate_account_statement"
    APPLY_INTEREST = "apply_monthly_interest"
    
    # Vinculación
    LINK_ACCOUNT = "link_account_to_customer"

@dataclass
class Operation:
    def __init__(self, type: OperationType, **kwargs):
        self.type = type
        self.details = kwargs
        self.details['type'] = type.value  # Asegúrate de tener esta línea
        print(f"[DEBUG] Nueva operación: {self.details}")

class Turn:
    _prefix_counters = {
        "C": 1,    # Cliente no registrado
        "AZ": 1,   # Cliente normal
        "VIP": 1   # Cliente VIP
    }

    def __init__(
        self,
        operations: Optional[List[Union[Dict, Operation]]] = None,
        customer: Optional[Customer] = None,
        card: Optional[Union[CreditCard, DebitCard]] = None,
        created_at: Optional[datetime] = None,
        turn_id: Optional[str] = None,
        priority: Optional[int] = None
    ):
        """
        Args:
            operations: Lista de operaciones (dicts u objetos Operation)
            customer: Cliente asociado al turno
            card: Tarjeta asociada (crédito/débito)
            created_at: Fecha de creación personalizada
            turn_id: ID personalizado
            priority: Prioridad personalizada (1-3)
        """
        self.customer = customer
        self.card = card
        self.operations = [op if isinstance(op, Operation) else Operation(**op) 
                         for op in (operations or [])]
        
        self.priority = priority or self._determine_priority(card)
        self.turn_id = turn_id or self._generate_turn_id()
        self.created_at = created_at or datetime.now()
        self.status = TurnStatus.PENDING
        self.service_type: Optional[ServiceType] = None
        self.attended = False

    def _determine_priority(self, card) -> int:
        """Determina la prioridad basada en el tipo de tarjeta"""
        if not card:
            return 3  # Prioridad más baja

        priority_map = {
            CardType.PLATINUM: 1,
            CardType.GOLD: 1,
            CardType.STANDARD: 2,
            None: 3  # Para tarjetas sin tipo definido
        }

        if isinstance(card, CreditCard):
            return priority_map.get(card.type, 2)
        return 2  # Débito siempre prioridad media

    def _generate_turn_id(self) -> str:
        """Genera un ID de turno único basado en prioridad"""
        prefix = self._priority_to_prefix(self.priority)
        turn_id = f"{prefix}{Turn._prefix_counters[prefix]:03}"
        Turn._prefix_counters[prefix] += 1
        return turn_id

    @staticmethod
    def _priority_to_prefix(priority: int) -> str:
        """Mapea prioridad numérica a prefijo alfabético"""
        return {
            1: "VIP",
            2: "AZ",
            3: "C"
        }[priority]

    def add_operation(self, operation_type: str, **kwargs) -> None:
        """Añade una nueva operación al turno"""
        self.operations.append(Operation(type=operation_type, details=kwargs))

    def assign_service(self, service_type: ServiceType) -> None:
        """Asigna el tipo de servicio que atenderá el turno"""
        self.service_type = service_type
        self.mark_in_progress()

    def mark_in_progress(self) -> None:
        self.status = TurnStatus.IN_PROGRESS

    def mark_completed(self) -> None:
        self.status = TurnStatus.COMPLETED
        self.attended = True

    def mark_failed(self) -> None:
        self.status = TurnStatus.FAILED
        self.attended = True

    def __lt__(self, other: 'Turn') -> bool:
        """Comparación para ordenar por prioridad y tiempo de creación"""
        if self.priority == other.priority:
            return self.created_at < other.created_at
        return self.priority < other.priority

    def __str__(self) -> str:
        customer_id = getattr(self.customer, 'customer_id', 'INVITADO')
        service = self.service_type.name if self.service_type else "No asignado"
        return (
            f"Turno {self.turn_id} - Cliente: {customer_id} - "
            f"Prioridad: {self.priority} ({self._priority_to_prefix(self.priority)}) - "
            f"Servicio: {service} - Estado: {self.status.name} - "
            f"Operaciones: {len(self.operations)}"
        )

    @property
    def is_high_priority(self) -> bool:
        return self.priority == 1

    @property
    def requires_advisor(self) -> bool:
        """Determina si el turno requiere un asesor"""
        advisor_ops = {
            OperationType.CREATE_ACCOUNT,
            OperationType.CLOSE_ACCOUNT,
            OperationType.ADD_CUSTOMER,
            OperationType.DELETE_CUSTOMER,
            OperationType.ISSUE_DEBIT_CARD,
            OperationType.ISSUE_CREDIT_CARD,
            OperationType.DEACTIVATE_CARD,
            OperationType.LINK_ACCOUNT
        }
        return any(op.type in advisor_ops for op in self.operations)