from multiprocessing import Pool
from core.turn import Turn
from event_logger import EventConsole, ProcessTracker
import os
import time

def run_process(turn: Turn, operations):
    """Ejecuta operaciones en paralelo con multiprocessing."""
    pid = os.getpid()
    ProcessTracker.update_process(
        pid,
        state="running",
        current_operation=f"Processing turn {turn.turn_id}"
    )
    
    start_time = time.time()
    results = []
    
    try:
        with Pool(processes=min(len(operations), 3)) as pool:
            for i, op in enumerate(operations):
                ProcessTracker.update_process(
                    pid,
                    state="running",
                    current_operation=f"Executing op {i+1}/{len(operations)}"
                )
                results.append(pool.apply_async(_execute_operation, (op,)))
            
            results = [r.get() for r in results]
            
        if all(results):
            turn.mark_as_attended()
            EventConsole.add_event(
                pid,
                "PROCESS_COMPLETE",
                f"Turn {turn.turn_id} completed successfully",
                "success"
            )
        else:
            turn.mark_as_failed()
            EventConsole.add_event(
                pid,
                "PROCESS_FAILED",
                f"Turn {turn.turn_id} failed",
                "error"
            )
            
    except Exception as e:
        EventConsole.add_event(
            pid,
            "PROCESS_ERROR",
            f"Error in turn {turn.turn_id}: {str(e)}",
            "error"
        )
        turn.mark_as_failed()
        
    finally:
        ProcessTracker.update_process(
            pid,
            state="completed",
            current_operation=f"Turn {turn.turn_id} processed in {time.time()-start_time:.2f}s"
        )

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