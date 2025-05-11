from hashlib import sha256
import re  # Para validación de formato

class Account:
    def __init__(self, account_number, customer_id, number_card, card_type, initial_balance=0, nip=None):
        self.account_number = account_number
        self.customer_id = customer_id
        self.balance = initial_balance
        self.nip_hash = self._hash_nip(nip) if nip else None
        self.number_card = number_card
        self.card_type = card_type
        self.nip_attempts = 0  # Contador de intentos fallidos
        self.is_locked = False  # Bloqueo por seguridad

    def _hash_nip(self, nip):
        """Cifra el NIP (sin restricción de longitud)."""
        if not self._is_valid_nip(nip):
            raise ValueError("Formato de NIP inválido")
        return sha256(nip.encode('utf-8')).hexdigest()

    def _is_valid_nip(self, nip):
        """Valida el formato del NIP (ej: mínimo 4 caracteres, solo dígitos)."""
        # Ejemplo: Entre 4
        return bool(re.fullmatch(r'^\d{4}$', nip))

    def verify_nip(self, nip):
        """Verifica el NIP y maneja intentos fallidos."""
        if self.is_locked:
            raise ValueError("Cuenta bloqueada. Contacte al banco.")
        
        if self.nip_hash and sha256(nip.encode('utf-8')).hexdigest() == self.nip_hash:
            self.nip_attempts = 0  # Resetear intentos si es correcto
            return True
        
        self.nip_attempts += 1
        if self.nip_attempts >= 3:  # Bloquear tras 3 intentos fallidos
            self.is_locked = True
        return False