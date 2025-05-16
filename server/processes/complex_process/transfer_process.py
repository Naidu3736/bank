from core.transaction import Transaction, TransactionType

def execute(bank, source_id: str, target_id: str, amount: float, nip: str = None) -> bool:
    with bank._accounts_lock:
        source = bank.accounts.get(source_id)
        target = bank.accounts.get(target_id)
        
        if not source or not target:
            return False
            
        if nip and not source.validate_nip(nip):
            return False
            
        if source.balance >= amount:
            source.balance -= amount
            target.balance += amount
            
            # Registrar transacciones
            source.add_transaction(Transaction(
                source_id, amount, TransactionType.TRANSFER, target_id
            ))
            target.add_transaction(Transaction(
                target_id, amount, TransactionType.DEPOSIT, source_id
            ))
            return True
        return False