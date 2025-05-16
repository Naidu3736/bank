from datetime import datetime
from core.turn import Turn

class Teller:
    def __init__(self, teller_id: str):
        self.teller_id = teller_id
        self.available = True
        self.current_turn = None
        self.history = []  # Historial de turnos atendidos

    def assign_turn(self, turn: Turn):
        """Asigna un turno a esta ventanilla."""
        self.current_turn = turn
        self.available = False
        print(f"[Teller {self.teller_id}] Turno {turn.turn_id} asignado.")

    def attend_turn(self, operation_funcs: list):
        """
        Atiende el turno actual ejecutando hasta 3 operaciones (funciones).
        `operation_funcs` debe ser una lista de funciones ya configuradas para ejecutar.
        """
        if not self.current_turn:
            print(f"[Teller {self.teller_id}] No hay turno asignado.")
            return

        print(f"[Teller {self.teller_id}] Atendiendo turno {self.current_turn.turn_id} (cliente {self.current_turn.customer_id})")

        operaciones_ejecutadas = 0
        for func in operation_funcs:
            if operaciones_ejecutadas >= 3:
                print(f"[Teller {self.teller_id}] Límite de 3 operaciones alcanzado.")
                break
            try:
                func()  # Aquí puedes correr procesos si el dispatcher lo gestiona
                operaciones_ejecutadas += 1
            except Exception as e:
                print(f"[Teller {self.teller_id}] Error en operación: {e}")

        self.current_turn.mark_as_attended()
        self.log_turn(self.current_turn, operaciones_ejecutadas)
        print(f"[Teller {self.teller_id}] Turno {self.current_turn.turn_id} finalizado.")
        
        self.current_turn = None
        self.available = True

    def log_turn(self, turn: Turn, operaciones: int):
        self.history.append({
            "turn_id": turn.turn_id,
            "customer_id": turn.customer_id,
            "attended_at": datetime.now(),
            "operations_executed": operaciones
        })

    def reset(self):
        """Resetea la ventanilla en caso de error o interrupción."""
        self.current_turn = None
        self.available = True
        print(f"[Teller {self.teller_id}] Reset de estado ejecutado.")
