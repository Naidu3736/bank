import unittest
import multiprocessing
import time
import sys
import os

# Agregar el directorio padre al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from server.teller import Teller
from server.advisor import Advisor
from unittest.mock import MagicMock, patch, PropertyMock
from server.process_dispatcher import ProcessDispatcher
from core.turn import OperationType, Turn, ServiceType, Operation
from core.bank import Bank
from server.locks import BankLocks
from event_logger import EventConsole, ProcessTracker
from functools import partial

class TestProcessDispatcher(unittest.TestCase):
    def setUp(self):
        # Configuración inicial para las pruebas
        self.mock_bank = MagicMock(spec=Bank)
        self.event_console = EventConsole()
        self.process_tracker = ProcessTracker()
        
        # Configurar el atributo _manager en el mock del banco
        self.mock_bank._manager = MagicMock()
        
        # Configurar mocks para los componentes dependientes
        self.mock_turn_manager = MagicMock()
        self.mock_locks = MagicMock(spec=BankLocks)
        self.mock_locks.tellers_sem = MagicMock()
        self.mock_locks.advisors_sem = MagicMock()
        self.mock_locks.turn_queue_lock = MagicMock()
        
        # Crear instancia del dispatcher con mocks
        self.dispatcher = ProcessDispatcher(
            bank=self.mock_bank,
            num_tellers=2,
            num_advisors=1,
            event_console=self.event_console,
            process_tracker=self.process_tracker
        )
        
        # Reemplazar componentes internos con mocks
        self.dispatcher.turn_manager = self.mock_turn_manager
        self.dispatcher.locks = self.mock_locks
        
        # Configurar comportamiento por defecto de los mocks
        self.mock_locks.tellers_sem.acquire.return_value = True
        self.mock_locks.advisors_sem.acquire.return_value = True

    def _create_teller_turn(self):
        """Crea un turno para cajero"""
        return Turn(operations=[Operation(OperationType.DEPOSIT, account_number='ACC123', amount=100)])

    def _create_advisor_turn(self):
        """Crea un turno para asesor"""
        return Turn(operations=[Operation(OperationType.ISSUE_CREDIT_CARD, customer_id='CUST123', card_type='GOLD')])

    def test_initialization(self):
        """Prueba que el dispatcher se inicializa correctamente"""
        self.assertEqual(len(self.dispatcher.tellers), 2)
        self.assertEqual(len(self.dispatcher.advisors), 1)
        self.assertIsInstance(self.dispatcher.operation_queue, multiprocessing.queues.Queue)
        self.assertTrue(self.dispatcher._running.is_set())
        
    def test_assign_turn(self):
        """Prueba que se puede asignar un turno correctamente"""
        test_turn = self._create_teller_turn()
        
        with patch.object(self.dispatcher, '_log_event') as mock_log:
            self.dispatcher.assign_turn(test_turn)
            
            self.mock_turn_manager.add_turn.assert_called_once_with(test_turn)
            mock_log.assert_called_once_with(
                "TURN_ADDED",
                f"Turn {test_turn.turn_id} added to queue",
                "info"
            )
            
    def test_get_next_turn(self):
        """Prueba la obtención del siguiente turno"""
        test_turn = self._create_teller_turn()
        self.mock_turn_manager.get_next_turn.return_value = test_turn
        
        self.mock_locks.turn_queue_lock.__enter__.return_value = None
        
        result = self.dispatcher._get_next_turn()
        self.assertEqual(result, test_turn)
        self.mock_turn_manager.get_next_turn.assert_called_once()
        
    def test_assign_handler_teller_turn(self):
        """Prueba la asignación de un turno a un cajero"""
        test_turn = self._create_teller_turn()
        
        # Create a proper mock teller with spec
        mock_teller = MagicMock(spec=Teller)
        mock_teller.current_turn = None
        mock_teller.teller_id = "T1"
        mock_teller.assign_turn = MagicMock()
        mock_teller.complete_turn = MagicMock()
        
        # Replace the tellers list
        self.dispatcher.tellers = [mock_teller]
        
        # Ensure semaphore acquisition succeeds
        self.mock_locks.tellers_sem.acquire.return_value = True
        
        # Patch the process creation to prevent actual process start
        with patch.object(self.dispatcher, '_start_process_for_turn', return_value=True):
            success = self.dispatcher._assign_handler(test_turn)
            
            # Verify the results
            self.assertTrue(success)
            mock_teller.assign_turn.assert_called_once_with(test_turn)  # Should be called exactly once
            self.mock_locks.tellers_sem.acquire.assert_called_once()
            
    def test_assign_handler_advisor_turn(self):
        """Prueba la asignación de un turno a un asesor"""
        test_turn = self._create_advisor_turn()
        
        # Create a more complete mock advisor
        mock_advisor = MagicMock(spec=Advisor)  # Use the actual Advisor class as spec
        mock_advisor.current_turn = None
        mock_advisor.advisor_id = "A1"
        mock_advisor.assign_turn = MagicMock()
        mock_advisor.complete_turn = MagicMock()
        
        # Replace the entire advisors list
        self.dispatcher.advisors = [mock_advisor]
        
        # Ensure semaphore acquisition succeeds
        self.mock_locks.advisors_sem.acquire.return_value = True
        
        # Patch the process creation
        with patch.object(self.dispatcher, '_start_process_for_turn', return_value=True):
            success = self.dispatcher._assign_handler(test_turn)
            
            # Verify the results
            self.assertTrue(success)
            mock_advisor.assign_turn.assert_called_once_with(test_turn)
            self.mock_locks.advisors_sem.acquire.assert_called_once()
            
    def test_assign_handler_no_available(self):
        """Prueba cuando no hay handlers disponibles"""
        test_turn = self._create_teller_turn()
        
        mock_teller = MagicMock()
        mock_teller.current_turn = "ocupado"
        self.dispatcher.tellers = [mock_teller]
        
        self.mock_locks.tellers_sem.acquire.return_value = True
        
        success = self.dispatcher._assign_handler(test_turn)
        self.assertFalse(success)
        
    def test_prepare_monetary_operation(self):
        """Prueba la preparación de operaciones monetarias"""
        mock_handler = MagicMock()
        mock_handler.deposit = MagicMock()
        
        # Cambiar para usar diccionario en lugar de Operation
        op_data = {'type': 'deposit', 'account_number': 'ACC123', 'amount': 100.0}
        
        operation = self.dispatcher._prepare_monetary_operation(mock_handler, op_data)
        self.assertIsNotNone(operation)
        
        # Verificar que se creó un partial con los parámetros correctos
        self.assertEqual(operation.func, mock_handler.deposit)
        self.assertEqual(operation.keywords, {'account_number': 'ACC123', 'amount': 100.0})
        
    def test_stop_dispatcher(self):
        """Prueba que el dispatcher se detiene correctamente"""
        self.dispatcher.stop()
        self.assertFalse(self.dispatcher._running.is_set())
        
    @patch('multiprocessing.Process')
    def test_start_process_for_turn(self, mock_process):
        """Prueba el inicio de un proceso para un turno"""
        test_turn = self._create_teller_turn()
        mock_handler = MagicMock()
        mock_handler.teller_id = "T1"
        mock_handler.deposit = MagicMock()
        
        # Configurar operaciones preparadas
        with patch.object(self.dispatcher, '_prepare_operations', 
                         return_value=[partial(mock_handler.deposit, account_number='ACC123', amount=100)]):
            success = self.dispatcher._start_process_for_turn(test_turn, mock_handler, "teller")
            self.assertTrue(success)
            mock_process.assert_called_once()
            mock_process.return_value.start.assert_called_once()
            
    def test_dispatch_processes_stop_condition(self):
        """Prueba que el loop de dispatch se detiene cuando _running está desactivado"""
        self.dispatcher._running.clear()
        
        with patch('time.sleep') as mock_sleep:
            self.dispatcher.dispatch_processes()
            mock_sleep.assert_not_called()

    def test_turn_service_type_detection(self):
        """Prueba que el dispatcher detecta correctamente el tipo de servicio requerido"""
        teller_turn = self._create_teller_turn()
        advisor_turn = self._create_advisor_turn()
        
        self.assertFalse(teller_turn.requires_advisor)
        self.assertTrue(advisor_turn.requires_advisor,
                    f"Expected requires_advisor=True for {advisor_turn.operations[0].type}")

if __name__ == '__main__':
    unittest.main()