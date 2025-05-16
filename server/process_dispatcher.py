import multiprocessing
from queue import Empty
from server.turn_manger import TurnManager
from server.locks import BankLocks
from core.teller import Teller
from core.advisor import Advisor
from core.turn import Turn
from server.run_process import run_process

class ProcessDispatcher:
    def __init__(self, bank, num_tellers=3, num_advisors=2):
        self.bank = bank
        self.locks = BankLocks()
        self.turn_manager = TurnManager()
        self.tellers = [Teller(f"T{i+1}") for i in range(num_tellers)]
        self.advisors = [Advisor(bank) for _ in range(num_advisors)]
        self.operation_queue = multiprocessing.Queue()
        
    def assign_turn(self, turn: Turn):
        """Asigna un turno al sistema"""
        with self.locks.turn_queue_lock:
            self.turn_manager.add_turn(turn)
            print(f"Turno {turn.turn_id} agregado al sistema")
            
    def dispatch_processes(self):
        """Despacha procesos según disponibilidad de recursos"""
        while True:
            try:
                # Buscar el siguiente turno
                with self.locks.turn_queue_lock:
                    turn = self.turn_manager.get_next_turn()
                    if not turn:
                        continue
                        
                # Asignar a ventanilla o asesor según tipo de servicio
                if turn.service_type == "teller":
                    self._assign_to_teller(turn)
                else:
                    self._assign_to_advisor(turn)
                    
            except Empty:
                continue
                
    def _assign_to_teller(self, turn):
        """Asigna un turno a una ventanilla disponible"""
        with self.locks.teller_pool_lock:
            for teller in self.tellers:
                if teller.available:
                    teller.assign_turn(turn)
                    # Convertir operaciones a funciones ejecutables
                    operations = self._prepare_operations(turn, teller)
                    # Ejecutar procesos con round-robin
                    process = multiprocessing.Process(
                        target=run_process,
                        args=(turn, operations))
                    process.start()
                    break
                    
    def _assign_to_advisor(self, turn):
        """Asigna un turno a un asesor disponible"""
        with self.locks.teller_pool_lock:
            for advisor in self.advisors:
                # Implementar lógica similar a ventanilla
                operations = self._prepare_advisor_operations(turn, advisor)
                if operations:
                    process = multiprocessing.Process(
                        target=run_process,
                        args=(turn, operations))
                    process.start()
                    break
    
    def _prepare_operations(self, turn, teller):
        """Prepara las operaciones para ejecución"""
        operations = []
        for op in turn.operations:
            if op['type'] == 'withdrawal':
                operations.append(lambda: teller.process_withdrawal(
                    op['account_number'],
                    op['amount'],
                    op['nip']))
            # Agregar más tipos de operaciones aquí
        return operations[:3]  # Limitar a 3 operaciones
        
    def _prepare_advisor_operations(self, turn, advisor):
        """Prepara operaciones para asesor"""
        operations = []
        for op in turn.operations:
            if op['type'] == 'create_account':
                operations.append(lambda: advisor.create_account(
                    op['customer_name'],
                    op['email'],
                    op['nip'],
                    op.get('initial_balance', 0)))
            # Agregar más tipos de operaciones de asesor aquí
        return operations[:3]

