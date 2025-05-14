import threading
from queue import PriorityQueue
from datetime import datetime
import time
from enum import Enum, auto
import random
import string
from core.bank import Bank
from core.teller import Teller
from core.turn import Turn

class SyncType(Enum):
    MUTEX = auto()
    SEMAPHORE = auto()

class BankSystem:
    def __init__(self):
        self.bank = Bank()
        self.tellers = {}
        self.turn_queue = PriorityQueue()
        
        # Sincronización
        self.account_creation_lock = threading.Lock()
        self.transaction_lock = threading.Lock()
        self.teller_semaphore = threading.Semaphore(3)  # 3 ventanillas disponibles
        
        # Procesos activos
        self.active_processes = {}
        self.process_counter = 0
        
        # Iniciar scheduler de procesos
        self.scheduler_thread = threading.Thread(target=self._schedule_processes, daemon=True)
        self.scheduler_thread.start()

    def _generate_id(self, length=10):
        """Genera un ID aleatorio"""
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

    def add_teller(self, teller_id: str):
        """Añade un cajero al sistema"""
        with self.account_creation_lock:
            teller = Teller(self.bank, teller_id)
            self.tellers[teller_id] = teller
            return teller

    def create_customer(self, name: str, email: str) -> dict:
        """Crea un nuevo cliente (con Mutex)"""
        with self.account_creation_lock:
            customer = self.bank.add_customer(name, email)
            return {
                'customer_id': customer.customer_id,
                'name': customer.name,
                'email': customer.email
            }

    def create_account(self, customer_id: str, initial_balance: float = 0, nip: str = None) -> dict:
        """Crea una nueva cuenta (con Mutex)"""
        with self.account_creation_lock:
            account = self.bank.add_account(customer_id, initial_balance, nip)
            return {
                'account_number': account.account_number,
                'customer_id': account.customer_id,
                'balance': account.balance
            }

    def close_account(self, account_number: str) -> bool:
        """Cierra una cuenta (con Mutex)"""
        with self.account_creation_lock:
            if account_number not in self.bank.accounts:
                return False
            del self.bank.accounts[account_number]
            return True

    def request_turn(self, customer_id: str = None, card_number: str = None) -> str:
        """Solicita un turno (maneja prioridades)"""
        customer = self.bank.customers.get(customer_id) if customer_id else None
        card = self.bank.card_registry.get(card_number) if card_number else None
        
        turn = Turn(customer, card)
        self.turn_queue.put(turn)
        return turn.turn_id

    def process_transaction(self, transaction_type: str, **kwargs) -> int:
        """Inicia una transacción (con semáforo para ventanillas)"""
        with self.account_creation_lock:
            self.process_counter += 1
            process_id = self.process_counter
            
        process = {
            'id': process_id,
            'type': transaction_type,
            'kwargs': kwargs,
            'status': 'pending',
            'created_at': datetime.now()
        }
        
        self.active_processes[process_id] = process
        return process_id

    def _schedule_processes(self):
        """Planificador que asigna procesos a ventanillas"""
        while True:
            # Esperar si no hay procesos
            if not self.active_processes:
                time.sleep(0.1)
                continue
                
            # Buscar procesos pendientes
            for pid, process in list(self.active_processes.items()):
                if process['status'] == 'pending':
                    # Intentar adquirir ventanilla (semáforo)
                    if self.teller_semaphore.acquire(blocking=False):
                        try:
                            process['status'] = 'running'
                            process['started_at'] = datetime.now()
                            
                            # Ejecutar en hilo separado
                            t = threading.Thread(
                                target=self._execute_transaction,
                                args=(pid, process),
                                daemon=True
                            )
                            t.start()
                        except:
                            self.teller_semaphore.release()
                            raise

    def _execute_transaction(self, process_id: int, process: dict):
        """Ejecuta una transacción con el mecanismo de concurrencia adecuado"""
        try:
            result = None
            trans_type = process['type']
            kwargs = process['kwargs']
            
            # Bloqueo específico por tipo de transacción
            lock = self.transaction_lock if trans_type in ['deposit', 'withdrawal', 'transfer'] else self.account_creation_lock
            
            with lock:
                if trans_type == 'deposit':
                    result = self.bank.deposit(kwargs['account_number'], kwargs['amount'])
                elif trans_type == 'withdrawal':
                    result = self.bank.withdrawal(kwargs['account_number'], kwargs['amount'])
                elif trans_type == 'transfer':
                    result = self.bank.transfer(
                        kwargs['source_account'], 
                        kwargs['target_account'], 
                        kwargs['amount']
                    )
                elif trans_type == 'create_account':
                    result = self.create_account(
                        kwargs['customer_id'],
                        kwargs.get('initial_balance', 0),
                        kwargs.get('nip')
                    )
                elif trans_type == 'close_account':
                    result = self.close_account(kwargs['account_number'])
                
            process['result'] = result
            process['status'] = 'completed'
            
        except Exception as e:
            process['result'] = str(e)
            process['status'] = 'failed'
            
        finally:
            process['completed_at'] = datetime.now()
            self.teller_semaphore.release()

    def get_turn_queue(self) -> list:
        """Obtiene la cola de turnos actual"""
        items = []
        temp_queue = PriorityQueue()
        
        while not self.turn_queue.empty():
            turn = self.turn_queue.get()
            items.append({
                'turn_id': turn.turn_id,
                'customer_id': turn.customer_id,
                'priority': turn.priority,
                'created_at': turn.created_at.isoformat()
            })
            temp_queue.put(turn)
            
        # Restaurar la cola
        while not temp_queue.empty():
            self.turn_queue.put(temp_queue.get())
            
        return items

    def assign_turn_to_teller(self, teller_id: str) -> bool:
        """Asigna un turno a un cajero disponible"""
        if teller_id not in self.tellers or self.turn_queue.empty():
            return False
            
        teller = self.tellers[teller_id]
        if not teller.available:
            return False
            
        # Adquirir semáforo para ventanilla
        if not self.teller_semaphore.acquire(blocking=False):
            return False
            
        try:
            next_turn = self.turn_queue.get()
            success = teller.add_turn(next_turn)
            if not success:
                self.teller_semaphore.release()
            return success
        except:
            self.teller_semaphore.release()
            raise

    def get_system_status(self) -> dict:
        """Obtiene el estado completo del sistema"""
        return {
            'tellers': {t_id: t.get_status() for t_id, t in self.tellers.items()},
            'turn_queue': self.get_turn_queue(),
            'active_processes': {
                pid: {
                    'type': p['type'],
                    'status': p['status'],
                    'created_at': p['created_at'].isoformat()
                }
                for pid, p in self.active_processes.items()
            },
            'available_tellers': self.teller_semaphore._value,
            'customers_count': len(self.bank.customers),
            'accounts_count': len(self.bank.accounts)
        }