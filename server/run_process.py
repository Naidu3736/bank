from multiprocessing import Process
from core.turn import Turn
import time

def run_process(turn: Turn, operations, time_slice=0.1):
    """Ejecuta procesos con algoritmo round-robin"""
    active_processes = []
    
    try:
        # Iniciar todos los procesos primero
        for op in operations:
            p = Process(target=op)
            p.start()
            active_processes.append(p)
        
        # Implementación round-robin
        while active_processes:
            for p in list(active_processes):  # Copia para iteración segura
                if not p.is_alive():
                    active_processes.remove(p)
                    continue
                
                # Pequeña pausa para simular time slice
                time.sleep(time_slice)
                
                # En multiprocessing no podemos preemptar realmente,
                # esto es más un enfoque cooperativo
                
    except KeyboardInterrupt:
        for p in active_processes:
            p.terminate()
    
    # Limpieza final
    for p in active_processes:
        p.join()
        
    # Marcar turno como atendido
    turn.mark_as_attended()