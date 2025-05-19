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
                    self.turn_manager.add_turn(turn)  # Re-add to queue
                    
            except Empty:
                continue
                
    # Modificar el método _assign_handler
    def _assign_handler(self, turn):
        """Asigna turno a handler (teller o advisor) disponible."""
        # Determinar el tipo de servicio basado en las operaciones
        service_type = self._determine_service_type(turn.operations)
        turn.assign_service_type(service_type)  # Asignar el tipo de servicio
        
        handler_pool = self.tellers if service_type == "teller" else self.advisors
        with self.locks.teller_pool_lock:
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

    # Añadir nuevo método para determinar el tipo de servicio
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
        
    def _prepare_operations(self, turn, handler):
        operations = []
        for op in turn.operations:
            op_type = op['type']
            if op_type == 'withdrawal' and hasattr(handler, 'process_withdrawal'):
                operations.append(lambda: handler.process_withdrawal(
                    op['account_number'], op['amount'], op['nip']
                ))
            elif op['type'] == 'deposit' and hasattr(handler, 'process_deposit'):
                operations.append(lambda: handler.process_deposit(
                    op['account_number'], op['amount']
                ))
            elif op['type'] == 'transfer' and hasattr(handler, 'process_transfer'):
                operations.append(lambda: handler.process_transfer(
                    op['source_account'], op['target_account'], op['amount'], op.get('nip')
                ))
            elif op['type'] == 'transfer_between_own_accounts' and hasattr(handler, 'process_transfer_between_own_accounts'):
                operations.append(lambda: handler.process_transfer_between_own_accounts(
                    op['customer_id'], op['source_account'], op['target_account'], op['amount']
                ))
                
            # Operaciones de cuentas
            elif op['type'] == 'create_account' and hasattr(handler, 'create_account'):
                operations.append(lambda: handler.create_account(
                    op['customer_id'], op.get('initial_balance', 0), op.get('nip')
                ))
            elif op['type'] == 'close_account' and hasattr(handler, 'close_account'):
                operations.append(lambda: handler.close_account(
                    op['account_number']
                ))
            elif op['type'] == 'get_account_balance' and hasattr(handler, 'get_account_balance'):
                operations.append(lambda: handler.get_account_balance(
                    op['account_number']
                ))
            elif op['type'] == 'get_account_transactions' and hasattr(handler, 'get_account_transactions'):
                operations.append(lambda: handler.get_account_transactions(
                    op['account_number'], op.get('limit', 10)
                ))
                
            # Operaciones de clientes
            elif op['type'] == 'add_customer' and hasattr(handler, 'add_customer'):
                operations.append(lambda: handler.add_customer(
                    op['name'], op['email']
                ))
            elif op['type'] == 'delete_customer' and hasattr(handler, 'delete_customer'):
                operations.append(lambda: handler.delete_customer(
                    op['customer_id']
                ))
            elif op['type'] == 'get_customer_accounts' and hasattr(handler, 'get_customer_accounts'):
                operations.append(lambda: handler.get_customer_accounts(
                    op['customer_id']
                ))
            elif op['type'] == 'get_customer_by_email' and hasattr(handler, 'get_customer_by_email'):
                operations.append(lambda: handler.get_customer_by_email(
                    op['email']
                ))
                
            # Operaciones de tarjetas
            elif op['type'] == 'issue_debit_card' and hasattr(handler, 'issue_debit_card'):
                operations.append(lambda: handler.issue_debit_card(
                    op['account_number'], op['card_type']
                ))
            elif op['type'] == 'issue_credit_card' and hasattr(handler, 'issue_credit_card'):
                operations.append(lambda: handler.issue_credit_card(
                    op['customer_id'], op['card_type']
                ))
            elif op['type'] == 'block_card' and hasattr(handler, 'block_card'):
                operations.append(lambda: handler.block_card(
                    op['card_number']
                ))
            elif op['type'] == 'deactivate_card' and hasattr(handler, 'deactivate_card'):
                operations.append(lambda: handler.deactivate_card(
                    op['card_number']
                ))
            elif op['type'] == 'pay_credit_card' and hasattr(handler, 'pay_credit_card'):
                operations.append(lambda: handler.pay_credit_card(
                    op['card_number'], op['amount'], op.get('payment_source'), op.get('is_cash', False)
                ))
            elif op['type'] == 'get_credit_card_info' and hasattr(handler, 'get_credit_card_info'):
                operations.append(lambda: handler.get_credit_card_info(
                    op['card_number']
                ))
            elif op['type'] == 'get_debit_cards' and hasattr(handler, 'get_debit_cards'):
                operations.append(lambda: handler.get_debit_cards(
                    op['account_number']
                ))
            elif op['type'] == 'get_credit_cards' and hasattr(handler, 'get_credit_cards'):
                operations.append(lambda: handler.get_credit_cards(
                    op['customer_id']
                ))
            elif op['type'] == 'get_card_balance' and hasattr(handler, 'get_card_balance'):
                operations.append(lambda: handler.get_card_balance(
                    op['card_number']
                ))
                
            # Operaciones de consultas y reportes
            elif op['type'] == 'generate_account_statement' and hasattr(handler, 'generate_account_statement'):
                operations.append(lambda: handler.generate_account_statement(
                    op['account_number'], op.get('days', 30)
                ))
            elif op['type'] == 'apply_monthly_interest' and hasattr(handler, 'apply_monthly_interest'):
                operations.append(lambda: handler.apply_monthly_interest())
                
            # Vinculación cuenta-cliente
            elif op['type'] == 'link_account_to_customer' and hasattr(handler, 'link_account_to_customer'):
                operations.append(lambda: handler.link_account_to_customer(
                    op['account_number'], op['customer_id']
                ))
                
        return operations[:3]  # Limitar a 3 operaciones