def run_process(pid, turn, operations, handler, process_tracker=None):
    if process_tracker:
        process_tracker.update_process(pid, state="processing", current_operation=f"Procesando turno {turn.turn_id}", type=handler.__class__.__name__)
    try:
        for op in operations:
            try:
                # Aquí la operación llamará al método del handler, que actualiza el process_tracker con _track()
                print(f"[RUN] Ejecutando operación {op}")
                op()
            except Exception as e:
                print(f"[ERROR] Fallo en operación: {e}")
    finally:
        if process_tracker:
            process_tracker.update_process(pid, state="ready", current_operation="Operación completada", type=handler.__class__.__name__)
