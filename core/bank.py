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
    def __init__(self, locks: BankLocks, event_console: EventConsole, 
                 process_tracker: ProcessTracker, shared_data=None, manager=None):
        """
        Inicializa el banco con sistemas de concurrencia y datos compartidos.
        
        Args:
            locks (BankLocks): Sistema de bloqueos para concurrencia
            event_console (EventConsole): Sistema de registro de eventos
            process_tracker (ProcessTracker): Rastreador de procesos
            shared_data (dict, optional): Datos compartidos entre procesos. Defaults to None.
            manager (multiprocessing.Manager, optional): Manager compartido. Defaults to None.
        """
        # Sistemas esenciales
        self.locks = locks
        self.event_console = event_console
        self.process_tracker = process_tracker
        self._manager = manager  # Guardar el manager compartido
        
        # Inicialización de estructuras de datos
        self._initialize_data_structures(shared_data)
        
        # Contadores para IDs (usando Value para compartir entre procesos)
        self._account_counter = multiprocessing.Value('i', 1000)
        self._customer_counter = multiprocessing.Value('i', 100)
        self._transaction_counter = multiprocessing.Value('i', 1)
        self._counter_lock = multiprocessing.Lock()

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

    def _create_shared_dict(self):
        """Crea un diccionario compartido usando el manager existente"""
        if self._manager is None:
            raise RuntimeError("Manager no proporcionado para creación de datos compartidos")
        return self._manager.dict()

    def _create_shared_list(self):
        """Crea una lista compartida usando el manager existente"""
        if self._manager is None:
            raise RuntimeError("Manager no proporcionado para creación de datos compartidos")
        return self._manager.list()

        
    @contextmanager
    def _track_operation(self, operation_name: str, lock_names: List[str] = None):
        """Context manager mejorado para tracking de operaciones con múltiples locks"""
        pid = os.getpid()
        start_time = time.time()
        locks = []
        
        try:
            # Registrar inicio de operación
            self.event_console.add_event(
                pid,
                f"{operation_name}_START",
                f"Iniciando {operation_name.replace('_', ' ')}",
                "info"
            )
            
            if lock_names:
                # Adquirir locks en orden
                for lock_name in lock_names:
                    lock = getattr(self.locks, lock_name)
                    self.process_tracker.update_process(
                        pid,
                        state="waiting",
                        current_operation=f"Esperando {lock_name} para {operation_name}",
                        lock_waiting=lock_name
                    )
                    self.process_tracker.update_lock(lock_name, state="waiting", owner_pid=pid)
                    lock.acquire()
                    locks.append(lock)
                    self.process_tracker.update_lock(lock_name, state="acquired", owner_pid=pid)
                    self.process_tracker.update_process(
                        pid,
                        state="working",
                        current_operation=f"Operación en progreso ({lock_name} adquirido)",
                        lock_acquired=lock_name,
                        lock_waiting=None
                    )
            
            yield
            
            # Registrar éxito
            duration = time.time() - start_time
            self.event_console.add_event(
                pid,
                f"{operation_name}_SUCCESS",
                f"Operación completada en {duration:.2f}s",
                "success"
            )
            
        except Exception as e:
            # Registrar error
            self.event_console.add_event(
                pid,
                f"{operation_name}_ERROR",
                f"Error en {operation_name.replace('_', ' ')}: {str(e)}",
                "error"
            )
            raise
            
        finally:
            # Liberar todos los locks en orden inverso
            for lock in reversed(locks):
                lock_name = [name for name, l in vars(self.locks).items() if l == lock][0]
                lock.release()
                self.process_tracker.update_lock(lock_name, state="free", owner_pid=-1)
            
            self.process_tracker.update_process(
                pid,
                state="ready",
                current_operation="Esperando siguiente operación",
                lock_acquired=None,
                lock_waiting=None
            )

    # ======================
    # Métodos de Clientes
    # ======================

    def add_customer(self, name: str, email: str) -> Customer:
        with self._track_operation("ADD_CUSTOMER", ["customers_lock"]):
            if any(c.email == email for c in self.customers.values()):
                raise ValueError("Email ya registrado")
            customer = Customer(name, email)
            self.customers[customer.customer_id] = customer
            return customer

    def delete_customer(self, customer_id: str) -> bool:
        with self._track_operation("DELETE_CUSTOMER", ["customers_lock"]):
            if customer_id not in self.customers:
                return False
            del self.customers[customer_id]
            return True

    def get_customer_by_email(self, email: str) -> Optional[Customer]:
        with self._track_operation("GET_CUSTOMER_BY_EMAIL", ["customers_lock"]):
            for customer in self.customers.values():
                if customer.email == email:
                    return customer
            return None

    # ======================
    # Métodos de Cuentas
    # ======================

    def add_account(self, customer_id: str, initial_balance: float = 0, nip: str = None) -> Account:
        with self._track_operation("ADD_ACCOUNT", ["customers_lock", "accounts_lock"]):
            if customer_id not in self.customers:
                raise ValueError("Cliente no encontrado")
            
            account = Account(customer_id, initial_balance, nip)
            self.accounts[account.account_number] = account

            customer = self.customers[customer_id]
            if not customer.link_account(account):
                del self.accounts[account.account_number]
                raise ValueError("No se pudo vincular la cuenta al cliente")
                
            return account

    def close_account(self, account_number: str) -> bool:
        with self._track_operation("CLOSE_ACCOUNT", ["accounts_lock"]):
            if account_number not in self.accounts:
                return False
            del self.accounts[account_number]
            return True

    def get_account_balance(self, account_number: str) -> Optional[float]:
        with self._track_operation("GET_ACCOUNT_BALANCE", ["accounts_lock"]):
            account = self.accounts.get(account_number)
            return account.balance if account else None

    def get_account_transactions(self, account_number: str, limit: int = 10) -> List[Transaction]:
        with self._track_operation("GET_ACCOUNT_TRANSACTIONS", ["accounts_lock"]):
            account = self.accounts.get(account_number)
            return account.get_transactions(limit) if account else []

    def generate_account_statement(self, account_number: str, days: int = 30) -> Dict:
        with self._track_operation("GENERATE_ACCOUNT_STATEMENT", ["accounts_lock"]):
            account = self.accounts.get(account_number)
            if not account:
                return {}
                
            transactions = [t for t in account.get_transactions(100) if t.is_recent(days)]
            return {
                'account_number': account_number,
                'current_balance': account.balance,
                'transactions': transactions,
                'summary': {
                    'deposits': sum(t.amount for t in transactions if t.type == TransactionType.DEPOSIT),
                    'withdrawals': sum(t.amount for t in transactions if t.type == TransactionType.WITHDRAWAL),
                    'transfers': sum(t.amount for t in transactions if t.type == TransactionType.TRANSFER)
                }
            }

    # ======================
    # Métodos de Tarjetas
    # ======================

    def issue_debit_card(self, account_number: str, card_type: CardType) -> DebitCard:
        with self._track_operation("ISSUE_DEBIT_CARD", ["accounts_lock", "cards_lock"]):
            account = self.accounts.get(account_number)
            if not account:
                raise ValueError("Cuenta no existe")
            
            card = account.add_debit_card(card_type)
            self.card_registry[card.card_number] = card
            return card

    def issue_credit_card(self, customer_id: str, card_type: CardType) -> CreditCard:
        with self._track_operation("ISSUE_CREDIT_CARD", ["customers_lock", "cards_lock"]):
            customer = self.customers.get(customer_id)
            if not customer:
                raise ValueError("Cliente no existe")
                
            card = customer.add_credit_card(card_type)
            self.card_registry[card.card_number] = card
            return card

    def block_card(self, card_number: str) -> bool:
        with self._track_operation("BLOCK_CARD", ["cards_lock"]):
            card = self.card_registry.get(card_number)
            if not card:
                return False
            card.block_card()
            return True

    def deactivate_card(self, card_number: str) -> bool:
        with self._track_operation("DEACTIVATE_CARD", ["cards_lock", "customers_lock", "accounts_lock"]):
            card = self.card_registry.get(card_number)
            if not card:
                return False
                
            if isinstance(card, CreditCard) and card.outstanding_balance > 0:
                raise ValueError(f"Tarjeta {card_number} tiene saldo pendiente")
            
            del self.card_registry[card_number]
            
            if isinstance(card, CreditCard):
                customer = self.customers.get(card.customer_id)
                if customer:
                    customer.credit_cards = [c for c in customer.credit_cards if c.card_number != card_number]
            else:
                account = self.accounts.get(card.account_id)
                if account:
                    account.debit_cards = [dc for dc in account.debit_cards if dc.card_number != card_number]
            
            return True

    def get_credit_card_info(self, card_number: str) -> Optional[Dict]:
        with self._track_operation("GET_CREDIT_CARD_INFO", ["cards_lock"]):
            card = self.card_registry.get(card_number)
            if not isinstance(card, CreditCard):
                return None
                
            return {
                "card_type": card.type.name,
                "customer_id": card.customer_id,
                "outstanding_balance": card.outstanding_balance,
                "available_credit": card.available_credit,
                "interest_rate": card.benefits["interest_rate"],
                "status": "active" if card.is_valid() else "blocked/expired"
            }

    def get_debit_cards(self, account_number: str) -> List[DebitCard]:
        with self._track_operation("GET_DEBIT_CARDS", ["accounts_lock"]):
            account = self.accounts.get(account_number)
            return account.debit_cards.copy() if account else []

    def get_credit_cards(self, customer_id: str) -> List[CreditCard]:
        with self._track_operation("GET_CREDIT_CARDS", ["customers_lock"]):
            customer = self.customers.get(customer_id)
            return customer.credit_cards.copy() if customer else []

    def get_card_balance(self, card_number: str) -> Optional[float]:
        with self._track_operation("GET_CARD_BALANCE", ["cards_lock", "accounts_lock"]):
            card = self.card_registry.get(card_number)
            if not card:
                return None
                
            if isinstance(card, DebitCard):
                account = self.accounts.get(card.account_id)
                return account.balance if account else None
            elif isinstance(card, CreditCard):
                return card.available_credit
            return None

    # ======================
    # Operaciones Bancarias
    # ======================

    def transfer(self, source_id: str, target_id: str, amount: float, nip: Optional[str] = None) -> bool:
        with self._track_operation("TRANSFER", ["accounts_lock"]):
            if source_id == target_id:
                raise ValueError("No se puede transferir a la misma cuenta")
                
            source = self.accounts.get(source_id)
            target = self.accounts.get(target_id)
            
            if not source or not target:
                raise ValueError("Cuenta(s) no encontrada(s)")
                
            if nip and not source.validate_nip(nip):
                raise ValueError("PIN incorrecto")
                
            if source.balance < amount:
                raise ValueError("Fondos insuficientes")

            source.balance -= amount
            target.balance += amount

            source_transaction = Transaction(
                account_id=source_id,
                amount=amount,
                transaction_type=TransactionType.TRANSFER,
                description=f"Transferencia a {target_id[:4]}...",
                source_reference=target_id
            )
            
            target_transaction = Transaction(
                account_id=target_id,
                amount=amount,
                transaction_type=TransactionType.DEPOSIT,
                description=f"Transferencia de {source_id[:4]}...",
                source_reference=source_id
            )
            
            source.add_transaction(source_transaction)
            target.add_transaction(target_transaction)
            self.transaction_history.extend([source_transaction, target_transaction])
            return True

    def transfer_between_own_accounts(self, customer_id: str, source_acc: str, target_acc: str, amount: float) -> bool:
        with self._track_operation("TRANSFER_BETWEEN_OWN_ACCOUNTS"):
            owned_accounts = {acc.account_number for acc in self.get_customer_accounts(customer_id)}
            if source_acc not in owned_accounts or target_acc not in owned_accounts:
                raise ValueError("Una o ambas cuentas no pertenecen al cliente")
            return self.transfer(source_acc, target_acc, amount)

    def deposit(self, account_number: str, amount: float, source_reference: str = None) -> bool:
        with self._track_operation("DEPOSIT", ["accounts_lock"]):
            if amount <= 0:
                raise ValueError("Monto inválido")
                
            account = self.accounts.get(account_number)
            if not account:
                raise ValueError("Cuenta no encontrada")

            account.balance += amount
            transaction = Transaction(
                account_id=account_number,
                amount=amount,
                transaction_type=TransactionType.DEPOSIT if not source_reference else TransactionType.TRANSFER_RECEIVED,
                source_reference=source_reference
            )
            
            account.add_transaction(transaction)
            self.transaction_history.append(transaction)
            return True

    def withdraw(self, account_number: str, amount: float, nip: str) -> bool:
        with self._track_operation("WITHDRAW", ["accounts_lock"]):
            if amount <= 0:
                raise ValueError("Monto inválido")
                
            account = self.accounts.get(account_number)
            if not account:
                raise ValueError("Cuenta no encontrada")
                
            if account.is_locked:
                raise ValueError("Cuenta bloqueada temporalmente")
                
            if not account.validate_nip(nip):
                raise ValueError("PIN incorrecto")
                
            if account.balance < amount:
                raise ValueError("Fondos insuficientes")

            account.balance -= amount
            transaction = Transaction(
                account_id=account_number,
                amount=amount,
                transaction_type=TransactionType.WITHDRAWAL,
                description="Retiro de efectivo"
            )
            
            account.add_transaction(transaction)
            self.transaction_history.append(transaction)
            return True

    def pay_credit_card(self, card_number: str, amount: float, payment_source: Optional[str] = None, is_cash: bool = False) -> bool:
        with self._track_operation("PAY_CREDIT_CARD", ["cards_lock", "accounts_lock"]):
            card = self.card_registry.get(card_number)
            if not isinstance(card, CreditCard):
                raise ValueError("Tarjeta no es de crédito o no existe")

            if not is_cash:
                account = self.accounts.get(payment_source)
                if not account or account.balance < amount:
                    raise ValueError("Cuenta no existe o fondos insuficientes")
                    
                account.balance -= amount
                account.add_transaction(Transaction(
                    account_id=payment_source,
                    amount=amount,
                    transaction_type=TransactionType.PAYMENT,
                    card_number=card_number
                ))

            card.make_payment(amount)
            self.transaction_history.append(Transaction(
                account_id=card.customer_id if is_cash else payment_source,
                amount=amount,
                transaction_type=TransactionType.PAYMENT,
                card_number=card_number,
                is_cash=is_cash
            ))
            return True

    # ======================
    # Relación Cliente-Cuenta
    # ======================

    def link_account_to_customer(self, account_number: str, customer_id: str) -> bool:
        with self._track_operation("LINK_ACCOUNT_TO_CUSTOMER", ["accounts_lock", "customers_lock"]):
            account = self.accounts.get(account_number)
            if not account or account.customer_id != customer_id:
                raise ValueError("Cuenta no existe o no pertenece al cliente")
                
            customer = self.customers.get(customer_id)
            if not customer:
                raise ValueError("Cliente no encontrado")
                
            customer.link_account(account)
            return True

    def get_customer_accounts(self, customer_id: str) -> List[Account]:
        with self._track_operation("GET_CUSTOMER_ACCOUNTS", ["customers_lock"]):
            customer = self.customers.get(customer_id)
            return customer.accounts.copy() if customer else []

    # ======================
    # Operaciones Adicionales
    # ======================

    def apply_monthly_interest(self):
        with self._track_operation("APPLY_MONTHLY_INTEREST", ["cards_lock"]):
            total_interest = 0.0
            cards_processed = 0
            
            for card in self.card_registry.values():
                if isinstance(card, CreditCard) and card.outstanding_balance > 0:
                    interest = card.calculate_interest()
                    card.apply_interest()
                    total_interest += interest
                    cards_processed += 1
                    
                    self.transaction_history.append(Transaction(
                        account_id=card.customer_id,
                        amount=interest,
                        transaction_type=TransactionType.PAYMENT,
                        description="Interés mensual"
                    ))
            
            return cards_processed, total_interest