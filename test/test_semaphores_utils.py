import unittest
from unittest.mock import MagicMock, patch, call
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from server.locks import BankLocks, ResourceSemaphore
import multiprocessing

class TestBankSemaphores(unittest.TestCase):
    def setUp(self):
        self.process_tracker = MagicMock()
        
        # Mock para el semáforo subyacente
        self.mock_semaphore_impl = MagicMock()
        self.mock_semaphore_impl.acquire.return_value = True
        
        # Patch para el Semaphore real
        self.semaphore_patcher = patch('multiprocessing.Semaphore', 
                                     return_value=self.mock_semaphore_impl)
        self.mock_semaphore = self.semaphore_patcher.start()
        
        # Crear instancia real de BankLocks con nuestro mock inyectado
        self.locks = BankLocks(process_tracker=self.process_tracker)

    def tearDown(self):
        self.semaphore_patcher.stop()

    def test_semaphore_initialization(self):
        """Verifica que se inicializan los semáforos"""
        # Verificar que se crearon los semáforos con valores correctos
        self.assertEqual(self.locks.tellers_sem.max_workers, 4)
        self.assertEqual(self.locks.tellers_sem.name, "tellers_pool")
        self.assertEqual(self.locks.advisors_sem.max_workers, 2)
        self.assertEqual(self.locks.advisors_sem.name, "advisors_pool")

    def test_semaphore_acquire(self):
        """Test de adquisición con tracking"""
        # Configurar mock
        self.mock_semaphore_impl.acquire.return_value = True
        
        # Ejecutar
        result = self.locks.tellers_sem.acquire()
        
        # Verificar llamada a acquire (versión flexible)
        self.assertEqual(self.mock_semaphore_impl.acquire.call_count, 1)
        call_args = self.mock_semaphore_impl.acquire.call_args[1]
        self.assertTrue(call_args.get('blocking', True))  # Valor por defecto True
        self.assertIsNone(call_args.get('timeout'))  # Valor por defecto None
        
        # Verificar tracking
        self.process_tracker.update_lock.assert_has_calls([
            call("tellers_pool", owner_pid=unittest.mock.ANY, state="waiting"),
            call("tellers_pool", owner_pid=unittest.mock.ANY, state="acquired")
        ])

    def test_semaphore_release(self):
        """Test de liberación con tracking"""
        # Configurar mock
        self.mock_semaphore_impl.acquire.return_value = True
        self.locks.tellers_sem.acquire()  # Adquirir primero
        
        # Resetear mock para verificar solo release
        self.process_tracker.reset_mock()
        
        # Ejecutar
        self.locks.tellers_sem.release()
        
        # Verificar llamadas
        self.assertEqual(self.mock_semaphore_impl.release.call_count, 1)
        self.process_tracker.update_lock.assert_called_once_with(
            "tellers_pool", owner_pid=-1, state="released"
        )

    def test_semaphore_full_cycle(self):
        """Test completo acquire/release"""
        # Configurar mock
        self.mock_semaphore_impl.acquire.return_value = True
        
        # Ciclo completo
        self.assertTrue(self.locks.tellers_sem.acquire())
        self.locks.tellers_sem.release()
        
        # Verificar llamadas
        self.assertEqual(self.mock_semaphore_impl.acquire.call_count, 1)
        self.assertEqual(self.mock_semaphore_impl.release.call_count, 1)

if __name__ == '__main__':
    unittest.main()