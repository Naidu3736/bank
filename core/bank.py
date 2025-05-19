from core.transaction import Transaction, TransactionType
from core.account import Account
from core.customer import Customer 
from core.card import CardType
from core.debit_card import DebitCard
from core.credit_card import CreditCard
from typing import Dict, List, Optional, Tuple
from server.locks import BankLocks
from event_logger import EventConsole, ProcessTracker
import os
import time
import multiprocessing
from contextlib import contextmanager

class Bank:
    def __init__(self, locks: BankLocks, event_console: EventConsole, process_tracker: ProcessTracker, shared_data=None):
        """
        Inicializa el banco con sistemas de concurrencia y datos compartidos.
        
        Args:
            locks (BankLocks): Sistema de bloqueos para concurrencia
            event_console (EventConsole): Sistema de registro de eventos
            process_tracker (ProcessTracker): Rastreador de procesos
            shared_data (dict, optional): Datos compartidos entre procesos. Defaults to None.
        """
        # Sistemas esenciales
        self.locks = locks
        self.event_console = event_console
        self.process_tracker = process_tracker
        
        # Inicialización de estructuras de datos
        self._initialize_data_structures(shared_data)
        
        # Contadores para IDs
        self._account_counter = multiprocessing.Value('i', 1000)
        self._customer_counter = multiprocessing.Value('i', 100)
        self._transaction_counter = multiprocessing.Value('i', 1)

    def _initialize_data_structures(self, shared_data):
        """Inicializa las estructuras de datos, con o sin memoria compartida"""
        if shared_data:
            # Modo multiproceso con datos compartidos
            self.accounts = shared_data.get('accounts', self._create_shared_dict())
            self.customers = shared_data.get('customers', self._create_shared_dict())
            self.card_registry = shared_data.get('cards', self._create_shared_dict())
            self.transaction_history = shared_data.get('transactions', self._create_shared_list())
        else:
            # Modo single-process
            self.accounts = {}
            self.customers = {}
            self.card_registry = {}
            self.transaction_history = []
            
        # Bloqueo para contadores
        self._counter_lock = multiprocessing.Lock()

    def _create_shared_dict(self):
        """Crea un diccionario compartido seguro para multiprocesos"""
        manager = multiprocessing.Manager()
        return manager.dict()

    def _create_shared_list(self):
        """Crea una lista compartida segura para multiprocesos"""
        manager = multiprocessing.Manager()
        return manager.list()

        
    @contextmanager
    def _track_operation(self, operation_name: str, lock_name: str = None):
        """Context manager para tracking de operaciones con Rich"""
        pid = os.getpid()
        start_time = time.time()
        
        try:
            # Registrar inicio de operación
            self.event_console.add_event(
                pid,
                "OPERATION_START",
                f"Iniciando {operation_name}",
                "info"
            )
            
            if lock_name:
                lock = getattr(self.locks, lock_name)
                self.process_tracker.update_process(
                    pid,
                    state="waiting",
                    current_operation=f"Esperando {lock_name} para {operation_name}",
                    lock_waiting=lock_name
                )
                
            yield
            
            # Registrar éxito
            duration = time.time() - start_time
            self.event_console.add_event(
                pid,
                operation_name.upper(),
                f"Operación completada en {duration:.2f}s",
                "success"
            )
            
        except Exception as e:
            # Registrar error
            self.event_console.add_event(
                pid,
                "OPERATION_ERROR",
                f"Error en {operation_name}: {str(e)}",
                "error"
            )
            raise
            
        finally:
            self.process_tracker.update_process(
                pid,
                state="ready",
                current_operation="Esperando siguiente operación",
                lock_acquired=None,
                lock_waiting=None
            )

    # ---- Relación Cliente-Cuenta ----
    def link_account_to_customer(self, account_number: str, customer_id: str) -> bool:
        pid = os.getpid()
        try:
            # Registrar inicio de operación
            self.event_console.add_event(
                pid,
                "LINK_ACCOUNT_START",
                f"Intentando vincular cuenta {account_number} a cliente {customer_id}",
                "info"
            )
            
            # 1. Esperando accounts_lock
            self.process_tracker.update_process(
                pid,
                state="waiting",
                current_operation="Esperando accounts_lock para verificar cuenta",
                lock_waiting="accounts_lock"
            )
            self.process_tracker.update_lock("accounts_lock", state="waiting", owner_pid=pid)
            
            with self.locks.accounts_lock:
                # 2. Adquirido accounts_lock
                self.process_tracker.update_lock("accounts_lock", state="acquired", owner_pid=pid)
                self.process_tracker.update_process(
                    pid,
                    state="working",
                    current_operation="Verificando cuenta (accounts_lock adquirido)",
                    lock_acquired="accounts_lock"
                )
                
                account = self.accounts.get(account_number)
                if not account or account.customer_id != customer_id:
                    self.event_console.add_event(
                        pid,
                        "LINK_ACCOUNT_FAILED",
                        f"Cuenta {account_number} no existe o no pertenece al cliente",
                        "error"
                    )
                    return False

            # 3. Esperando customers_lock
            self.process_tracker.update_process(
                pid,
                state="waiting",
                current_operation="Esperando customers_lock para verificar cliente",
                lock_waiting="customers_lock"
            )
            self.process_tracker.update_lock("customers_lock", state="waiting", owner_pid=pid)
            
            with self.locks.customers_lock:
                # 4. Adquirido customers_lock
                self.process_tracker.update_lock("customers_lock", state="acquired", owner_pid=pid)
                self.process_tracker.update_process(
                    pid,
                    state="working",
                    current_operation="Verificando cliente (customers_lock adquirido)",
                    lock_acquired="customers_lock"
                )
                
                customer = self.customers.get(customer_id)
                if not customer:
                    self.event_console.add_event(
                        pid,
                        "LINK_ACCOUNT_FAILED",
                        f"Cliente {customer_id} no encontrado",
                        "error"
                    )
                    return False

                try:
                    customer.link_account(account)
                    self.event_console.add_event(
                        pid,
                        "LINK_ACCOUNT_SUCCESS",
                        f"Cuenta {account_number} vinculada exitosamente a cliente {customer_id}",
                        "success"
                    )
                    return True
                except ValueError as e:
                    self.event_console.add_event(
                        pid,
                        "LINK_ACCOUNT_ERROR",
                        f"Error al vincular: {str(e)}",
                        "error"
                    )
                    return False
                    
        finally:
            # Liberar todos los locks y actualizar estado
            self.process_tracker.update_lock("accounts_lock", state="free", owner_pid=-1)
            self.process_tracker.update_lock("customers_lock", state="free", owner_pid=-1)
            self.process_tracker.update_process(
                pid,
                state="ready",
                current_operation="Operación completada",
                lock_acquired=None,
                lock_waiting=None
            )

    def transfer_between_own_accounts(self, customer_id: str, 
                                    source_acc: str, target_acc: str, 
                                    amount: float) -> bool:
        pid = os.getpid()
        try:
            self.event_console.add_event(
                pid,
                "INTERNAL_TRANSFER_START",
                f"Iniciando transferencia entre cuentas propias (Cliente: {customer_id})",
                "info"
            )
            
            # Verificación de propiedad sin lock (solo lectura)
            self.process_tracker.update_process(
                pid,
                state="working",
                current_operation="Verificando propiedad de cuentas"
            )
            
            owned_accounts = {acc.account_number for acc in self.get_customer_accounts(customer_id)}
            if source_acc not in owned_accounts or target_acc not in owned_accounts:
                self.event_console.add_event(
                    pid,
                    "INTERNAL_TRANSFER_FAILED",
                    "Una o ambas cuentas no pertenecen al cliente",
                    "error"
                )
                return False

            # 1. Esperando accounts_lock para transferencia
            self.process_tracker.update_process(
                pid,
                state="waiting",
                current_operation="Esperando accounts_lock para transferencia",
                lock_waiting="accounts_lock"
            )
            self.process_tracker.update_lock("accounts_lock", state="waiting", owner_pid=pid)
            
            # Realizar transferencia (este método ya maneja sus propios locks)
            result = self.transfer(source_acc, target_acc, amount)
            
            if result:
                self.event_console.add_event(
                    pid,
                    "INTERNAL_TRANSFER_SUCCESS",
                    "Transferencia entre cuentas propias completada",
                    "success"
                )
            else:
                self.event_console.add_event(
                    pid,
                    "INTERNAL_TRANSFER_FAILED",
                    "Error en la transferencia entre cuentas",
                    "error"
                )
                
            return result
            
        finally:
            # Asegurarse de liberar locks (aunque transfer ya lo hace)
            self.process_tracker.update_lock("accounts_lock", state="free", owner_pid=-1)
            self.process_tracker.update_process(
                pid,
                state="ready",
                current_operation="Transferencia procesada",
                lock_acquired=None,
                lock_waiting=None
            )

    # ---- Métodos de Clientes ----
    def add_customer(self, name: str, email: str) -> Customer:
        pid = os.getpid()
        try:
            # Registrar inicio de operación
            self.event_console.add_event(
                pid,
                "ADD_CUSTOMER_START",
                f"Intentando agregar nuevo cliente: {name} ({email})",
                "info"
            )
            
            # 1. Estado de espera para customers_lock
            self.process_tracker.update_process(
                pid,
                state="waiting",
                current_operation="Esperando customers_lock para validar email",
                lock_waiting="customers_lock"
            )
            self.process_tracker.update_lock("customers_lock", state="waiting", owner_pid=pid)
            
            with self.locks.customers_lock:
                # 2. Lock adquirido
                self.process_tracker.update_lock("customers_lock", state="acquired", owner_pid=pid)
                self.process_tracker.update_process(
                    pid,
                    state="working",
                    current_operation="Validando email único (customers_lock adquirido)",
                    lock_acquired="customers_lock"
                )
                
                # Verificar email único
                if any(c.email == email for c in self.customers.values()):
                    self.event_console.add_event(
                        pid,
                        "ADD_CUSTOMER_FAILED",
                        f"Email {email} ya está registrado",
                        "error"
                    )
                    raise ValueError("Email ya registrado")
                
                # Crear nuevo cliente
                customer = Customer(name, email)
                self.customers[customer.customer_id] = customer
                
                self.event_console.add_event(
                    pid,
                    "ADD_CUSTOMER_SUCCESS",
                    f"Nuevo cliente creado: {name} (ID: {customer.customer_id})",
                    "success"
                )
                
                return customer
                
        except Exception as e:
            self.event_console.add_event(
                pid,
                "ADD_CUSTOMER_ERROR",
                f"Error al crear cliente: {str(e)}",
                "error"
            )
            raise
            
        finally:
            # Liberar lock y actualizar estado
            self.process_tracker.update_lock("customers_lock", state="free", owner_pid=-1)
            self.process_tracker.update_process(
                pid,
                state="ready",
                current_operation="Operación completada",
                lock_acquired=None,
                lock_waiting=None
            )

    def delete_customer(self, customer_id: str) -> bool:
        pid = os.getpid()
        try:
            self.event_console.add_event(
                pid,
                "DELETE_CUSTOMER_START",
                f"Intentando eliminar cliente: {customer_id}",
                "info"
            )
            
            # 1. Estado de espera para customers_lock
            self.process_tracker.update_process(
                pid,
                state="waiting",
                current_operation="Esperando customers_lock para eliminar cliente",
                lock_waiting="customers_lock"
            )
            self.process_tracker.update_lock("customers_lock", state="waiting", owner_pid=pid)
            
            with self.locks.customers_lock:
                # 2. Lock adquirido
                self.process_tracker.update_lock("customers_lock", state="acquired", owner_pid=pid)
                self.process_tracker.update_process(
                    pid,
                    state="working",
                    current_operation="Eliminando cliente (customers_lock adquirido)",
                    lock_acquired="customers_lock"
                )
                
                if customer_id in self.customers:
                    # Registrar antes de eliminar
                    customer_name = self.customers[customer_id].name
                    del self.customers[customer_id]
                    
                    self.event_console.add_event(
                        pid,
                        "DELETE_CUSTOMER_SUCCESS",
                        f"Cliente eliminado: {customer_name} (ID: {customer_id})",
                        "warning"  # Warning porque es una operación sensible
                    )
                    return True
                    
                self.event_console.add_event(
                    pid,
                    "DELETE_CUSTOMER_FAILED",
                    f"Cliente {customer_id} no encontrado",
                    "error"
                )
                return False
                
        finally:
            # Liberar lock y actualizar estado
            self.process_tracker.update_lock("customers_lock", state="free", owner_pid=-1)
            self.process_tracker.update_process(
                pid,
                state="ready",
                current_operation="Operación completada",
                lock_acquired=None,
                lock_waiting=None
            )

    # ---- Métodos de Cuentas ----
    def add_account(self, customer_id: str, initial_balance: float = 0, nip: str = None) -> Account:
        pid = os.getpid()
        try:
            # Registrar inicio de operación
            self.event_console.add_event(
                pid,
                "ADD_ACCOUNT_START",
                f"Creando nueva cuenta para cliente {customer_id}",
                "info"
            )
            
            # 1. Esperando customers_lock para verificar cliente
            self.process_tracker.update_process(
                pid,
                state="waiting",
                current_operation="Esperando customers_lock para verificar cliente",
                lock_waiting="customers_lock"
            )
            self.process_tracker.update_lock("customers_lock", state="waiting", owner_pid=pid)
            
            with self.locks.customers_lock:
                # 2. customers_lock adquirido
                self.process_tracker.update_lock("customers_lock", state="acquired", owner_pid=pid)
                self.process_tracker.update_process(
                    pid,
                    state="working",
                    current_operation="Verificando cliente (customers_lock adquirido)",
                    lock_acquired="customers_lock"
                )
                
                if customer_id not in self.customers:
                    self.event_console.add_event(
                        pid,
                        "ADD_ACCOUNT_FAILED",
                        f"Cliente {customer_id} no encontrado",
                        "error"
                    )
                    raise ValueError("Cliente no encontrado")

            # 3. Esperando accounts_lock para crear cuenta
            self.process_tracker.update_process(
                pid,
                state="waiting",
                current_operation="Esperando accounts_lock para crear cuenta",
                lock_waiting="accounts_lock"
            )
            self.process_tracker.update_lock("accounts_lock", state="waiting", owner_pid=pid)
            
            with self.locks.accounts_lock:
                # 4. accounts_lock adquirido
                self.process_tracker.update_lock("accounts_lock", state="acquired", owner_pid=pid)
                self.process_tracker.update_process(
                    pid,
                    state="working",
                    current_operation="Registrando cuenta (accounts_lock adquirido)",
                    lock_acquired="accounts_lock"
                )
                
                account = Account(customer_id, initial_balance, nip)
                self.accounts[account.account_number] = account
                
                # 5. Necesitamos customers_lock nuevamente para link_account
                self.process_tracker.update_process(
                    pid,
                    state="waiting",
                    current_operation="Esperando customers_lock para vincular cuenta",
                    lock_waiting="customers_lock"
                )
                self.process_tracker.update_lock("customers_lock", state="waiting", owner_pid=pid)
                
                with self.locks.customers_lock:
                    # 6. customers_lock adquirido nuevamente
                    self.process_tracker.update_lock("customers_lock", state="acquired", owner_pid=pid)
                    self.process_tracker.update_process(
                        pid,
                        state="working",
                        current_operation="Vinculando cuenta a cliente (customers_lock adquirido)",
                        lock_acquired="customers_lock"
                    )
                    
                    self.customers[customer_id].link_account(account)
                    
                    self.event_console.add_event(
                        pid,
                        "ADD_ACCOUNT_SUCCESS",
                        f"Nueva cuenta creada: {account.account_number} con saldo inicial ${initial_balance:.2f}",
                        "success"
                    )
                    
                    return account
                    
        except Exception as e:
            self.event_console.add_event(
                pid,
                "ADD_ACCOUNT_ERROR",
                f"Error al crear cuenta: {str(e)}",
                "error"
            )
            raise
            
        finally:
            # Liberar todos los locks y actualizar estado
            self.process_tracker.update_lock("customers_lock", state="free", owner_pid=-1)
            self.process_tracker.update_lock("accounts_lock", state="free", owner_pid=-1)
            self.process_tracker.update_process(
                pid,
                state="ready",
                current_operation="Operación completada",
                lock_acquired=None,
                lock_waiting=None
            )

    def close_account(self, account_number: str) -> bool:
        pid = os.getpid()
        try:
            self.event_console.add_event(
                pid,
                "CLOSE_ACCOUNT_START",
                f"Intentando cerrar cuenta {account_number}",
                "warning"  # Warning porque es operación sensible
            )
            
            # 1. Esperando accounts_lock
            self.process_tracker.update_process(
                pid,
                state="waiting",
                current_operation="Esperando accounts_lock para cerrar cuenta",
                lock_waiting="accounts_lock"
            )
            self.process_tracker.update_lock("accounts_lock", state="waiting", owner_pid=pid)
            
            with self.locks.accounts_lock:
                # 2. accounts_lock adquirido
                self.process_tracker.update_lock("accounts_lock", state="acquired", owner_pid=pid)
                self.process_tracker.update_process(
                    pid,
                    state="working",
                    current_operation="Cerrando cuenta (accounts_lock adquirido)",
                    lock_acquired="accounts_lock"
                )
                
                if account_number in self.accounts:
                    # Obtener información antes de eliminar
                    customer_id = self.accounts[account_number].customer_id
                    balance = self.accounts[account_number].balance
                    
                    del self.accounts[account_number]
                    
                    self.event_console.add_event(
                        pid,
                        "CLOSE_ACCOUNT_SUCCESS",
                        f"Cuenta {account_number} cerrada (Cliente: {customer_id}, Saldo final: ${balance:.2f})",
                        "warning"
                    )
                    return True
                    
                self.event_console.add_event(
                    pid,
                    "CLOSE_ACCOUNT_FAILED",
                    f"Cuenta {account_number} no encontrada",
                    "error"
                )
                return False
                
        finally:
            # Liberar lock y actualizar estado
            self.process_tracker.update_lock("accounts_lock", state="free", owner_pid=-1)
            self.process_tracker.update_process(
                pid,
                state="ready",
                current_operation="Operación completada",
                lock_acquired=None,
                lock_waiting=None
            )

    # ---- Métodos de Tarjetas ----
    def issue_debit_card(self, account_number: str, card_type: CardType) -> DebitCard:
        pid = os.getpid()
        try:
            # Registrar inicio de operación
            self.event_console.add_event(
                pid,
                "ISSUE_DEBIT_CARD_START",
                f"Emisión de tarjeta débito para cuenta {account_number}",
                "info"
            )
            
            # 1. Esperando accounts_lock para verificar cuenta
            self.process_tracker.update_process(
                pid,
                state="waiting",
                current_operation="Esperando accounts_lock para verificar cuenta",
                lock_waiting="accounts_lock"
            )
            self.process_tracker.update_lock("accounts_lock", state="waiting", owner_pid=pid)
            
            with self.locks.accounts_lock:
                # 2. accounts_lock adquirido
                self.process_tracker.update_lock("accounts_lock", state="acquired", owner_pid=pid)
                self.process_tracker.update_process(
                    pid,
                    state="working",
                    current_operation="Verificando cuenta (accounts_lock adquirido)",
                    lock_acquired="accounts_lock"
                )
                
                account = self.accounts.get(account_number)
                if not account:
                    self.event_console.add_event(
                        pid,
                        "ISSUE_DEBIT_CARD_FAILED",
                        f"Cuenta {account_number} no existe",
                        "error"
                    )
                    raise ValueError("Cuenta no existe")

            # 3. Esperando cards_lock para emitir tarjeta
            self.process_tracker.update_process(
                pid,
                state="waiting",
                current_operation="Esperando cards_lock para emitir tarjeta",
                lock_waiting="cards_lock"
            )
            self.process_tracker.update_lock("cards_lock", state="waiting", owner_pid=pid)
            
            with self.locks.cards_lock:
                # 4. cards_lock adquirido
                self.process_tracker.update_lock("cards_lock", state="acquired", owner_pid=pid)
                self.process_tracker.update_process(
                    pid,
                    state="working",
                    current_operation="Registrando tarjeta (cards_lock adquirido)",
                    lock_acquired="cards_lock"
                )
                
                card = account.add_debit_card(card_type)
                self.card_registry[card.card_number] = card
                
                self.event_console.add_event(
                    pid,
                    "ISSUE_DEBIT_CARD_SUCCESS",
                    f"Tarjeta débito emitida: {card.card_number} (Tipo: {card_type.name})",
                    "success"
                )
                
                return card
                
        except Exception as e:
            self.event_console.add_event(
                pid,
                "ISSUE_DEBIT_CARD_ERROR",
                f"Error al emitir tarjeta: {str(e)}",
                "error"
            )
            raise
            
        finally:
            # Liberar todos los locks
            self.process_tracker.update_lock("accounts_lock", state="free", owner_pid=-1)
            self.process_tracker.update_lock("cards_lock", state="free", owner_pid=-1)
            self.process_tracker.update_process(
                pid,
                state="ready",
                current_operation="Operación completada",
                lock_acquired=None,
                lock_waiting=None
            )

    def block_card(self, card_number: str) -> bool:
        pid = os.getpid()
        try:
            self.event_console.add_event(
                pid,
                "BLOCK_CARD_START",
                f"Intentando bloquear tarjeta {card_number}",
                "warning"
            )
            
            # 1. Esperando cards_lock
            self.process_tracker.update_process(
                pid,
                state="waiting",
                current_operation="Esperando cards_lock para bloquear tarjeta",
                lock_waiting="cards_lock"
            )
            self.process_tracker.update_lock("cards_lock", state="waiting", owner_pid=pid)
            
            with self.locks.cards_lock:
                # 2. cards_lock adquirido
                self.process_tracker.update_lock("cards_lock", state="acquired", owner_pid=pid)
                self.process_tracker.update_process(
                    pid,
                    state="working",
                    current_operation="Procesando bloqueo (cards_lock adquirido)",
                    lock_acquired="cards_lock"
                )
                
                card = self.card_registry.get(card_number)
                if card:
                    card.block_card()
                    
                    self.event_console.add_event(
                        pid,
                        "BLOCK_CARD_SUCCESS",
                        f"Tarjeta {card_number} bloqueada exitosamente",
                        "warning"
                    )
                    return True
                    
            self.event_console.add_event(
                pid,
                "BLOCK_CARD_FAILED",
                f"Tarjeta {card_number} no encontrada",
                "error"
            )
            return False
            
        finally:
            # Liberar lock
            self.process_tracker.update_lock("cards_lock", state="free", owner_pid=-1)
            self.process_tracker.update_process(
                pid,
                state="ready",
                current_operation="Operación completada",
                lock_acquired=None,
                lock_waiting=None
            )

    def issue_credit_card(self, customer_id: str, card_type: CardType) -> CreditCard:
        pid = os.getpid()
        try:
            self.event_console.add_event(
                pid,
                "ISSUE_CREDIT_CARD_START",
                f"Emisión de tarjeta crédito para cliente {customer_id}",
                "info"
            )
            
            # 1. Esperando customers_lock
            self.process_tracker.update_process(
                pid,
                state="waiting",
                current_operation="Esperando customers_lock para verificar cliente",
                lock_waiting="customers_lock"
            )
            self.process_tracker.update_lock("customers_lock", state="waiting", owner_pid=pid)
            
            with self.locks.customers_lock:
                # 2. customers_lock adquirido
                self.process_tracker.update_lock("customers_lock", state="acquired", owner_pid=pid)
                self.process_tracker.update_process(
                    pid,
                    state="working",
                    current_operation="Verificando cliente (customers_lock adquirido)",
                    lock_acquired="customers_lock"
                )
                
                if customer_id not in self.customers:
                    self.event_console.add_event(
                        pid,
                        "ISSUE_CREDIT_CARD_FAILED",
                        f"Cliente {customer_id} no existe",
                        "error"
                    )
                    raise ValueError("Cliente no existe")
                customer = self.customers[customer_id]

            # 3. Esperando cards_lock
            self.process_tracker.update_process(
                pid,
                state="waiting",
                current_operation="Esperando cards_lock para emitir tarjeta",
                lock_waiting="cards_lock"
            )
            self.process_tracker.update_lock("cards_lock", state="waiting", owner_pid=pid)
            
            with self.locks.cards_lock:
                # 4. cards_lock adquirido
                self.process_tracker.update_lock("cards_lock", state="acquired", owner_pid=pid)
                self.process_tracker.update_process(
                    pid,
                    state="working",
                    current_operation="Registrando tarjeta (cards_lock adquirido)",
                    lock_acquired="cards_lock"
                )
                
                card = customer.add_credit_card(card_type)
                self.card_registry[card.card_number] = card
                
                self.event_console.add_event(
                    pid,
                    "ISSUE_CREDIT_CARD_SUCCESS",
                    f"Tarjeta crédito emitida: {card.card_number} (Límite: ${card.credit_limit:.2f})",
                    "success"
                )
                
                return card
                
        except Exception as e:
            self.event_console.add_event(
                pid,
                "ISSUE_CREDIT_CARD_ERROR",
                f"Error al emitir tarjeta: {str(e)}",
                "error"
            )
            raise
            
        finally:
            # Liberar todos los locks
            self.process_tracker.update_lock("customers_lock", state="free", owner_pid=-1)
            self.process_tracker.update_lock("cards_lock", state="free", owner_pid=-1)
            self.process_tracker.update_process(
                pid,
                state="ready",
                current_operation="Operación completada",
                lock_acquired=None,
                lock_waiting=None
            )

    def pay_credit_card(self, card_number: str, amount: float, 
                    payment_source: Optional[str] = None, 
                    is_cash: bool = False) -> bool:
        pid = os.getpid()
        try:
            self.event_console.add_event(
                pid,
                "CREDIT_PAYMENT_START",
                f"Procesando pago de ${amount:.2f} a tarjeta {card_number}",
                "info"
            )
            
            # 1. Esperando cards_lock para verificar tarjeta
            self.process_tracker.update_process(
                pid,
                state="waiting",
                current_operation="Esperando cards_lock para verificar tarjeta",
                lock_waiting="cards_lock"
            )
            self.process_tracker.update_lock("cards_lock", state="waiting", owner_pid=pid)
            
            with self.locks.cards_lock:
                # 2. cards_lock adquirido
                self.process_tracker.update_lock("cards_lock", state="acquired", owner_pid=pid)
                self.process_tracker.update_process(
                    pid,
                    state="working",
                    current_operation="Validando tarjeta (cards_lock adquirido)",
                    lock_acquired="cards_lock"
                )
                
                card = self.card_registry.get(card_number)
                if not isinstance(card, CreditCard):
                    self.event_console.add_event(
                        pid,
                        "CREDIT_PAYMENT_FAILED",
                        f"Tarjeta {card_number} no es de crédito o no existe",
                        "error"
                    )
                    return False

            if not is_cash:
                # 3. Esperando accounts_lock para pago desde cuenta
                self.process_tracker.update_process(
                    pid,
                    state="waiting",
                    current_operation="Esperando accounts_lock para debitar cuenta",
                    lock_waiting="accounts_lock"
                )
                self.process_tracker.update_lock("accounts_lock", state="waiting", owner_pid=pid)
                
                with self.locks.accounts_lock:
                    # 4. accounts_lock adquirido
                    self.process_tracker.update_lock("accounts_lock", state="acquired", owner_pid=pid)
                    self.process_tracker.update_process(
                        pid,
                        state="working",
                        current_operation="Procesando pago (accounts_lock adquirido)",
                        lock_acquired="accounts_lock"
                    )
                    
                    account = self.accounts.get(payment_source)
                    if not account or account.balance < amount:
                        self.event_console.add_event(
                            pid,
                            "CREDIT_PAYMENT_FAILED",
                            "Cuenta no existe o fondos insuficientes",
                            "error"
                        )
                        return False
                    
                    try:
                        account.balance -= amount
                        account_transaction = Transaction(
                            account_id=payment_source,
                            amount=amount,
                            transaction_type=TransactionType.PAYMENT,
                            card_number=card_number
                        )
                        account.add_transaction(account_transaction)
                    except ValueError:
                        self.event_console.add_event(
                            pid,
                            "CREDIT_PAYMENT_ERROR",
                            "Error al registrar transacción en cuenta",
                            "error"
                        )
                        return False
            else:
                self.event_console.add_event(
                    pid,
                    "CREDIT_CASH_PAYMENT",
                    f"Pago en efectivo registrado: ${amount:.2f}",
                    "info"
                )

            # 5. Necesitamos cards_lock nuevamente para aplicar pago
            self.process_tracker.update_process(
                pid,
                state="waiting",
                current_operation="Esperando cards_lock para aplicar pago",
                lock_waiting="cards_lock"
            )
            self.process_tracker.update_lock("cards_lock", state="waiting", owner_pid=pid)
            
            with self.locks.cards_lock:
                # 6. cards_lock adquirido nuevamente
                self.process_tracker.update_lock("cards_lock", state="acquired", owner_pid=pid)
                self.process_tracker.update_process(
                    pid,
                    state="working",
                    current_operation="Aplicando pago (cards_lock adquirido)",
                    lock_acquired="cards_lock"
                )
                
                try:
                    card.make_payment(amount)
                    
                    payment_transaction = Transaction(
                        account_id=card.customer_id if is_cash else payment_source,
                        amount=amount,
                        transaction_type=TransactionType.PAYMENT,
                        card_number=card_number,
                        is_cash=is_cash
                    )
                    self.transaction_history.append(payment_transaction)
                    
                    self.event_console.add_event(
                        pid,
                        "CREDIT_PAYMENT_SUCCESS",
                        f"Pago aplicado a tarjeta {card_number}. Nuevo saldo: ${card.outstanding_balance:.2f}",
                        "success"
                    )
                    
                    return True
                    
                except ValueError as e:
                    self.event_console.add_event(
                        pid,
                        "CREDIT_PAYMENT_ERROR",
                        f"Error al aplicar pago: {str(e)}",
                        "error"
                    )
                    return False
                    
        finally:
            # Liberar todos los locks
            self.process_tracker.update_lock("cards_lock", state="free", owner_pid=-1)
            self.process_tracker.update_lock("accounts_lock", state="free", owner_pid=-1)
            self.process_tracker.update_process(
                pid,
                state="ready",
                current_operation="Operación completada",
                lock_acquired=None,
                lock_waiting=None
            )

    def get_credit_card_info(self, card_number: str) -> Optional[Dict]:
        pid = os.getpid()
        try:
            self.event_console.add_event(
                pid,
                "CREDIT_CARD_QUERY",
                f"Solicitando información de tarjeta {card_number}",
                "info"
            )
            
            # 1. Esperando cards_lock
            self.process_tracker.update_process(
                pid,
                state="waiting",
                current_operation="Esperando cards_lock para consultar tarjeta",
                lock_waiting="cards_lock"
            )
            self.process_tracker.update_lock("cards_lock", state="waiting", owner_pid=pid)
            
            with self.locks.cards_lock:
                # 2. cards_lock adquirido
                self.process_tracker.update_lock("cards_lock", state="acquired", owner_pid=pid)
                self.process_tracker.update_process(
                    pid,
                    state="working",
                    current_operation="Consultando tarjeta (cards_lock adquirido)",
                    lock_acquired="cards_lock"
                )
                
                card = self.card_registry.get(card_number)
                if not isinstance(card, CreditCard):
                    self.event_console.add_event(
                        pid,
                        "CREDIT_CARD_NOT_FOUND",
                        f"Tarjeta {card_number} no existe o no es de crédito",
                        "warning"
                    )
                    return None

                self.event_console.add_event(
                    pid,
                    "CREDIT_CARD_INFO",
                    f"Información obtenida para tarjeta {card_number}",
                    "success"
                )
                
                return {
                    "card_type": card.type.name,
                    "customer_id": card.customer_id,
                    "outstanding_balance": card.outstanding_balance,
                    "available_credit": card.available_credit,
                    "interest_rate": card.benefits["interest_rate"],
                    "status": "active" if card.is_valid() else "blocked/expired"
                }
                
        finally:
            # Liberar lock
            self.process_tracker.update_lock("cards_lock", state="free", owner_pid=-1)
            self.process_tracker.update_process(
                pid,
                state="ready",
                current_operation="Consulta completada",
                lock_acquired=None,
                lock_waiting=None
            )

    def apply_monthly_interest(self):
        pid = os.getpid()
        try:
            self.event_console.add_event(
                pid,
                "MONTHLY_INTEREST_START",
                "Aplicando intereses mensuales a tarjetas de crédito",
                "info"
            )
            
            # 1. Esperando cards_lock
            self.process_tracker.update_process(
                pid,
                state="waiting",
                current_operation="Esperando cards_lock para aplicar intereses",
                lock_waiting="cards_lock"
            )
            self.process_tracker.update_lock("cards_lock", state="waiting", owner_pid=pid)
            
            with self.locks.cards_lock:
                # 2. cards_lock adquirido
                self.process_tracker.update_lock("cards_lock", state="acquired", owner_pid=pid)
                self.process_tracker.update_process(
                    pid,
                    state="working",
                    current_operation="Calculando intereses (cards_lock adquirido)",
                    lock_acquired="cards_lock"
                )
                
                cards_processed = 0
                total_interest = 0.0
                
                for card in self.card_registry.values():
                    if isinstance(card, CreditCard) and card.outstanding_balance > 0:
                        interest = card.calculate_interest()
                        card.apply_interest()
                        total_interest += interest
                        cards_processed += 1
                        
                        interest_transaction = Transaction(
                            account_id=card.customer_id,
                            amount=interest,
                            transaction_type=TransactionType.PAYMENT,
                            description="Interés mensual"
                        )
                        self.transaction_history.append(interest_transaction)

                self.event_console.add_event(
                    pid,
                    "MONTHLY_INTEREST_COMPLETE",
                    f"Intereses aplicados a {cards_processed} tarjetas. Total: ${total_interest:.2f}",
                    "success"
                )
                
        except Exception as e:
            self.event_console.add_event(
                pid,
                "MONTHLY_INTEREST_ERROR",
                f"Error al aplicar intereses: {str(e)}",
                "error"
            )
            raise
            
        finally:
            # Liberar lock
            self.process_tracker.update_lock("cards_lock", state="free", owner_pid=-1)
            self.process_tracker.update_process(
                pid,
                state="ready",
                current_operation="Proceso de intereses completado",
                lock_acquired=None,
                lock_waiting=None
            )

    def deactivate_card(self, card_number: str) -> bool:
        pid = os.getpid()
        try:
            self.event_console.add_event(
                pid,
                "DEACTIVATE_CARD_START",
                f"Iniciando desactivación de tarjeta {card_number}",
                "warning"
            )
            
            # 1. Esperando cards_lock para verificar tarjeta
            self.process_tracker.update_process(
                pid,
                state="waiting",
                current_operation="Esperando cards_lock para desactivar tarjeta",
                lock_waiting="cards_lock"
            )
            self.process_tracker.update_lock("cards_lock", state="waiting", owner_pid=pid)
            
            with self.locks.cards_lock:
                # 2. cards_lock adquirido
                self.process_tracker.update_lock("cards_lock", state="acquired", owner_pid=pid)
                self.process_tracker.update_process(
                    pid,
                    state="working",
                    current_operation="Validando tarjeta (cards_lock adquirido)",
                    lock_acquired="cards_lock"
                )
                
                card = self.card_registry.get(card_number)
                if not card:
                    self.event_console.add_event(
                        pid,
                        "DEACTIVATE_CARD_FAILED",
                        f"Tarjeta {card_number} no encontrada",
                        "error"
                    )
                    return False
                
                if isinstance(card, CreditCard) and card.outstanding_balance > 0:
                    error_msg = f"Tarjeta {card_number} tiene saldo pendiente: ${card.outstanding_balance:.2f}"
                    self.event_console.add_event(
                        pid,
                        "DEACTIVATE_CARD_FAILED",
                        error_msg,
                        "error"
                    )
                    raise ValueError(error_msg)
                
                # Registrar datos antes de eliminar
                card_type = "crédito" if isinstance(card, CreditCard) else "débito"
                owner_id = card.customer_id if isinstance(card, CreditCard) else card.account_id
                
                del self.card_registry[card_number]
                
                # Determinar qué lock necesitamos para actualizar referencias
                if isinstance(card, CreditCard):
                    # 3. Esperando customers_lock para tarjetas de crédito
                    self.process_tracker.update_process(
                        pid,
                        state="waiting",
                        current_operation="Esperando customers_lock para actualizar referencias",
                        lock_waiting="customers_lock"
                    )
                    self.process_tracker.update_lock("customers_lock", state="waiting", owner_pid=pid)
                    
                    with self.locks.customers_lock:
                        # 4. customers_lock adquirido
                        self.process_tracker.update_lock("customers_lock", state="acquired", owner_pid=pid)
                        self.process_tracker.update_process(
                            pid,
                            state="working",
                            current_operation="Actualizando cliente (customers_lock adquirido)",
                            lock_acquired="customers_lock"
                        )
                        
                        owner = self.customers.get(card.customer_id)
                        if owner:
                            owner.credit_cards = [c for c in owner.credit_cards if c.card_number != card_number]
                else:
                    # 3. Esperando accounts_lock para tarjetas de débito
                    self.process_tracker.update_process(
                        pid,
                        state="waiting",
                        current_operation="Esperando accounts_lock para actualizar referencias",
                        lock_waiting="accounts_lock"
                    )
                    self.process_tracker.update_lock("accounts_lock", state="waiting", owner_pid=pid)
                    
                    with self.locks.accounts_lock:
                        # 4. accounts_lock adquirido
                        self.process_tracker.update_lock("accounts_lock", state="acquired", owner_pid=pid)
                        self.process_tracker.update_process(
                            pid,
                            state="working",
                            current_operation="Actualizando cuenta (accounts_lock adquirido)",
                            lock_acquired="accounts_lock"
                        )
                        
                        owner = self.accounts.get(card.account_id)
                        if owner:
                            owner.debit_cards = [dc for dc in owner.debit_cards if dc.card_number != card_number]

                self.event_console.add_event(
                    pid,
                    "DEACTIVATE_CARD_SUCCESS",
                    f"Tarjeta {card_type} {card_number} desactivada (Propietario: {owner_id})",
                    "warning"
                )
                return True
                
        except Exception as e:
            self.event_console.add_event(
                pid,
                "DEACTIVATE_CARD_ERROR",
                f"Error al desactivar tarjeta: {str(e)}",
                "error"
            )
            raise
            
        finally:
            # Liberar todos los locks posibles
            self.process_tracker.update_lock("cards_lock", state="free", owner_pid=-1)
            self.process_tracker.update_lock("customers_lock", state="free", owner_pid=-1)
            self.process_tracker.update_lock("accounts_lock", state="free", owner_pid=-1)
            self.process_tracker.update_process(
                pid,
                state="ready",
                current_operation="Operación completada",
                lock_acquired=None,
                lock_waiting=None
            )

    def get_debit_cards(self, account_number: str) -> List[DebitCard]:
        pid = os.getpid()
        try:
            self.event_console.add_event(
                pid,
                "DEBIT_CARDS_QUERY",
                f"Consultando tarjetas débito para cuenta {account_number}",
                "info"
            )
            
            # 1. Esperando accounts_lock
            self.process_tracker.update_process(
                pid,
                state="waiting",
                current_operation="Esperando accounts_lock para consultar tarjetas",
                lock_waiting="accounts_lock"
            )
            self.process_tracker.update_lock("accounts_lock", state="waiting", owner_pid=pid)
            
            with self.locks.accounts_lock:
                # 2. accounts_lock adquirido
                self.process_tracker.update_lock("accounts_lock", state="acquired", owner_pid=pid)
                self.process_tracker.update_process(
                    pid,
                    state="working",
                    current_operation="Obteniendo tarjetas (accounts_lock adquirido)",
                    lock_acquired="accounts_lock"
                )
                
                account = self.accounts.get(account_number)
                if not account:
                    self.event_console.add_event(
                        pid,
                        "DEBIT_CARDS_NOT_FOUND",
                        f"Cuenta {account_number} no encontrada",
                        "warning"
                    )
                    return []
                    
                cards = account.debit_cards.copy()
                self.event_console.add_event(
                    pid,
                    "DEBIT_CARDS_RESULT",
                    f"Encontradas {len(cards)} tarjetas para cuenta {account_number}",
                    "success"
                )
                return cards
                
        finally:
            # Liberar lock
            self.process_tracker.update_lock("accounts_lock", state="free", owner_pid=-1)
            self.process_tracker.update_process(
                pid,
                state="ready",
                current_operation="Consulta completada",
                lock_acquired=None,
                lock_waiting=None
            )

    def get_credit_cards(self, customer_id: str) -> List[CreditCard]:
        pid = os.getpid()
        try:
            self.event_console.add_event(
                pid,
                "CREDIT_CARDS_QUERY",
                f"Consultando tarjetas crédito para cliente {customer_id}",
                "info"
            )
            
            # 1. Esperando customers_lock
            self.process_tracker.update_process(
                pid,
                state="waiting",
                current_operation="Esperando customers_lock para consultar tarjetas",
                lock_waiting="customers_lock"
            )
            self.process_tracker.update_lock("customers_lock", state="waiting", owner_pid=pid)
            
            with self.locks.customers_lock:
                # 2. customers_lock adquirido
                self.process_tracker.update_lock("customers_lock", state="acquired", owner_pid=pid)
                self.process_tracker.update_process(
                    pid,
                    state="working",
                    current_operation="Obteniendo tarjetas (customers_lock adquirido)",
                    lock_acquired="customers_lock"
                )
                
                customer = self.customers.get(customer_id)
                if not customer:
                    self.event_console.add_event(
                        pid,
                        "CREDIT_CARDS_NOT_FOUND",
                        f"Cliente {customer_id} no encontrado",
                        "warning"
                    )
                    return []
                    
                cards = customer.credit_cards.copy()
                self.event_console.add_event(
                    pid,
                    "CREDIT_CARDS_RESULT",
                    f"Encontradas {len(cards)} tarjetas para cliente {customer_id}",
                    "success"
                )
                return cards
                
        finally:
            # Liberar lock
            self.process_tracker.update_lock("customers_lock", state="free", owner_pid=-1)
            self.process_tracker.update_process(
                pid,
                state="ready",
                current_operation="Consulta completada",
                lock_acquired=None,
                lock_waiting=None
            )

    # ---- Banking Operations ----
    def transfer(self, source_id: str, target_id: str, amount: float, nip: Optional[str] = None) -> bool:
        pid = os.getpid()
        try:
            # Register operation start
            self.event_console.add_event(
                pid,
                "TRANSFER_INITIATED",
                f"Transfer initiated: ${amount:.2f} from {source_id[:4]}... to {target_id[:4]}...",
                "info"
            )
            
            # 1. Waiting for accounts_lock
            self.process_tracker.update_process(
                pid,
                state="waiting",
                current_operation="Waiting for accounts_lock to validate transfer",
                lock_waiting="accounts_lock"
            )
            self.process_tracker.update_lock("accounts_lock", state="waiting", owner_pid=pid)
            
            with self.locks.accounts_lock:
                # 2. accounts_lock acquired
                self.process_tracker.update_lock("accounts_lock", state="acquired", owner_pid=pid)
                self.process_tracker.update_process(
                    pid,
                    state="working",
                    current_operation="Processing transfer (accounts_lock acquired)",
                    lock_acquired="accounts_lock"
                )
                
                # Basic validation
                if source_id == target_id:
                    self.event_console.add_event(
                        pid,
                        "TRANSFER_FAILED",
                        "Cannot transfer to same account",
                        "error"
                    )
                    return False
                    
                source = self.accounts.get(source_id)
                target = self.accounts.get(target_id)
                
                # Validations
                if not source or not target:
                    self.event_console.add_event(
                        pid,
                        "TRANSFER_FAILED",
                        "Account(s) not found",
                        "error"
                    )
                    return False
                    
                if nip and not source.validate_nip(nip):
                    self.event_console.add_event(
                        pid,
                        "TRANSFER_FAILED",
                        "Incorrect PIN",
                        "error"
                    )
                    return False
                    
                if source.balance < amount:
                    self.event_console.add_event(
                        pid,
                        "TRANSFER_FAILED",
                        f"Insufficient funds (${source.balance:.2f} < ${amount:.2f})",
                        "error"
                    )
                    return False

                # Execute transfer
                source.balance -= amount
                target.balance += amount

                # Record transactions
                source_transaction = Transaction(
                    account_id=source_id,
                    amount=amount,
                    transaction_type=TransactionType.TRANSFER,
                    description=f"Transfer to {target_id[:4]}...",
                    source_reference=target_id
                )
                
                target_transaction = Transaction(
                    account_id=target_id,
                    amount=amount,
                    transaction_type=TransactionType.DEPOSIT,
                    description=f"Transfer from {source_id[:4]}...",
                    source_reference=source_id
                )
                
                source.add_transaction(source_transaction)
                target.add_transaction(target_transaction)
                self.transaction_history.extend([source_transaction, target_transaction])
                
                self.event_console.add_event(
                    pid,
                    "TRANSFER_COMPLETED",
                    f"Transfer successful. New balances: {source_id[:4]}...=${source.balance:.2f}, {target_id[:4]}...=${target.balance:.2f}",
                    "success"
                )
                
                return True
                
        except Exception as e:
            self.event_console.add_event(
                pid,
                "TRANSFER_ERROR",
                f"Transfer error: {str(e)}",
                "error"
            )
            return False
            
        finally:
            # Release lock and update status
            self.process_tracker.update_lock("accounts_lock", state="free", owner_pid=-1)
            self.process_tracker.update_process(
                pid,
                state="ready",
                current_operation="Waiting for operation",
                lock_acquired=None,
                lock_waiting=None
            )

    def deposit(self, account_number: str, amount: float, source_reference: str = None) -> bool:
        pid = os.getpid()
        try:
            self.event_console.add_event(
                pid,
                "DEPOSIT_INITIATED",
                f"Attempting to deposit ${amount:.2f} to {account_number}",
                "info"
            )
            
            if amount <= 0:
                self.event_console.add_event(
                    pid,
                    "DEPOSIT_FAILED",
                    f"Invalid amount: ${amount:.2f}",
                    "error"
                )
                return False

            # 1. Waiting for accounts_lock
            self.process_tracker.update_process(
                pid,
                state="waiting",
                current_operation="Waiting for accounts_lock to process deposit",
                lock_waiting="accounts_lock"
            )
            self.process_tracker.update_lock("accounts_lock", state="waiting", owner_pid=pid)
            
            with self.locks.accounts_lock:
                # 2. accounts_lock acquired
                self.process_tracker.update_lock("accounts_lock", state="acquired", owner_pid=pid)
                self.process_tracker.update_process(
                    pid,
                    state="working",
                    current_operation="Processing deposit (accounts_lock acquired)",
                    lock_acquired="accounts_lock"
                )
                
                account = self.accounts.get(account_number)
                if not account:
                    self.event_console.add_event(
                        pid,
                        "DEPOSIT_FAILED",
                        f"Account {account_number} not found",
                        "error"
                    )
                    return False

                # Make deposit
                account.balance += amount
                
                transaction_type = (
                    TransactionType.DEPOSIT if not source_reference 
                    else TransactionType.TRANSFER_RECEIVED
                )
                
                transaction = Transaction(
                    account_id=account_number,
                    amount=amount,
                    transaction_type=transaction_type,
                    source_reference=source_reference
                )
                
                account.add_transaction(transaction)
                self.transaction_history.append(transaction)
                
                self.event_console.add_event(
                    pid,
                    "DEPOSIT_COMPLETED",
                    f"Deposit successful. New balance: ${account.balance:.2f}",
                    "success"
                )
                
                return True
                
        except Exception as e:
            self.event_console.add_event(
                pid,
                "DEPOSIT_ERROR",
                f"Unexpected deposit error: {str(e)}",
                "error"
            )
            return False
            
        finally:
            # Release lock and update status
            self.process_tracker.update_lock("accounts_lock", state="free", owner_pid=-1)
            self.process_tracker.update_process(
                pid,
                state="ready",
                current_operation="Deposit processed",
                lock_acquired=None,
                lock_waiting=None
            )

    def withdraw(self, account_number: str, amount: float, nip: str) -> bool:
        pid = os.getpid()
        try:
            self.event_console.add_event(
                pid,
                "WITHDRAWAL_INITIATED",
                f"Attempting to withdraw ${amount:.2f} from {account_number}",
                "info"
            )
            
            # Basic amount validation
            if amount <= 0:
                self.event_console.add_event(
                    pid,
                    "WITHDRAWAL_FAILED",
                    f"Invalid amount: ${amount:.2f}",
                    "error"
                )
                return False

            # 1. Waiting for accounts_lock
            self.process_tracker.update_process(
                pid,
                state="waiting",
                current_operation="Waiting for accounts_lock to validate withdrawal",
                lock_waiting="accounts_lock"
            )
            self.process_tracker.update_lock("accounts_lock", state="waiting", owner_pid=pid)
            
            with self.locks.accounts_lock:
                # 2. accounts_lock acquired
                self.process_tracker.update_lock("accounts_lock", state="acquired", owner_pid=pid)
                self.process_tracker.update_process(
                    pid,
                    state="working",
                    current_operation="Processing withdrawal (accounts_lock acquired)",
                    lock_acquired="accounts_lock"
                )
                
                account = self.accounts.get(account_number)
                
                # Account validations
                if not account:
                    self.event_console.add_event(
                        pid,
                        "WITHDRAWAL_FAILED",
                        f"Account {account_number} not found",
                        "error"
                    )
                    return False
                    
                if account.is_locked:
                    self.event_console.add_event(
                        pid,
                        "ACCOUNT_LOCKED",
                        f"Account {account_number} temporarily locked",
                        "error"
                    )
                    return False
                    
                if not account.validate_nip(nip):
                    remaining_attempts = 3 - account.nip_attempts
                    self.event_console.add_event(
                        pid,
                        "WITHDRAWAL_FAILED",
                        f"Incorrect PIN. Remaining attempts: {remaining_attempts}",
                        "warning"
                    )
                    return False
                    
                if account.balance < amount:
                    self.event_console.add_event(
                        pid,
                        "WITHDRAWAL_FAILED",
                        f"Insufficient funds. Available: ${account.balance:.2f}",
                        "error"
                    )
                    return False

                # Process withdrawal
                account.balance -= amount
                transaction = Transaction(
                    account_id=account_number,
                    amount=amount,
                    transaction_type=TransactionType.WITHDRAWAL,
                    description="Cash withdrawal"
                )
                account.add_transaction(transaction)
                self.transaction_history.append(transaction)
                
                self.event_console.add_event(
                    pid,
                    "WITHDRAWAL_COMPLETED",
                    f"Withdrawal successful. New balance: ${account.balance:.2f}",
                    "success"
                )
                
                return True
                
        except Exception as e:
            self.event_console.add_event(
                pid,
                "WITHDRAWAL_ERROR",
                f"Unexpected withdrawal error: {str(e)}",
                "error"
            )
            return False
            
        finally:
            # Release lock and update status
            self.process_tracker.update_lock("accounts_lock", state="free", owner_pid=-1)
            self.process_tracker.update_process(
                pid,
                state="ready",
                current_operation="Withdrawal processed",
                lock_acquired=None,
                lock_waiting=None
            )

    def get_account_transactions(self, account_number: str, limit: int = 10) -> List[Transaction]:
        pid = os.getpid()
        try:
            self.event_console.add_event(
                pid,
                "TRANSACTION_HISTORY_REQUEST",
                f"Requesting transaction history for {account_number} (last {limit} transactions)",
                "info"
            )
            
            # 1. Waiting for accounts_lock
            self.process_tracker.update_process(
                pid,
                state="waiting",
                current_operation="Waiting for accounts_lock to get transactions",
                lock_waiting="accounts_lock"
            )
            self.process_tracker.update_lock("accounts_lock", state="waiting", owner_pid=pid)
            
            with self.locks.accounts_lock:
                # 2. accounts_lock acquired
                self.process_tracker.update_lock("accounts_lock", state="acquired", owner_pid=pid)
                self.process_tracker.update_process(
                    pid,
                    state="working",
                    current_operation="Getting transactions (accounts_lock acquired)",
                    lock_acquired="accounts_lock"
                )
                
                account = self.accounts.get(account_number)
                if not account:
                    self.event_console.add_event(
                        pid,
                        "ACCOUNT_NOT_FOUND",
                        f"Account {account_number} does not exist",
                        "warning"
                    )
                    return []
                    
                transactions = account.get_transactions(limit)
                self.event_console.add_event(
                    pid,
                    "TRANSACTION_HISTORY_RETURNED",
                    f"Found {len(transactions)} transactions",
                    "success"
                )
                return transactions
                
        finally:
            # Release lock and update status
            self.process_tracker.update_lock("accounts_lock", state="free", owner_pid=-1)
            self.process_tracker.update_process(
                pid,
                state="ready",
                current_operation="Transaction history retrieved",
                lock_acquired=None,
                lock_waiting=None
            )

    def get_account_balance(self, account_number: str) -> Optional[float]:
        pid = os.getpid()
        try:
            self.event_console.add_event(
                pid,
                "BALANCE_REQUEST",
                f"Requesting balance for {account_number}",
                "info"
            )
            
            # 1. Waiting for accounts_lock
            self.process_tracker.update_process(
                pid,
                state="waiting",
                current_operation="Waiting for accounts_lock to get balance",
                lock_waiting="accounts_lock"
            )
            self.process_tracker.update_lock("accounts_lock", state="waiting", owner_pid=pid)
            
            with self.locks.accounts_lock:
                # 2. accounts_lock acquired
                self.process_tracker.update_lock("accounts_lock", state="acquired", owner_pid=pid)
                self.process_tracker.update_process(
                    pid,
                    state="working",
                    current_operation="Getting balance (accounts_lock acquired)",
                    lock_acquired="accounts_lock"
                )
                
                account = self.accounts.get(account_number)
                if account:
                    self.event_console.add_event(
                        pid,
                        "BALANCE_RETURNED",
                        f"Balance retrieved: ${account.balance:.2f}",
                        "success"
                    )
                    return account.balance
                else:
                    self.event_console.add_event(
                        pid,
                        "ACCOUNT_NOT_FOUND",
                        f"Account {account_number} does not exist",
                        "warning"
                    )
                    return None
                    
        finally:
            # Release lock and update status
            self.process_tracker.update_lock("accounts_lock", state="free", owner_pid=-1)
            self.process_tracker.update_process(
                pid,
                state="ready",
                current_operation="Balance retrieved",
                lock_acquired=None,
                lock_waiting=None
            )

    def get_customer_by_email(self, email: str) -> Optional[Customer]:
        pid = os.getpid()
        try:
            self.event_console.add_event(
                pid,
                "CUSTOMER_SEARCH",
                f"Searching for customer by email: {email}",
                "info"
            )
            
            # 1. Waiting for customers_lock
            self.process_tracker.update_process(
                pid,
                state="waiting",
                current_operation="Waiting for customers_lock to search customer",
                lock_waiting="customers_lock"
            )
            self.process_tracker.update_lock("customers_lock", state="waiting", owner_pid=pid)
            
            with self.locks.customers_lock:
                # 2. customers_lock acquired
                self.process_tracker.update_lock("customers_lock", state="acquired", owner_pid=pid)
                self.process_tracker.update_process(
                    pid,
                    state="working",
                    current_operation="Searching records (customers_lock acquired)",
                    lock_acquired="customers_lock"
                )
                
                for customer in self.customers.values():
                    if customer.email == email:
                        self.event_console.add_event(
                            pid,
                            "CUSTOMER_FOUND",
                            f"Customer found: {customer.customer_id}",
                            "success"
                        )
                        return customer
                        
                self.event_console.add_event(
                    pid,
                    "CUSTOMER_NOT_FOUND",
                    f"No customer found with email: {email}",
                    "warning"
                )
                return None
                
        finally:
            # Release lock and update status
            self.process_tracker.update_lock("customers_lock", state="free", owner_pid=-1)
            self.process_tracker.update_process(
                pid,
                state="ready",
                current_operation="Customer search completed",
                lock_acquired=None,
                lock_waiting=None
            )

    # ---- Consultas ----
    def get_customer_accounts(self, customer_id: str) -> List[Account]:
        pid = os.getpid()
        try:
            self.event_console.add_event(
                pid,
                "CUSTOMER_ACCOUNTS_QUERY",
                f"Consultando cuentas del cliente {customer_id}",
                "info"
            )
            
            self.process_tracker.update_process(
                pid,
                state="waiting",
                current_operation="Esperando customers_lock",
                lock_waiting="customers_lock"
            )
            self.process_tracker.update_lock("customers_lock", state="waiting", owner_pid=pid)

            with self.locks.customers_lock:
                self.process_tracker.update_lock("customers_lock", state="acquired", owner_pid=pid)
                self.process_tracker.update_process(
                    pid,
                    state="working",
                    current_operation="Obteniendo cuentas (lock adquirido)",
                    lock_acquired="customers_lock",
                    lock_waiting=None
                )

                customer = self.customers.get(customer_id)
                if not customer:
                    self.event_console.add_event(
                        pid,
                        "CUSTOMER_NOT_FOUND",
                        f"Cliente {customer_id} no encontrado",
                        "warning"
                    )
                    return []

                accounts = customer.accounts
                self.event_console.add_event(
                    pid,
                    "ACCOUNTS_RETRIEVED",
                    f"Encontradas {len(accounts)} cuentas para el cliente {customer_id}",
                    "success"
                )
                return accounts

        finally:
            self.process_tracker.update_lock("customers_lock", state="free", owner_pid=-1)
            self.process_tracker.update_process(
                pid,
                state="ready",
                current_operation="Consulta completada",
                lock_acquired=None,
                lock_waiting=None
            )

    def get_card_balance(self, card_number: str) -> Optional[float]:
        pid = os.getpid()
        try:
            self.event_console.add_event(
                pid,
                "CARD_BALANCE_QUERY",
                f"Consultando saldo de tarjeta {card_number}",
                "info"
            )

            self.process_tracker.update_process(
                pid,
                state="waiting",
                current_operation="Esperando cards_lock",
                lock_waiting="cards_lock"
            )
            self.process_tracker.update_lock("cards_lock", state="waiting", owner_pid=pid)

            with self.locks.cards_lock:
                self.process_tracker.update_lock("cards_lock", state="acquired", owner_pid=pid)
                self.process_tracker.update_process(
                    pid,
                    state="working",
                    current_operation="Obteniendo saldo (lock adquirido)",
                    lock_acquired="cards_lock",
                    lock_waiting=None
                )

                card = self.card_registry.get(card_number)
                if not card:
                    self.event_console.add_event(
                        pid,
                        "CARD_NOT_FOUND",
                        f"Tarjeta {card_number} no encontrada",
                        "warning"
                    )
                    return None

                if isinstance(card, DebitCard):
                    account = self.accounts.get(card.account_id)
                    if not account:
                        self.event_console.add_event(
                            pid,
                            "ACCOUNT_NOT_FOUND",
                            f"Cuenta asociada a tarjeta {card_number} no existe",
                            "error"
                        )
                        return None

                    balance = account.balance
                    self.event_console.add_event(
                        pid,
                        "DEBIT_BALANCE_RETURNED",
                        f"Saldo de débito: ${balance:.2f}",
                        "success"
                    )
                    return balance

                elif isinstance(card, CreditCard):
                    available_credit = card.available_credit
                    self.event_console.add_event(
                        pid,
                        "CREDIT_BALANCE_RETURNED",
                        f"Crédito disponible: ${available_credit:.2f}",
                        "success"
                    )
                    return available_credit

                return None

        finally:
            self.process_tracker.update_lock("cards_lock", state="free", owner_pid=-1)
            self.process_tracker.update_process(
                pid,
                state="ready",
                current_operation="Consulta completada",
                lock_acquired=None,
                lock_waiting=None
            )

    def generate_account_statement(self, account_number: str, days: int = 30) -> Dict:
        pid = os.getpid()
        try:
            self.event_console.add_event(
                pid,
                "ACCOUNT_STATEMENT_START",
                f"Generando estado de cuenta para {account_number} (últimos {days} días)",
                "info"
            )

            self.process_tracker.update_process(
                pid,
                state="waiting",
                current_operation="Esperando accounts_lock",
                lock_waiting="accounts_lock"
            )
            self.process_tracker.update_lock("accounts_lock", state="waiting", owner_pid=pid)

            with self.locks.accounts_lock:
                self.process_tracker.update_lock("accounts_lock", state="acquired", owner_pid=pid)
                self.process_tracker.update_process(
                    pid,
                    state="working",
                    current_operation="Generando reporte (lock adquirido)",
                    lock_acquired="accounts_lock",
                    lock_waiting=None
                )

                account = self.accounts.get(account_number)
                if not account:
                    self.event_console.add_event(
                        pid,
                        "ACCOUNT_NOT_FOUND",
                        f"Cuenta {account_number} no existe",
                        "error"
                    )
                    return {}

                transactions = account.get_transactions(limit=100)
                recent_transactions = [t for t in transactions if t.is_recent(days)]

                deposits = sum(t.amount for t in recent_transactions if t.type == TransactionType.DEPOSIT)
                withdrawals = sum(t.amount for t in recent_transactions if t.type == TransactionType.WITHDRAWAL)
                transfers = sum(t.amount for t in recent_transactions if t.type == TransactionType.TRANSFER)

                statement = {
                    'account_number': account_number,
                    'current_balance': account.balance,
                    'transactions': recent_transactions,
                    'summary': {
                        'deposits': deposits,
                        'withdrawals': withdrawals,
                        'transfers': transfers
                    }
                }

                self.event_console.add_event(
                    pid,
                    "STATEMENT_GENERATED",
                    f"Estado de cuenta generado para {account_number}",
                    "success"
                )

                return statement

        except Exception as e:
            self.event_console.add_event(
                pid,
                "STATEMENT_ERROR",
                f"Error generando estado de cuenta: {str(e)}",
                "error"
            )
            return {}

        finally:
            self.process_tracker.update_lock("accounts_lock", state="free", owner_pid=-1)
            self.process_tracker.update_process(
                pid,
                state="ready",
                current_operation="Operación completada",
                lock_acquired=None,
                lock_waiting=None
            )
