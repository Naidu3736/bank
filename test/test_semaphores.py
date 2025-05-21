import unittest
from unittest.mock import MagicMock, patch, call
import sys
import os

# Agregar el directorio padre al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.turn import Turn, Operation, OperationType
from server.process_dispatcher import ProcessDispatcher
import multiprocessing

class TestDispatcherSemaphores(unittest.TestCase):
    def setUp(self):
        # Configuración básica
        self.mock_bank = MagicMock()
        self.event_console = MagicMock()
        self.process_tracker = MagicMock()
        
        # Mock de locks y semáforos
        self.mock_locks = MagicMock()
        self.mock_locks.tellers_sem = MagicMock()
        self.mock_locks.advisors_sem = MagicMock()
        self.mock_locks.turn_queue_lock = MagicMock()
        
        # Dispatcher con mocks
        self.dispatcher = ProcessDispatcher(
            bank=self.mock_bank,
            num_tellers=2,
            num_advisors=1,
            event_console=self.event_console,
            process_tracker=self.process_tracker
        )
        self.dispatcher.locks = self.mock_locks

    def _create_test_turn(self, requires_advisor=False):
        """Helper para crear turnos de prueba"""
        op_type = OperationType.ISSUE_CREDIT_CARD if requires_advisor else OperationType.DEPOSIT
        return Turn(operations=[Operation(op_type, account_number='ACC123', amount=100)])

    # --------------------------
    # Tests de adquisición de semáforos
    # --------------------------
    
    def test_acquire_teller_semaphore_on_teller_turn(self):
        """Debería adquirir semáforo de cajeros para turno de cajero"""
        test_turn = self._create_test_turn(requires_advisor=False)
        self.mock_locks.tellers_sem.acquire.return_value = True
        
        with patch.object(self.dispatcher, '_start_process_for_turn', return_value=True):
            self.dispatcher._assign_handler(test_turn)
            self.mock_locks.tellers_sem.acquire.assert_called_once()
            self.mock_locks.advisors_sem.acquire.assert_not_called()

    def test_acquire_advisor_semaphore_on_advisor_turn(self):
        """Debería adquirir semáforo de asesores para turno de asesor"""
        test_turn = self._create_test_turn(requires_advisor=True)
        self.mock_locks.advisors_sem.acquire.return_value = True
        
        with patch.object(self.dispatcher, '_start_process_for_turn', return_value=True):
            self.dispatcher._assign_handler(test_turn)
            self.mock_locks.advisors_sem.acquire.assert_called_once()
            self.mock_locks.tellers_sem.acquire.assert_not_called()

    # --------------------------
    # Tests de liberación de semáforos
    # --------------------------
    
    def test_release_semaphore_when_no_available_handler(self):
        """Debería liberar semáforo si no hay handlers disponibles"""
        test_turn = self._create_test_turn()
        self.mock_locks.tellers_sem.acquire.return_value = True
        self.dispatcher.tellers = []  # Ningún cajero disponible
        
        success = self.dispatcher._assign_handler(test_turn)
        self.assertFalse(success)
        self.mock_locks.tellers_sem.release.assert_called_once()

    def test_release_semaphore_on_process_start_failure(self):
        """Debería liberar semáforo si falla el inicio del proceso"""
        test_turn = self._create_test_turn()
        self.mock_locks.tellers_sem.acquire.return_value = True
        mock_teller = MagicMock()
        mock_teller.current_turn = None
        self.dispatcher.tellers = [mock_teller]
        
        with patch.object(self.dispatcher, '_start_process_for_turn', return_value=False):
            success = self.dispatcher._assign_handler(test_turn)
            self.assertFalse(success)
            self.mock_locks.tellers_sem.release.assert_called_once()

    # --------------------------
    # Tests de comportamiento de bloqueo
    # --------------------------
    
    def test_semaphore_blocking_behavior(self):
        """Debería manejar correctamente semáforos bloqueados"""
        test_turn = self._create_test_turn()
        self.mock_locks.tellers_sem.acquire.return_value = False  # Semáforo bloqueado
        
        success = self.dispatcher._assign_handler(test_turn)
        self.assertFalse(success)
        self.mock_locks.tellers_sem.acquire.assert_called_once()

    def test_non_blocking_semaphore_acquire(self):
        """Debería usar acquire(block=False) para evitar bloqueos"""
        test_turn = self._create_test_turn()
        
        # Verificar parámetros de llamada a acquire
        self.dispatcher._assign_handler(test_turn)
        call_args = self.mock_locks.tellers_sem.acquire.call_args
        self.assertEqual(call_args, call(block=False))

    # --------------------------
    # Tests de integración de semáforos
    # --------------------------
    
    def test_semaphore_integration_with_process_lifecycle(self):
        """Test completo del ciclo de vida con semáforos"""
        # Configuración inicial
        test_turn = self._create_test_turn()
        self.mock_locks.tellers_sem.acquire.return_value = True
        
        # Creamos un mock más realista del teller
        mock_teller = MagicMock()
        mock_teller.current_turn = None  # Estado inicial
        mock_teller.teller_id = "T1"
        
        # Configuramos el comportamiento de complete_turn
        def complete_turn_side_effect():
            mock_teller.current_turn = None
        mock_teller.complete_turn.side_effect = complete_turn_side_effect
        
        self.dispatcher.tellers = [mock_teller]
        
        # Mock del proceso que termina inmediatamente
        mock_process = MagicMock()
        mock_process.is_alive.return_value = False
        
        with patch('multiprocessing.Process', return_value=mock_process):
            # 1. Asignar turno
            success = self.dispatcher._assign_handler(test_turn)
            self.assertTrue(success)
            
            # Simular que el proceso fue asignado
            mock_teller.current_process = mock_process
            mock_teller.current_turn = test_turn
            
            # 2. Ejecutar cleanup
            self.dispatcher._cleanup_processes()
            
            # 3. Verificaciones
            mock_teller.complete_turn.assert_called_once()
            self.mock_locks.tellers_sem.release.assert_called_once()
            self.assertIsNone(mock_teller.current_turn)

if __name__ == '__main__':
    unittest.main()