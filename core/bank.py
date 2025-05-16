from threading import Lock
from typing import Dict
from core.transaction import Transaction, TransactionType
from core.account import Account
from core.customer import Customer 
from core.card import CardType
from core.debit_card import DebitCard
from core.credit_card import CreditCard

class Bank:
    def __init__(self):
        self.accounts: Dict[str, Account] = {}
        self.customers: Dict[str, Customer] = {}
        self.card_registry: Dict[str, DebitCard | CreditCard] = {}
        self._accounts_lock = Lock()
        self._customers_lock = Lock()
        self._cards_lock = Lock()

    def add_customer(self, name: str, email: str) -> Customer:
        with self._customers_lock:
            customer = Customer(name, email)
            self.customers[customer.customer_id] = customer
            return customer

    def add_account(self, customer_id: str, initial_balance: float = 0, nip: str = None) -> Account:
        with self._customers_lock:
            if customer_id not in self.customers:
                raise ValueError("Cliente no encontrado")

        with self._accounts_lock:
            account = Account(customer_id, initial_balance, nip)
            self.accounts[account.account_number] = account
            self.customers[customer_id].link_account(account)
            return account

    def issue_debit_card(self, account_number: str, card_type: CardType) -> DebitCard:
        with self._accounts_lock:
            if account_number not in self.accounts:
                raise ValueError("Cuenta no existe")
            account = self.accounts[account_number]

        with self._cards_lock:
            card = account.add_debit_card(card_type)
            self.card_registry[card.card_number] = card
            return card
        
    def issue_credit_card(self, customer_id: str, card_type: CardType) -> CreditCard:
        with self._customers_lock:
            if customer_id not in self.customers:
                raise ValueError("Cliente no existe")
            customer = self.customers[customer_id]

        with self._cards_lock:
            card = customer.add_credit_card(card_type)
            self.card_registry[card.card_number] = card
            return card

    def process_debit_payment(self, card_number: str, amount: float, merchant: str) -> bool:
        with self._cards_lock:
            card = self.card_registry.get(card_number)
            if not isinstance(card, DebitCard):
                return False

        with self._accounts_lock:
            account = self.accounts.get(card.account_id)
            if not account or not card.is_valid() or not card.can_spend(amount):
                return False
            if account.balance < amount:
                return False

            account.balance -= amount
            card.register_spending(amount)

            transaction = Transaction(
                account_id=card.account_id,
                amount=amount,
                transaction_type=TransactionType.PURCHASE,
                merchant=merchant,
                card_number=card_number
            )
            account.add_transaction(transaction)
            return True

    def process_credit_purchase(self, card_number: str, amount: float, merchant: str) -> bool:
        with self._cards_lock:
            card = self.card_registry.get(card_number)
            if not isinstance(card, CreditCard) or not card.is_valid():
                return False

        try:
            card.make_purchase(amount)
            # Podrías almacenar la transacción en el cliente si llevas historial
            return True
        except ValueError:
            return False

    def pay_credit_card(self, card_number: str, amount: float) -> bool:
        with self._cards_lock:
            card = self.card_registry.get(card_number)
            if not isinstance(card, CreditCard):
                return False

        try:
            card.make_payment(amount)
            return True
        except ValueError:
            return False

    def apply_all_credit_interest(self):
        with self._cards_lock:
            for card in self.card_registry.values():
                if isinstance(card, CreditCard) and card.outstanding_balance > 0:
                    card.apply_interest()

    def transfer(self, source_id: str, target_id: str, amount: float) -> bool:
        with self._accounts_lock:
            if source_id not in self.accounts or target_id not in self.accounts:
                return False

            source = self.accounts[source_id]
            target = self.accounts[target_id]

            if source.balance < amount:
                return False

            source.balance -= amount
            target.balance += amount

            source.transaction_history.append(
                Transaction(source_id, amount, TransactionType.TRANSFER, target_id)
            )
            target.transaction_history.append(
                Transaction(target_id, amount, TransactionType.DEPOSIT, source_id)
            )
            return True

    def deposit(self, account_number: str, amount: float) -> bool:
        with self._accounts_lock:
            account = self.accounts.get(account_number)
            if account:
                account.deposit(amount)
                return True
            return False

    def withdraw(self, account_number: str, amount: float) -> bool:
        with self._accounts_lock:
            account = self.accounts.get(account_number)
            if account and account.withdraw(amount):
                return True
            return False
