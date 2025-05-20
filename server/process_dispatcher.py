import multiprocessing
from queue import Empty
from server.turn_manger import TurnManager
from server.locks import BankLocks
from server.teller import Teller
from server.advisor import Advisor
from core.turn import Turn
from server.run_process import run_process
from event_logger import EventConsole, ProcessTracker
import os

class ProcessDispatcher:
    def __init__(self, bank, num_tellers=3, num_advisors=2, event_console=None, process_tracker=None):
        if not bank:
            raise ValueError("Bank instance is required")
        self.bank = bank
        self.locks = BankLocks()
        self.turn_manager = TurnManager()
        self.tellers = [Teller(f"T{i+1}", bank) for i in range(num_tellers)]
        self.advisors = [Advisor(f"A{j+1}", bank) for j in range(num_advisors)]
        self.operation_queue = multiprocessing.Queue()
        self.event_console = event_console or EventConsole()
        self.process_tracker = process_tracker or ProcessTracker()
        
    def assign_turn(self, turn: Turn):
        """Asigna un turno al sistema"""
        with self.locks.turn_queue_lock:
            self.turn_manager.add_turn(turn)
            self.event_console.add_event(
                os.getpid(),
                "TURN_ADDED",
                f"Turn {turn.turn_id} added to queue",
                "info"
            )
            
    def dispatch_processes(self):
        """Despacha procesos según disponibilidad de recursos"""
        pid = os.getpid()
        self.process_tracker.update_process(
            pid,
            state="ready",
            current_operation="Waiting for turns"
        )
        
        while True:
            try:
                self.process_tracker.update_process(
                    pid,
                    state="waiting",
                    current_operation="Checking for new turns"
                )
                
                # Buscar el siguiente turno
                with self.locks.turn_queue_lock:
                    turn = self.turn_manager.get_next_turn()
                    if not turn:
                        continue
                        
                self.process_tracker.update_process(
                    pid,
                    state="processing",
                    current_operation=f"Dispatching turn {turn.turn_id}"
                )
                
                # Asignar a handler disponible
                if not self._assign_handler(turn):
                    self.event_console.add_event(
                        pid,
                        "NO_HANDLERS",
                        f"No available handlers for turn {turn.turn_id}",
                        "warning"
                    )
                    with self.locks.turn_queue_lock:
                        self.turn_manager.add_turn_to_end(turn)  # Re-add to end of queue
                    
            except Empty:
                continue
                
    def _assign_handler(self, turn):
        service_type = self._determine_service_type(turn.operations)
        turn.assign_service_type(service_type)
        
        handler_pool = self.tellers if service_type == "teller" else self.advisors
        lock = self.locks.teller_pool_lock if service_type == "teller" else self.locks.advisor_pool_lock
        
        with lock:
            for handler in handler_pool:
                if handler.available:
                    handler.assign_turn(turn)
                    operations = self._prepare_operations(turn, handler)
                    if operations:
                        process = multiprocessing.Process(
                            target=run_process,
                            args=(turn, operations))
                        process.start()
                        
                        self.event_console.add_event(
                            os.getpid(),
                            "PROCESS_STARTED",
                            f"Started process for turn {turn.turn_id} ({service_type})",
                            "info"
                        )
                        return True
        return False

    def _determine_service_type(self, operations):
        """Determina si las operaciones son de teller o advisor."""
        advisor_ops = {
            'create_account', 'close_account', 'add_customer', 
            'delete_customer', 'issue_debit_card', 'issue_credit_card',
            'deactivate_card', 'link_account_to_customer'
        }
        
        for op in operations:
            if op['type'] in advisor_ops:
                return "advisor"
        return "teller"
        
    def _validate_operation(self, op):
        """Valida que la operación tenga los campos requeridos."""
        required_fields = {
            'withdrawal': ['account_number', 'amount', 'nip'],
            'deposit': ['account_number', 'amount'],
            'transfer': ['source_account', 'target_account', 'amount'],
            'transfer_between_own_accounts': ['customer_id', 'source_account', 'target_account', 'amount'],
            'create_account': ['customer_id'],
            # Agregar todas las operaciones con sus campos requeridos
        }
        
        if op['type'] not in required_fields:
            return False
        return all(field in op for field in required_fields[op['type']])
        
    def _prepare_operations(self, turn, handler):
        """Prepara las operaciones para ejecución, validando cada una."""
        operations = []
        for op in turn.operations:
            if not self._validate_operation(op):
                self.event_console.add_event(
                    os.getpid(),
                    "INVALID_OPERATION",
                    f"Invalid operation data: {op}",
                    "warning"
                )
                continue
                
            op_type = op['type']
            try:
                if op_type == 'withdrawal' and hasattr(handler, 'process_withdrawal'):
                    operations.append(lambda op=op: handler.process_withdrawal(
                        op['account_number'], op['amount'], op['nip']
                    ))
                elif op_type == 'deposit' and hasattr(handler, 'process_deposit'):
                    operations.append(lambda op=op: handler.process_deposit(
                        op['account_number'], op['amount']
                    ))
                elif op_type == 'transfer' and hasattr(handler, 'process_transfer'):
                    operations.append(lambda op=op: handler.process_transfer(
                        op['source_account'], op['target_account'], op['amount'], op.get('nip')
                    ))
                # ... (todas las demás operaciones con el mismo patrón lambda op=op: ...)
                
                elif op_type == 'apply_monthly_interest' and hasattr(handler, 'apply_monthly_interest'):
                    operations.append(lambda: handler.apply_monthly_interest())
                    
                else:
                    self.event_console.add_event(
                        os.getpid(),
                        "UNKNOWN_OPERATION",
                        f"Unknown operation type: {op_type}",
                        "warning"
                    )
                    
            except Exception as e:
                self.event_console.add_event(
                    os.getpid(),
                    "OPERATION_PREP_ERROR",
                    f"Error preparing operation {op_type}: {str(e)}",
                    "error"
                )
        
        return operations[:3]  # Limitar a 3 operaciones (considerar hacer configurable)