import multiprocessing
from event_logger import ProcessTracker
import os

def run_process(parent_pid, turn, operations, manager=None):
    """Versión mejorada con mejor tracking"""
    tracker = ProcessTracker(manager)
    
    try:
        current_pid = os.getpid()
        # Registrar inicio con más detalle
        tracker.update_process(
            pid=current_pid,
            state="running",
            current_operation=f"Processing turn {turn.turn_id} with {len(operations)} ops",
            ppid=parent_pid
        )
        
        # Ejecutar operaciones con tracking
        results = []
        for i, op in enumerate(operations):
            tracker.update_process(
                pid=current_pid,
                current_operation=f"Executing op {i+1}/{len(operations)}: {op.__name__}"
            )
            results.append(op())
        
        if all(results):
            turn.mark_as_attended()
        else:
            turn.mark_as_failed()
            
    except Exception as e:
        tracker.update_process(
            pid=current_pid,
            state="error",
            current_operation=f"Failed: {str(e)}"
        )
        turn.mark_as_failed()

def _execute_operation(op):
    """Función auxiliar para ejecutar una operación."""
    pid = os.getpid()
    try:
        ProcessTracker.update_process(
            pid,
            state="running",
            current_operation="Executing bank operation"
        )
        return op()
    except Exception as e:
        EventConsole.add_event(
            pid,
            "OPERATION_ERROR",
            f"Operation failed: {str(e)}",
            "error"
        )
        return False