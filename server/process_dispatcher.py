import sys
import os
import traceback
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.turn import TurnStatus
from server.locks import BankLocks
from server.turn_manger import TurnManager
from server.teller import Teller
from server.advisor import Advisor
from server.run_process import run_process
from core.turn import Operation, Turn, OperationType, TurnStatus
from functools import partial
from event_logger import EventConsole, ProcessTracker
import threading
import time

class ProcessDispatcher:
    def __init__(self, bank, num_tellers=3, num_advisors=2, event_console=None, process_tracker=None):
        self.bank = bank
        self.locks = BankLocks(process_tracker=process_tracker)
        self.turn_manager = TurnManager(event_console=event_console)
        self.tellers = [Teller(f"T{i+1}", bank) for i in range(num_tellers)]
        self.advisors = [Advisor(f"A{j+1}", bank) for j in range(num_advisors)]
        self.event_console = event_console
        self.process_tracker = process_tracker
        self._running = threading.Event()
        self._running.set()
        self._running_interval = 0.5  # tiempo entre intentos de despacho

    def assign_turn(self, turn: Turn):
        """Agrega el turno a la cola segura con logging."""
        with self.locks.turn_queue_lock:
            print(f"[DEBUG] Asignando turno {turn.turn_id} con {len(turn.operations)} operaciones")
            self.turn_manager.add_turn(turn)
            self._log_event("TURN_ADDED", f"Turn {turn.turn_id} added to queue", "info")

    def dispatch_processes(self):
        print("[DEBUG] Hilo de dispatcher iniciado")

        pid = threading.get_ident()
        self._update_process_state(pid, "ready", "Esperando turnos", type="Dispatcher")

        while self._running.is_set():
            try:
                self._update_process_state(pid, "waiting", "Buscando siguiente turno", type="Dispatcher")
                turn = self._get_next_turn()
                if not turn:
                    time.sleep(self._running_interval)
                    continue

                self._update_process_state(pid, "processing", f"Procesando turno {turn.turn_id}", type="TurnManager")
                self._handle_turn(turn)

            except Exception as e:
                self._log_event("DISPATCH_ERROR", str(e), "error")
                traceback.print_exc()
                time.sleep(1)

    def _get_next_turn(self):
        with self.locks.turn_queue_lock:
            turn = self.turn_manager.get_next_turn()
            print(f"[DEBUG] Obtenido turno: {turn.turn_id if turn else 'None'}")
            return turn

    def _handle_turn(self, turn: Turn):
        """Determina si requiere asesor o cajero y lanza el proceso."""
        if turn.requires_advisor:
            self._launch_handler_process(turn, self.advisors, self.locks.advisors_sem, 'advisor')
        else:
            self._launch_handler_process(turn, self.tellers, self.locks.tellers_sem, 'teller')

    def _launch_handler_process(self, turn: Turn, handler_pool, semaphore, handler_type: str):
        if not semaphore.acquire(blocking=False):
            self._log_event("SEMAPHORE_FULL", f"No hay {handler_type}s disponibles", "warning")
            print(f"[DEBUG] Clientes actuales: {len(self.bank.customers)}")
            self.assign_turn(turn)
            return

        handler = next((h for h in handler_pool if not h.current_turn), None)
        if not handler:
            semaphore.release()
            self.assign_turn(turn)
            return

        handler.assign_turn(turn)
        operations = self._prepare_operations(turn, handler)

        def run():
            try:
                run_process(threading.get_ident(), turn, operations, handler, self.process_tracker)
            finally:
                handler.complete_turn()
                handler.current_thread = None
                semaphore.release()
                self.turn_manager.update_turn_status(turn.turn_id, TurnStatus.COMPLETED)

        t = threading.Thread(target=run, daemon=True)
        t.start()
        handler.current_thread = t

    def _prepare_operations(self, turn: Turn, handler) -> list:
        prepared = []
        for op in turn.operations:
            print(f"[DEBUG] Preparando operación: {op.type} con detalles: {op.details}")
            method = self._get_handler_method(handler, op)
            if method:
                prepared.append(partial(method, **{k: v for k, v in op.details.items() if k != 'type'}))
        return prepared

    def _get_handler_method(self, handler, operation: Operation):
        op_type = (operation.type.value if isinstance(operation.type, OperationType) else operation.type)
        print(f"[DEBUG] Handler: {handler.__class__.__name__}, operación recibida: '{op_type}'")
        
        mapping = {
            OperationType.DEPOSIT.value: 'deposit',
            OperationType.WITHDRAWAL.value: 'withdraw',
            OperationType.TRANSFER.value: 'transfer',
            OperationType.CREDIT_PAYMENT.value: 'pay_credit_card',
            OperationType.ADD_CUSTOMER.value: 'create_customer',
            OperationType.CREATE_ACCOUNT.value: 'open_account',
            OperationType.ISSUE_CREDIT_CARD.value: 'issue_credit_card',
            OperationType.ISSUE_DEBIT_CARD.value: 'issue_debit_card',
            OperationType.LINK_ACCOUNT.value: 'link_account',
            OperationType.GET_BALANCE.value: 'check_balance',
            OperationType.GET_STATEMENT.value: 'generate_account_statement',
            OperationType.GET_CREDIT_CARD_INFO.value: 'get_credit_card_info',
        }
        
        method_name = mapping.get(op_type)
        if method_name and hasattr(handler, method_name):
            return getattr(handler, method_name)
        else:
            self._log_event("OP_MAP_ERROR", f"No se encontró método para {op_type} en {handler.__class__.__name__}", "warning")
            print(f"[WARN] No método '{method_name}' para operación '{op_type}' en handler '{handler.__class__.__name__}'")
            return None

    def stop(self):
        self._running.clear()

    def _log_event(self, operation: str, details: str, status: str):
        self.event_console.add_event(os.getpid(), operation, details, status)

    def _update_process_state(self, pid: int, state: str, operation: str, type: str = None):
        if self.process_tracker:
            self.process_tracker.update_process(pid, state=state, current_operation=operation, type=type)

