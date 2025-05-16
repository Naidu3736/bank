def process_transfer(bank, source_account, target_account, amount, nip):
    """Procesa una transferencia entre cuentas"""
    source = bank.accounts.get(source_account)
    if source and source.validate_nip(nip):
        return bank.transfer(source_account, target_account, amount)
    return False