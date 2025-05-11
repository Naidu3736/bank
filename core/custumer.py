import uuid

class Custumer:
    @staticmethod
    def generate_customer_id():
        """Genera un UUID único para el cliente (ej: '550e8400-e29b-41d4-a716-446655440000')"""
        return str(uuid.uuid4())

    def __init__(self, name, email):
        self.custumer_id = self.generate_customer_id() 
        self.name = name
        self.email = email