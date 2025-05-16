from core.transaction import Transaction, TransactionType

def execute(bank, account_number: str, amount: float, nip: str) -> bool:
    with bank._accounts_lock:
        account = bank.accounts.get(account_number)
        if not account or not account.validate_nip(nip):
            return False
            
        if account.balance >= amount:
            account.balance -= amount
            account.add_transaction(Transaction(
                account_number,
                amount,
                TransactionType.WITHDRAWAL
            ))
            return True
        return False