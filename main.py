import time
import json
from server.bank_server import BankSystem
from core.debit_card import DebitCard, CardType

if __name__ == "__main__":
    bank_system = BankSystem()
    
    # Añadir cajeros
    bank_system.add_teller("VENTANILLA-1")
    bank_system.add_teller("VENTANILLA-2")
    
    # Crear cliente
    customer = bank_system.create_customer("María García", "maria@example.com")
    
    # Crear cuenta
    account = bank_system.create_account(customer['customer_id'], initial_balance=1000, nip="1234")
    
    # Solicitar turno (como cliente con tarjeta)
    turn_id = bank_system.request_turn(
        "treller",
        customer_id=customer['customer_id'],
        card_number="1234567890123456"
    )
    
    # Procesar transacciones concurrentemente
    deposit_pid = bank_system.process_transaction(
        "deposit",
        account_number=account['account_number'],
        amount=500
    )
    
    withdrawal_pid = bank_system.process_transaction(
        "withdrawal",
        account_number=account['account_number'],
        amount=200
    )
    
    # Monitorear estado
    time.sleep(1)
    print("Estado del sistema:")
    print(json.dumps(bank_system.get_system_status(), indent=2))