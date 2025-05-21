import threading
import time
import random
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.bank import Bank
from core.turn import Turn, Operation, OperationType
from core.card import CardType
from server.locks import BankLocks
from server.process_dispatcher import ProcessDispatcher
from event_logger import EventConsole, ProcessTracker, BankMonitor

class BankSimulation:
    def __init__(self):
        self.event_console = EventConsole()
        self.process_tracker = ProcessTracker()
        self.bank = Bank(
            locks=BankLocks(process_tracker=self.process_tracker),
            event_console=self.event_console,
            process_tracker=self.process_tracker
        )
        self.dispatcher = ProcessDispatcher(
            self.bank,
            num_tellers=3,
            num_advisors=1,
            event_console=self.event_console,
            process_tracker=self.process_tracker
        )
        self.monitor = BankMonitor(self.event_console, self.process_tracker)
        self.turn_counter = 0

    def generate_random_turn(self) -> Turn:
        operations = []
        
        # Only create new customer if no customers exist or with 10% probability
        if not self.bank.customers or random.random() < 0.1:
            name = random.choice(["Juan", "Ana", "Pedro", "Sofía"]) + " " + random.choice(["García", "López"])
            email = f"{name.lower().replace(' ', '.')}{random.randint(1000,9999)}@mail.com"
            operations.append(Operation(OperationType.ADD_CUSTOMER, name=name, email=email))
        
        # If we have customers, perform other operations
        if self.bank.customers:
            # Choose an existing customer
            customer = random.choice(list(self.bank.customers.values()))
            
            # 40% chance to create an account if none exists
            if not customer.accounts or random.random() < 0.4:
                operations.append(Operation(
                    OperationType.CREATE_ACCOUNT,
                    customer_id=customer.customer_id,
                    initial_balance=random.randint(100, 1000),
                    nip=f"{random.randint(0, 9999):04d}"
                ))
            
            # 30% chance to issue a card if accounts exist
            if customer.accounts and random.random() < 0.3:
                card_type = random.choice(list(CardType))
                account_number = customer.accounts[0].account_number if customer.accounts else None
                if account_number and random.random() > 0.5:
                    operations.append(Operation(
                        OperationType.ISSUE_DEBIT_CARD,
                        account_number=account_number,
                        card_type=card_type
                    ))
                else:
                    operations.append(Operation(
                        OperationType.ISSUE_CREDIT_CARD,
                        customer_id=customer.customer_id,
                        card_type=card_type
                    ))
            
            # Regular operations (1-3)
            for _ in range(random.randint(1, 3)):
                op = self._random_operation_for(customer)
                if op:
                    operations.append(op)
        
        return Turn(operations=operations)

    def _random_operation_for(self, customer):
        op_type = random.choice([
            OperationType.DEPOSIT,
            OperationType.WITHDRAWAL,
            OperationType.TRANSFER,
            OperationType.CREDIT_PAYMENT
        ])
        if not customer.accounts:
            return None

        account = random.choice(customer.accounts)
        details = {"account_number": account.account_number}

        if op_type in [OperationType.DEPOSIT, OperationType.WITHDRAWAL]:
            details["amount"] = random.randint(50, 300)
            if op_type == OperationType.WITHDRAWAL:
                details["nip"] = "1234"  # para pruebas

        elif op_type == OperationType.TRANSFER:
            possible_targets = [
                acc for acc in self.bank.accounts.values()
                if acc.customer_id != customer.customer_id
            ]
            if not possible_targets:
                return None  # No hay cuentas destino, no se puede hacer transferencia
            target = random.choice(possible_targets)
            details = {
                "source_id": account.account_number,
                "target_id": target.account_number,
                "amount": random.randint(50, 300),
                "nip": "1234"
            }

        elif op_type == OperationType.CREDIT_PAYMENT:
            if not customer.credit_cards:
                return None
            card = random.choice(customer.credit_cards)
            details = {
                "card_number": card.card_number,
                "amount": random.randint(50, 300),
                "payment_source": account.account_number
            }
            return Operation(op_type, **details)

        return Operation(op_type, **details)

    def run(self, duration_minutes=5):
        threading.Thread(target=self.monitor.run, daemon=True).start()
        print("[DEBUG] Lanzando hilo del despachador...")
        threading.Thread(target=self.dispatcher.dispatch_processes, daemon=True).start()

        print(f"🏁 Iniciando simulación por {duration_minutes} minutos...\n")
        end = time.time() + duration_minutes * 60

        try:
            while time.time() < end:
                turn = self.generate_random_turn()
                self.dispatcher.assign_turn(turn)
                self.turn_counter += 1

                if self.turn_counter % 10 == 0:
                    print(f"📦 Turnos generados: {self.turn_counter}")
                time.sleep(random.uniform(0.2, 1))

            print("\n✅ Simulación finalizada")
        except KeyboardInterrupt:
            print("\n🛑 Simulación interrumpida por el usuario.")

if __name__ == "__main__":
    BankSimulation().run(duration_minutes=5)
