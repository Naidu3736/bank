from core.card import Card, CardType

class DebitCard(Card):
    _BENEFITS = {
        CardType.NORMAL: {"fee": 0.02, "daily_limit": 5000, "cashback": 0.01},
        CardType.GOLD: {"fee": 0.01, "daily_limit": 10000, "cashback": 0.02},
        CardType.PLATINUM: {"fee": 0.0, "daily_limit": 20000, "cashback": 0.03}
    }

    def __init__(self, card_type: CardType, account_id: str):
        super().__init__(card_type)
        self.account_id = account_id
        self.daily_spent = 0
        self.benefits = self._BENEFITS[card_type]

    def __str__(self):
        return f"[DÉBITO] {self.type.name} {self.card_number[:4]}****{self.card_number[-4:]}, Límite diario: ${self.benefits['daily_limit']}"
