from datetime import datetime
from core.turn import Turn
from server.processes.system_calls import fast_transactions, account_queries

class Teller:
    def __init__(self, teller_id: str, bank):
        self.teller_id = teller_id
        self.bank = bank
        self.available = True
        self.current_turn = None
        self.history = []

    def deposit(self, account_number: str, amount: float) -> str:
        success = fast_transactions.deposit(self.bank, account_number, amount)
        return f"Depósito de ${amount} realizado" if success else "Error en depósito"

    def check_balance(self, account_number: str) -> str:
        balance = account_queries.get_balance(self.bank, account_number)
        return f"Saldo: ${balance}" if balance is not None else "Cuenta no encontrada"

    def assign_turn(self, turn: Turn):
        self.current_turn = turn
        self.available = False
        print(f"[Teller {self.teller_id}] Turno {turn.turn_id} asignado.")

    def attend_turn(self, operation_funcs: list):
        if not self.current_turn:
            print(f"[Teller {self.teller_id}] No hay turno asignado.")
            return

        print(f"[Teller {self.teller_id}] Atendiendo turno {self.current_turn.turn_id}")
        operaciones_ejecutadas = 0

        for func in operation_funcs[:3]:  # Máximo 3 operaciones
            try:
                func()
                operaciones_ejecutadas += 1
            except Exception as e:
                print(f"[Teller {self.teller_id}] Error: {str(e)}")

        self.current_turn.mark_as_attended()
        self.log_turn(operaciones_ejecutadas)
        self.current_turn = None
        self.available = True

    def log_turn(self, operaciones: int):
        self.history.append({
            "turn_id": self.current_turn.turn_id,
            "operaciones": operaciones,
            "timestamp": datetime.now()
        })

    def reset(self):
        self.current_turn = None
        self.available = True
        print(f"[Teller {self.teller_id}] Reiniciado.")