import threading
from core.bank import Bank

class Advisor:
    def __init__(self, id, bank: Bank):
        self.id = id
        self.bank = bank
        self.current_turn = None
        self.current_thread = None

    def _track(self, operation_desc):
        self.bank.process_tracker.update_process(
            threading.get_ident(),
            state="working",
            current_operation=operation_desc,
            type="Advisor"
        )

    def assign_turn(self, turn):
        self.current_turn = turn

    def complete_turn(self):
        self.current_turn = None

    def create_customer(self, name, email):
        self._track(f"Crear cliente: {name}")
        self.bank.add_customer(name, email)

    def open_account(self, customer_id, initial_balance, nip):
        self._track(f"Abrir cuenta para cliente {customer_id}")
        self.bank.add_account(customer_id, initial_balance, nip)

    def issue_credit_card(self, customer_id, card_type):
        self._track(f"Emitir tarjeta de crédito a cliente {customer_id}")
        self.bank.issue_credit_card(customer_id, card_type)

    def issue_debit_card(self, account_number, card_type):
        self._track(f"Emitir tarjeta de débito para cuenta {account_number}")
        self.bank.issue_debit_card(account_number=account_number, card_type=card_type)

    def deactivate_card(self, card_number):
        self._track(f"Desactivar tarjeta {card_number}")
        self.bank.deactivate_card(card_number)

    def link_account(self, account_number, customer_id):
        self._track(f"Vincular cuenta {account_number} al cliente {customer_id}")
        self.bank.link_account_to_customer(account_number=account_number, customer_id=customer_id)
