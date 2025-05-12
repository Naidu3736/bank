from datetime import datetime

class Turn:
    _prefix_counters = {
        "C": 1,    # Clientes sin tarjeta o baja prioridad
        "AZ": 1,   # Clientes con tarjeta GOLD, prioridad media
        "VIP": 1   # Clientes PLATINUM o alta prioridad
    }

    PRIORITY_PREFIX = {
        3: "C",     # Baja prioridad
        2: "AZ",    # Media prioridad
        1: "VIP"    # Alta prioridad
    }

    def __init__(self, customer_id: str, priority: int, created_at=None):
        if priority not in Turn.PRIORITY_PREFIX:
            raise ValueError("Prioridad no válida")

        self.prefix = Turn.PRIORITY_PREFIX[priority]
        self.turn_id = f"{self.prefix}{Turn._prefix_counters[self.prefix]:03}"
        Turn._prefix_counters[self.prefix] += 1

        self.customer_id = customer_id
        self.priority = priority  # Menor valor = mayor prioridad
        self.created_at = created_at or datetime.now()
        self.attended = False

    def mark_as_attended(self):
        self.attended = True

    def __lt__(self, other):
        if self.priority == other.priority:
            return self.created_at < other.created_at
        return self.priority < other.priority

    def __str__(self):
        status = "Atendido" if self.attended else "Pendiente"
        return f"Turno {self.turn_id} - Cliente: {self.customer_id} - Prioridad: {self.priority} - {status}"
