import threading

class Teller:
    def __init__(self, id, bank):
        self.id = id
        self.bank = bank
        self.current_turn = None
        self.current_thread = None

    def _track(self, operation_desc):
        self.bank.process_tracker.update_process(
            threading.get_ident(),
            state="working",
            current_operation=operation_desc,
            type="Teller"
        )

    def assign_turn(self, turn):
        self.current_turn = turn

    def complete_turn(self):
        self.current_turn = None

    def deposit(self, account_number, amount):
        self._track(f"Depósito de ${amount} en cuenta {account_number}")
        self.bank.deposit(account_number, amount)

    def withdraw(self, account_number, amount, nip):
        self._track(f"Retiro de ${amount} en cuenta {account_number}")
        self.bank.withdraw(account_number, amount, nip)

    def transfer(self, source_id, target_id, amount, nip):
        self._track(f"Transferencia de ${amount} de {source_id} a {target_id}")
        self.bank.transfer(source_id, target_id, amount, nip)

    def pay_credit_card(self, card_number, amount, payment_source):
        self._track(f"Pago de ${amount} a tarjeta {card_number} desde {payment_source}")
        self.bank.pay_credit_card(card_number, amount, payment_source)

    def get_account_transactions(self, account_number):
        self._track(f"Consultar movimientos de cuenta {account_number}")
        return self.bank.get_account_transactions(account_number)

    def check_balance(self, account_number):
        self._track(f"Consultar saldo de cuenta {account_number}")
        return self.bank.get_account_balance(account_number)
