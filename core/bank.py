from typing import Dict
from core.transaction import Transaction, TransactionType
from core.account import Account
from core.custumer import Customer
from core.card import CardType
from core.debit_card import DebitCard
from core.credit_card import CreditCard

class Bank:
    def __init__(self):
        self.accounts: Dict[str, Account] = {}  # Cuentas registradas en el banco
        self.customers: Dict[str, Customer] = {}    # Cliente registrados en el banco
        self.card_registry: Dict[str, DebitCard | CreditCard] = {}  # Tarjetas registradas en el sistema

    def add_customer(self, name, email):
        customer = Customer(name, email)
        self.customers[customer.customer_id] = customer
        return customer

    def add_account(self, customer_id, initial_balance=0, nip=None):
        if customer_id not in self.customers:
            raise ValueError("Cliente no encontrado")

        account = Account(customer_id, initial_balance, nip)
        self.accounts[account.account_number] = account
        self.customers[customer_id].link_account(account)
        return account

    def issue_debit_card(self, account_number: str, card_type: CardType) -> DebitCard:
        if account_number not in self.accounts:
            raise ValueError("Cuenta no existe")

        account = self.accounts[account_number]
        card = account.add_debit_card(card_type)
        self.card_registry[card.card_number] = card
        return card

    def issue_credit_card(self, customer_id: str, card_type: CardType) -> CreditCard:
        if customer_id not in self.customers:
            raise ValueError("Cliente no existe")

        customer = self.customers[customer_id]
        card = customer.add_credit_card(card_type)
        self.card_registry[card.card_number] = card
        return card

    def process_debit_payment(self, card_number: str, amount: float, merchant: str) -> bool:
        card = self.card_registry.get(card_number)
        if not isinstance(card, DebitCard):
            return False

        account = self.accounts.get(card.account_id)
        if not account or not card.is_valid():
            return False

        if not card.can_spend(amount):
            return False

        if account.balance < amount:
            return False

        account.balance -= amount
        card.register_spending(amount)

        transaction = Transaction(
            account_id=card.account_id,
            amount=amount,
            transaction_type="purchase",
            merchant=merchant,
            card_number=card_number
        )
        account.add_transaction(transaction)
        return True

    def process_credit_payment(self, card_number: str, amount: float, merchant: str) -> bool:
        card = self.card_registry.get(card_number)
        if not isinstance(card, CreditCard):
            return False

        if not card.is_valid():
            return False

        try:
            card.make_purchase(amount)
        except ValueError:
            return False

        transaction = Transaction(
            account_id=card.customer_id,
            amount=amount,
            transaction_type="purchase",
            merchant=merchant,
            card_number=card_number
        )
        customer = self.customers[card.customer_id]
        customer.transactions.append(transaction)
        return True

    def deposit(self, account_id: str, amount: float) -> bool:
        if account_id not in self.accounts:
            return False

        account = self.accounts[account_id]
        account.balance += amount
        account.transaction_history.append(
            Transaction(account_id=account_id, amount=amount, transaction_type=TransactionType.DEPOSIT)
        )
        return True

    def withdrawal(self, account_id: str, amount: float) -> bool:
        if account_id not in self.accounts:
            return False

        account = self.accounts[account_id]
        if account.balance < amount:
            return False

        account.balance -= amount
        account.transaction_history.append(
            Transaction(account_id=account_id, amount=amount, transaction_type=TransactionType.WITHDRAWAL)
        )
        return True

    def transfer(self, source_id: str, target_id: str, amount: float) -> bool:
        if source_id not in self.accounts or target_id not in self.accounts:
            return False

        source = self.accounts[source_id]
        target = self.accounts[target_id]

        if source.balance < amount:
            return False

        source.balance -= amount
        target.balance += amount

        source.transaction_history.append(
            Transaction(account_id=source_id, amount=amount, transaction_type=TransactionType.TRANSFER, merchant=target_id)
        )
        target.transaction_history.append(
            Transaction(account_id=target_id, amount=amount, transaction_type=TransactionType.DEPOSIT, merchant=source_id)
        )
        return True
