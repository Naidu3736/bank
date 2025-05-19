import heapq
from core.turn import Turn

class TurnManager:
    def __init__(self):
        self.priority_queue = []
        self.active_turns = set()
        
    def add_turn(self, turn: Turn):
        """Agrega un nuevo turno a la cola de prioridad"""
        heapq.heappush(self.priority_queue, (turn.priority, turn))
        self.active_turns.add(turn.turn_id)
        
    def get_next_turn(self):
        """Obtiene el siguiente turno según prioridad"""
        if self.priority_queue:
            _, turn = heapq.heappop(self.priority_queue)
            return turn
        return None
        
    def is_turn_active(self, turn_id):
        """Verifica si un turno está en la cola"""
        return turn_id in self.active_turns
        
    def remove_turn(self, turn_id):
        """Elimina un turno de los activos"""
        if turn_id in self.active_turns:
            self.active_turns.remove(turn_id)

    @property
    def has_pending_turns(self) -> bool:
        return len(self.priority_queue) > 0