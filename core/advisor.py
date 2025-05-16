from multiprocessing import Lock
from core.bank import Bank
from core.card import CardType

class Advisor:
    def __init__(self, bank: Bank):
        self.bank = bank
        self.lock = Lock()  # Protects critical sections (explained below)

    # --- Administrative Operations (System Calls) ---
    def create_account(self, customer_name: str, email: str, nip: str, initial_balance: float = 0) -> str:
        with self.lock:  # Ensures thread-safe account creation
            try:
                customer = self.bank.add_customer(customer_name, email)
                account = self.bank.add_account(customer.customer_id, initial_balance, nip)
                return f"Account {account.account_number} created for {customer_name}"
            except Exception as e:
                return f"Error: {str(e)}"

    def close_account(self, account_number: str) -> str:
        with self.lock:  # Prevents race conditions during account removal
            if account_number in self.bank.accounts:
                del self.bank.accounts[account_number]
                return f"Account {account_number} closed"
            return "Account not found"

    def assign_debit_card(self, account_number: str, card_type: CardType) -> str:
        with self.lock:  # Avoids concurrent card assignment conflicts
            try:
                card = self.bank.issue_debit_card(account_number, card_type)
                return f"Debit card {card.card_number} ({card_type.name}) assigned"
            except ValueError as e:
                return f"Error: {str(e)}"

    def assign_credit_card(self, customer_id: str, card_type: CardType) -> str:
        with self.lock:  # Protects credit card issuance
            try:
                card = self.bank.issue_credit_card(customer_id, card_type)
                return f"Credit card {card.card_number} ({card_type.name}) assigned"
            except ValueError as e:
                return f"Error: {str(e)}"