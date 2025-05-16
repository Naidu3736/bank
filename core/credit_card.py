from core.card import Card, CardType

class CreditCard(Card):
    _BENEFITS = {
        CardType.NORMAL: {"fee": 0.03, "credit_limit": 10000, "interest_rate": 0.05},
        CardType.GOLD: {"fee": 0.02, "credit_limit": 20000, "interest_rate": 0.04},
        CardType.PLATINUM: {"fee": 0.01, "credit_limit": 50000, "interest_rate": 0.03}
    }

    def __init__(self, card_type: CardType, customer_id: str):
        super().__init__(card_type)
        self.customer_id = customer_id
        self.benefits = self._BENEFITS[card_type]
        self.credit_limit = self.benefits["credit_limit"]
        self.outstanding_balance = 0
        self.available_credit = self.credit_limit

    def make_purchase(self, amount):
        if not self.is_valid():
            raise ValueError("Tarjeta no válida o bloqueada")
        if amount > self.available_credit:
            raise ValueError("Límite de crédito insuficiente")

        self.outstanding_balance += amount
        self.available_credit -= amount

    def make_payment(self, amount):
        if amount <= 0:
            raise ValueError("El monto debe ser positivo")
        payment = min(amount, self.outstanding_balance)
        self.outstanding_balance -= payment
        self.available_credit += payment

    def calculate_interest(self):
        return self.outstanding_balance * self.benefits["interest_rate"]
    
    def apply_interest(self):
        """Aplica el interés acumulado al saldo pendiente."""
        interest = self.calculate_interest()
        self.outstanding_balance += interest
        self.available_credit -= interest

    def get_statement(self) -> str:
        return (
            f"Tarjeta {self.type.name}\n"
            f"Crédito disponible: ${self.available_credit:.2f}\n"
            f"Saldo pendiente: ${self.outstanding_balance:.2f}\n"
            f"Interés mensual: {self.benefits['interest_rate'] * 100:.1f}%\n"
        )
    
    def reset_credit_limit(self):
        """Resetea el crédito disponible si el saldo pendiente es 0."""
        if self.outstanding_balance == 0:
            self.available_credit = self.credit_limit

    def is_overdue(self, days_late: int) -> bool:
        return self.outstanding_balance > 0 and days_late > 30  # Ajustable

    def __str__(self):
        return f"[CRÉDITO] {self.type.name} {self.card_number[:4]}****{self.card_number[-4:]}, Límite: ${self.credit_limit}, Saldo: ${self.outstanding_balance}"
