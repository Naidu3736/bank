import os
from core.bank import Bank
from server.locks import BankLocks
from event_logger import EventConsole, ProcessTracker, BankMonitor
from core.card import CardType
import multiprocessing
import time
import random
import signal
import sys
from typing import List
import queue

# Configuración ajustada
NUM_CLIENTES = 20  # Reducido para pruebas
MAX_OPERACIONES_POR_CLIENTE = 5
MAX_PROCESS_AT_ONCE = 10  
SIMULATION_DURATION = 30
QUEUE_TIMEOUT = 2

def customer_operations(bank: Bank, customer_id: str):
    """Versión con manejo robusto de errores"""
    try:
        # 1. Crear cuenta (obligatorio)
        account = bank.add_account(
            customer_id,
            initial_balance=random.randint(100, 5000),
            nip=str(random.randint(1000, 9999))
        )
        bank.event_console.add_event(
            os.getpid(),
            "ACCOUNT_CREATED",
            f"Cuenta {account.account_number[:4]}... creada",
            "success"
        )

        # 2. Operaciones básicas
        deposit_amt = random.randint(10, 300)
        bank.deposit(account.account_number, deposit_amt)
        
        withdraw_amt = random.randint(5, 150)
        bank.withdraw(account.account_number, withdraw_amt, account.nip)

        # 3. Operaciones condicionales
        if len(bank.accounts) > 1:
            target = random.choice([
                acc for acc in bank.accounts.keys() 
                if acc != account.account_number
            ])
            bank.transfer(account.account_number, target, random.randint(5, 100), account.nip)

        if random.random() < 0.5:  # 50% probabilidad
            bank.issue_debit_card(account.account_number, random.choice(list(CardType)))

    except Exception as e:
        bank.event_console.add_event(
            os.getpid(),
            "OPERATION_ERROR",
            f"Error: {str(e)}",
            "error"
        )

def customer_creator(bank: Bank, customer_queue: multiprocessing.Queue, stop_event):
    """Creador con verificación explícita"""
    created = 0
    while not stop_event.is_set() and created < NUM_CLIENTES:
        try:
            customer = bank.add_customer(
                f"Cliente-{created+1}",
                f"cliente.{created+1}@banco.com"
            )
            customer_queue.put(customer.customer_id)
            created += 1
            
            # Verificación crítica
            if customer_queue.qsize() == 0:
                bank.event_console.add_event(
                    os.getpid(),
                    "QUEUE_ERROR",
                    "¡La cola no está aceptando elementos!",
                    "critical"
                )
            
            time.sleep(random.uniform(0.01, 0.1))
            
        except Exception as e:
            bank.event_console.add_event(
                os.getpid(),
                "CREATION_ERROR",
                f"Error creando cliente: {str(e)}",
                "error"
            )
            time.sleep(0.5)

def operation_dispatcher(bank: Bank, customer_queue: multiprocessing.Queue, stop_event):
    """Dispatcher con manejo mejorado"""
    active_processes = []
    
    while not stop_event.is_set():
        try:
            # Limpieza de procesos
            active_processes = [p for p in active_processes if p.is_alive()]
            
            if len(active_processes) >= MAX_PROCESS_AT_ONCE:
                time.sleep(0.1)
                continue
                
            customer_id = customer_queue.get(timeout=QUEUE_TIMEOUT)
            p = multiprocessing.Process(
                target=customer_operations,
                args=(bank, customer_id),
                daemon=True
            )
            p.start()
            active_processes.append(p)
            
        except queue.Empty:
            bank.event_console.add_event(
                os.getpid(),
                "QUEUE_EMPTY",
                "Esperando clientes...",
                "warning"
            )
            time.sleep(1)
        except Exception as e:
            bank.event_console.add_event(
                os.getpid(),
                "DISPATCHER_FAILURE",
                f"Error crítico: {str(e)}",
                "critical"
            )
            time.sleep(2)

def main():
    # Configuración esencial
    signal.signal(signal.SIGINT, signal_handler)
    
    # Inicialización explícita del Manager
    manager = multiprocessing.Manager()
    print(f"Manager state: {manager._state}")  # Debug
    
    # Estructuras compartidas
    shared_data = {
        'accounts': manager.dict(),
        'customers': manager.dict(),
        'cards': manager.dict(),
        'transactions': manager.list()
    }
    
    # Sistema central
    locks = BankLocks()
    event_console = EventConsole(manager=manager)
    process_tracker = ProcessTracker(manager=manager)
    customer_queue = manager.Queue(maxsize=100)
    stop_event = manager.Event()
    
    # Banco
    bank = Bank(locks, event_console, process_tracker, shared_data, manager)
    
    # Monitor (con verificación)
    monitor = BankMonitor(event_console, process_tracker)
    monitor_process = multiprocessing.Process(
        target=monitor.run,
        daemon=True
    )
    monitor_process.start()
    time.sleep(1)  # Esperar inicialización
    
    try:
        # Procesos principales
        creator = multiprocessing.Process(
            target=customer_creator,
            args=(bank, customer_queue, stop_event),
            daemon=True
        )
        creator.start()
        
        dispatchers = [
            multiprocessing.Process(
                target=operation_dispatcher,
                args=(bank, customer_queue, stop_event),
                daemon=True
            ) for _ in range(2)
        ]
        for d in dispatchers:
            d.start()
        
        # Espera controlada
        print(f"\nSimulación en curso por {SIMULATION_DURATION} segundos...")
        time.sleep(SIMULATION_DURATION)
        
    finally:
        # Finalización controlada
        stop_event.set()
        creator.join(timeout=5)
        for d in dispatchers:
            d.join(timeout=5)
        
        # Estadísticas verificadas
        print("\n=== Estadísticas Verificadas ===")
        print(f"Clientes en sistema: {len(bank.customers)}")
        print(f"Cuentas creadas: {len(bank.accounts)}")
        print(f"Transacciones registradas: {len(bank.transaction_history)}")
        print(f"Elementos en cola no procesados: {customer_queue.qsize()}")
        
        # Debug adicional
        if not bank.customers:
            print("\n[DEBUG] Estado interno:")
            print(f"- Manager activo: {manager._state.value == 'STARTED'}")
            print(f"- Cola compartida: {type(customer_queue)}")
            print(f"- Eventos registrados: {len(event_console.get_events(100))}")

def signal_handler(sig, frame):
    print("\nInterrupción recibida")
    sys.exit(0)

if __name__ == "__main__":
    # Verificación de entorno multiproceso
    multiprocessing.set_start_method('spawn')  # Crucial para Linux/Mac
    print("Iniciando con método:", multiprocessing.get_start_method())
    main()