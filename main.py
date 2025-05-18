from core.bank import Bank
from core.card import CardType
from server.locks import BankLocks
from event_logger import EventConsole, ProcessTracker, BankMonitor
import time
import random
import os
import threading
from typing import List
from rich.console import Console

def customer_operations(bank: Bank, customer_id: str, account_numbers: List[str]):
    """Simula operaciones de un cliente"""
    pid = os.getpid()
    
    for i in range(5):
        time.sleep(random.uniform(0.1, 0.5))
        operation = random.choice([
            lambda: bank.deposit(account_numbers[0], random.uniform(10, 100)),
            lambda: bank.withdraw(account_numbers[0], random.uniform(10, 50), "1234"),
            lambda: bank.transfer(account_numbers[0], account_numbers[1], random.uniform(5, 30)),
            lambda: bank.get_account_balance(account_numbers[0]),
            lambda: bank.get_account_transactions(account_numbers[0])
        ])
        
        try:
            operation()
        except Exception as e:
            bank.event_console.add_event(
                pid,
                "CUSTOMER_OPERATION_ERROR",
                f"Error en operación: {str(e)}",
                "error"
            )

def credit_card_operations(bank: Bank, card_number: str, account_number: str):
    """Simula operaciones con tarjeta de crédito"""
    pid = os.getpid()
    
    for i in range(3):
        time.sleep(random.uniform(0.3, 1.0))
        try:
            if random.random() > 0.3:
                bank.pay_credit_card(
                    card_number, 
                    random.uniform(20, 100), 
                    account_number
                )
            else:
                bank.pay_credit_card(
                    card_number, 
                    random.uniform(10, 50), 
                    is_cash=True
                )
        except Exception as e:
            bank.event_console.add_event(
                pid,
                "CREDIT_CARD_OPERATION_ERROR",
                f"Error en pago: {str(e)}",
                "error"
            )

def main():
    console = Console()
    
    # Inicializar componentes
    locks = BankLocks()
    event_console = EventConsole()
    process_tracker = ProcessTracker()
    
    # Crear banco
    bank = Bank(locks, event_console, process_tracker)
    
    # Iniciar el monitor en un hilo separado
    monitor = BankMonitor(event_console, process_tracker)
    monitor_thread = threading.Thread(target=monitor.run, daemon=True)
    monitor_thread.start()
    
    try:
        console.print("\n--- Creando clientes ---", style="bold blue")
        customer1 = bank.add_customer("Juan Pérez", "juan@example.com")
        customer2 = bank.add_customer("María García", "maria@example.com")
        
        console.print("\n--- Creando cuentas ---", style="bold blue")
        account1 = bank.add_account(customer1.customer_id, 1000.0, "1234")
        account2 = bank.add_account(customer1.customer_id, 500.0, "5678")
        account3 = bank.add_account(customer2.customer_id, 2000.0, "4321")
        
        console.print("\n--- Emitiendo tarjetas ---", style="bold blue")
        debit_card1 = bank.issue_debit_card(account1.account_number, CardType.NORMAL)
        debit_card2 = bank.issue_debit_card(account2.account_number, CardType.GOLD)
        credit_card1 = bank.issue_credit_card(customer1.customer_id, CardType.PLATINUM)
        
        # Iniciar operaciones concurrentes
        console.print("\n--- Iniciando operaciones concurrentes ---", style="bold blue")
        threads = []
        
        # Operaciones del cliente 1
        t = threading.Thread(
            target=customer_operations,
            args=(bank, customer1.customer_id, [account1.account_number, account2.account_number])
        )
        threads.append(t)
        t.start()
        
        # Operaciones del cliente 2
        t = threading.Thread(
            target=customer_operations,
            args=(bank, customer2.customer_id, [account3.account_number])
        )
        threads.append(t)
        t.start()
        
        # Operaciones con tarjeta de crédito
        t = threading.Thread(
            target=credit_card_operations,
            args=(bank, credit_card1.card_number, account1.account_number)
        )
        threads.append(t)
        t.start()
        
        # Esperar a que terminen las operaciones
        for t in threads:
            t.join(timeout=10)
        
        # Operaciones administrativas finales
        console.print("\n--- Realizando operaciones administrativas ---", style="bold blue")
        bank.block_card(debit_card1.card_number)
        bank.generate_account_statement(account1.account_number)
        bank.apply_monthly_interest()
        
        console.print("\n--- Todas las operaciones completadas ---", style="bold green")
        console.print("El monitor seguirá activo durante 10 segundos más...")
        
        time.sleep(10)  # Tiempo para ver el monitor
        
    except Exception as e:
        console.print(f"\nError en main: {str(e)}", style="bold red")
    finally:
        # Detener el monitor
        monitor.running = False
        monitor_thread.join(timeout=1)
        
        # Resumen final
        console.print("\n--- Resumen final ---", style="bold green")
        console.print(f"Clientes creados: {len(bank.customers)}")
        console.print(f"Cuentas creadas: {len(bank.accounts)}")
        console.print(f"Tarjetas emitidas: {len(bank.card_registry)}")
        console.print(f"Transacciones realizadas: {len(bank.transaction_history)}")

if __name__ == "__main__":
    # Configuración para Windows
    import multiprocessing
    multiprocessing.freeze_support()
    
    main()