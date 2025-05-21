import heapq
from typing import Dict, Optional
from core.turn import Turn, TurnStatus
import os

class TurnManager:
    def __init__(self, event_console=None):
        self.priority_queue = []
        self.active_turns = set()  # solo turnos que ya fueron despachados
        self.event_console = event_console
        
    def add_turn(self, turn: Turn):
        """Agrega un nuevo turno a la cola de prioridad"""
        heapq.heappush(self.priority_queue, (turn.priority, turn.created_at, turn))
        
        if self.event_console:
            self.event_console.add_event(
                os.getpid(),
                "TURN_ADDED",
                f"Turn {turn.turn_id} (Priority: {turn.priority}) added to queue",
                "info"
            )
            
    def get_next_turn(self) -> Optional[Turn]:
        """Obtiene el siguiente turno según prioridad"""
        if not self.priority_queue:
            return None

        _, _, turn = heapq.heappop(self.priority_queue)
        self.active_turns.add(turn.turn_id)  # se marca como activo aquí
        return turn
        
    def update_turn_status(self, turn_id: str, status: TurnStatus):
        """Actualiza el estado de un turno activo"""
        if turn_id in self.active_turns and status == TurnStatus.COMPLETED:
            self.active_turns.remove(turn_id)
            
            if self.event_console:
                self.event_console.add_event(
                    os.getpid(),
                    "TURN_COMPLETED",
                    f"Turn {turn_id} completed and removed from active turns",
                    "info"
                )

    def cleanup_completed_turns(self):
        """Elimina turnos completados antiguos"""
        initial_count = len(self.priority_queue)
        self.priority_queue = [
            (priority, created_at, turn) 
            for (priority, created_at, turn) in self.priority_queue
            if turn.turn_id not in self.active_turns  # solo quedan turnos no activos
        ]
        heapq.heapify(self.priority_queue)
        
        if self.event_console and initial_count != len(self.priority_queue):
            removed = initial_count - len(self.priority_queue)
            self.event_console.add_event(
                os.getpid(),
                "TURN_CLEANUP",
                f"Removed {removed} completed turns from queue",
                "info"
            )

    def get_stats(self) -> Dict:
        stats = {
            "pending": len(self.priority_queue),
            "in_progress": len(self.active_turns)
        }
        
        if self.event_console:
            self.event_console.add_event(
                os.getpid(),
                "TURN_STATS",
                f"Turn stats - Pending: {stats['pending']}, In Progress: {stats['in_progress']}",
                "debug"
            )
            
        return stats

    @property
    def has_pending_turns(self) -> bool:
        has_turns = len(self.priority_queue) > 0
        
        if self.event_console and not has_turns:
            self.event_console.add_event(
                os.getpid(),
                "QUEUE_EMPTY",
                "No pending turns in queue",
                "info"
            )
            
        return has_turns
