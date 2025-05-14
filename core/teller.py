from typing import Optional
from datetime import datetime
from queue import PriorityQueue
from core.turn import Turn
from core.bank import Bank
from core.custumer import Customer
from core.account import Account
from core.card import CardType

class Teller:
    def __init__(self, bank: Bank, teller_id: str):
        self.bank = bank
        self.teller_id = teller_id
        self.turn_queue = PriorityQueue()
        self.current_turn: Optional[Turn] = None
        self.available = True
        self.completed_turns = []
        self.opening_time = datetime.now().replace(hour=9, minute=0, second=0)
        self.closing_time = datetime.now().replace(hour=17, minute=0, second=0)
    
    def is_open(self) -> bool:
        now = datetime.now()
        return self.opening_time <= now <= self.closing_time
    
    def add_turn(self, turn: Turn) -> bool:
        if not self.is_open():
            return False
            
        self.turn_queue.put(turn)
        return True
    
    def attend_next(self) -> bool:
        if not self.is_open() or not self.available or self.turn_queue.empty():
            return False
            
        self.current_turn = self.turn_queue.get()
        self.available = False
        return True
    
    def complete_current_turn(self) -> bool:
        if self.current_turn is None:
            return False
            
        self.current_turn.mark_as_attended()
        self.completed_turns.append(self.current_turn)
        self.current_turn = None
        self.available = True
        return True
    
    def process_deposit(self, account_number: str, amount: float) -> bool:
        if self.current_turn is None or not self.is_open():
            return False
            
        success = self.bank.deposit(account_number, amount)
        if success:
            self.complete_current_turn()
        return success
    
    def process_withdrawal(self, account_number: str, amount: float, pin: str) -> bool:
        if self.current_turn is None or not self.is_open():
            return False
            
        account = self.bank.accounts.get(account_number)
        if not account or not account.validate_nip(pin):
            return False
            
        success = self.bank.withdrawal(account_number, amount)
        if success:
            self.complete_current_turn()
        return success
    
    def process_transfer(self, source_account: str, target_account: str, amount: float, pin: str) -> bool:
        if self.current_turn is None or not self.is_open():
            return False
            
        account = self.bank.accounts.get(source_account)
        if not account or not account.validate_nip(pin):
            return False
            
        success = self.bank.transfer(source_account, target_account, amount)
        if success:
            self.complete_current_turn()
        return success
    
    def issue_debit_card(self, account_number: str, card_type: CardType) -> bool:
        if self.current_turn is None or not self.is_open():
            return False
            
        try:
            self.bank.issue_debit_card(account_number, card_type)
            self.complete_current_turn()
            return True
        except ValueError:
            return False
    
    def issue_credit_card(self, customer_id: str, card_type: CardType) -> bool:
        if self.current_turn is None or not self.is_open():
            return False
            
        try:
            self.bank.issue_credit_card(customer_id, card_type)
            self.complete_current_turn()
            return True
        except ValueError:
            return False
    
    def get_status(self) -> dict:
        return {
            "teller_id": self.teller_id,
            "available": self.available,
            "is_open": self.is_open(),
            "current_turn": str(self.current_turn) if self.current_turn else None,
            "queue_size": self.turn_queue.qsize(),
            "completed_today": len(self.completed_turns),
            "opening_time": self.opening_time.strftime("%H:%M"),
            "closing_time": self.closing_time.strftime("%H:%M")
        }
    
    def __str__(self) -> str:
        status = "Open" if self.is_open() else "Closed"
        availability = "Available" if self.available else "Busy"
        current_turn = f"Attending: {self.current_turn}" if self.current_turn else "No current turn"
        
        return (
            f"Teller {self.teller_id} - {status} - {availability}\n"
            f"{current_turn}\n"
            f"Turns in queue: {self.turn_queue.qsize()}\n"
            f"Turns completed today: {len(self.completed_turns)}"
        )