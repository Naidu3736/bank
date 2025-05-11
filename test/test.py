import unittest
from hashlib import sha256
from core.account import Account
from core.card import CardType, generate_card_number
import uuid
from core.custumer import Custumer

class TestAccount(unittest.TestCase):
    def setUp(self):
        # Configuración común para todas las pruebas
        self.account = Account(
            account_number="123456",
            customer_id="C001",
            number_card="4111111111111111",
            card_type="VISA",
            initial_balance=1000,
            nip="1234"
        )

    def test_nip_hashing(self):
        """Verifica que el NIP se hashea correctamente."""
        test_nip = "1234"
        expected_hash = sha256(test_nip.encode('utf-8')).hexdigest()
        self.assertEqual(self.account.nip_hash, expected_hash)

    def test_valid_nip_verification(self):
        """Verifica que un NIP correcto pase la validación."""
        self.assertTrue(self.account.verify_nip("1234"))

    def test_invalid_nip_verification(self):
        """Verifica que un NIP incorrecto falle."""
        self.assertFalse(self.account.verify_nip("0000"))

    def test_account_lock_after_3_attempts(self):
        """Verifica que la cuenta se bloquee tras 3 intentos fallidos."""
        for _ in range(3):
            self.account.verify_nip("wrong")
        self.assertTrue(self.account.is_locked)


class TestCard(unittest.TestCase):
    def test_card_number_generation(self):
        """Verifica que el número de tarjeta generado tenga 16 dígitos."""
        for card_type in CardType:
            card_number = generate_card_number(card_type)
            self.assertEqual(len(card_number), 16)
            self.assertTrue(card_number.startswith(card_type.value))

    def test_card_type_prefixes(self):
        """Verifica que los prefijos de cada tipo de tarjeta sean correctos."""
        self.assertEqual(CardType.NORMAL.value, "4")
        self.assertEqual(CardType.GOLD.value, "51")
        self.assertEqual(CardType.PLATINUM.value, "52")


class TestCustomer(unittest.TestCase):
    def test_customer_id_generation(self):
        """Verifica que el customer_id sea un UUID válido."""
        customer = Custumer(name="Ana", id="A001", email="ana@test.com")
        try:
            uuid.UUID(customer.custumer_id, version=4)
        except ValueError:
            self.fail("El customer_id no es un UUID válido")

    def test_customer_attributes(self):
        """Verifica que los atributos del cliente se asignen correctamente."""
        customer = Custumer(name="Juan", id="J001", email="juan@test.com")
        self.assertEqual(customer.name, "Juan")
        self.assertEqual(customer.email, "juan@test.com")

if __name__ == '__main__':
    unittest.main()