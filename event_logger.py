import os
from datetime import datetime
from typing import List, Dict
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
import multiprocessing
import time

class EventConsole:
    def __init__(self, log_dir="logs"):
        self.console = Console()
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.log_file = self.log_dir / f"bank_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        self._manager = multiprocessing.Manager()
        self._events = self._manager.list()
        self._lock = multiprocessing.Lock()
        
    def add_event(self, pid: int, operation: str, details: str, status: str = "info"):
        timestamp = datetime.now().strftime("%H:%M:%S,%f")[:-3]
        event_data = {
            'timestamp': timestamp,
            'pid': pid,
            'operation': operation,
            'details': details,
            'status': status.lower()
        }
        
        with self._lock:
            # Guardar en archivo
            self._save_to_file(event_data)
            
            # Mantener en memoria para la UI (últimos 50 eventos)
            if len(self._events) >= 50:
                self._events.pop()
            self._events.insert(0, event_data)
    
    def _save_to_file(self, event_data):
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event_data) + '\n')
        except Exception as e:
            self.console.print(f"[red]Error guardando log: {str(e)}[/]")
    
    def get_events(self, limit=15):
        with self._lock:
            return list(self._events[:limit])

class ProcessTracker:
    def __init__(self):
        self._manager = multiprocessing.Manager()
        self._processes = self._manager.dict()
        self._locks = self._manager.dict()
        self._lock = multiprocessing.Lock()
        
    def update_process(self, pid: int, **kwargs):
        """Actualiza la información de un proceso.
        
        Args:
            pid: ID del proceso
            kwargs: Puede incluir:
                - state: estado del proceso
                - current_operation: operación actual
                - lock_held: lock adquirido (opcional)
                - lock_waiting: lock esperando (opcional)
                - ppid: ID del proceso padre (opcional)
        """
        with self._lock:
            if pid not in self._processes:
                self._processes[pid] = self._manager.dict({
                    'start_time': time.time(),
                    'state': 'new',
                    'current_operation': '',
                    'lock_held': None,
                    'lock_waiting': None,
                    'ppid': os.getppid()
                })
            
            # Actualizar solo los campos proporcionados
            for key, value in kwargs.items():
                if key in ['state', 'current_operation', 'ppid']:
                    self._processes[pid][key] = value
                elif key == 'lock_held':
                    self._processes[pid]['lock_held'] = value if value else None
                elif key == 'lock_waiting':
                    self._processes[pid]['lock_waiting'] = value if value else None
    
    def update_lock(self, lock_name: str, owner_pid: int = None, state: str = None):
        with self._lock:
            if lock_name not in self._locks:
                self._locks[lock_name] = self._manager.dict({
                    'owner_pid': owner_pid or -1,
                    'state': state or 'free',
                    'acquired_time': time.time() if owner_pid else None
                })
            else:
                if owner_pid is not None:
                    self._locks[lock_name]['owner_pid'] = owner_pid
                    self._locks[lock_name]['acquired_time'] = time.time()
                if state is not None:
                    self._locks[lock_name]['state'] = state
    
    def get_processes(self):
        with self._lock:
            # Calcular uptime para cada proceso
            processes = []
            for pid, proc in self._processes.items():
                uptime = time.time() - proc['start_time']
                processes.append({
                    'pid': pid,
                    'ppid': proc['ppid'],
                    'state': proc['state'],
                    'current_operation': proc['current_operation'],
                    'lock_held': proc['lock_held'],
                    'lock_waiting': proc['lock_waiting'],
                    'uptime': f"{uptime:.2f}s"
                })
            return processes
    
    def get_locks(self):
        with self._lock:
            locks = {}
            for name, lock in self._locks.items():
                locks[name] = {
                    'owner_pid': lock['owner_pid'],
                    'state': lock['state'],
                    'acquired_time': lock.get('acquired_time')
                }
            return locks

class BankMonitor:
    def __init__(self, event_console: EventConsole, process_tracker: ProcessTracker):
        self.console = Console()
        self.event_console = event_console
        self.process_tracker = process_tracker
        self.running = True
    
    def generate_process_table(self) -> Table:
        """Genera la tabla de procesos"""
        table = Table(title="Bank Processes", show_header=True, header_style="bold blue")
        table.add_column("PID", style="dim", width=8)
        table.add_column("PPID", style="dim", width=8)
        table.add_column("State", width=12)
        table.add_column("Current Operation", width=30)
        table.add_column("Lock Held", width=15)
        table.add_column("Lock Waiting", width=15)
        table.add_column("Uptime", width=10)
        
        processes = self.process_tracker.get_processes()
        for proc in processes:
            state_style = {
                'working': 'green',
                'waiting': 'yellow',
                'error': 'red'
            }.get(proc['state'].lower(), 'white')
            
            table.add_row(
                str(proc['pid']),
                str(proc['ppid']),
                f"[{state_style}]{proc['state']}[/]",
                proc['current_operation'],
                proc['lock_held'] or '-',
                proc['lock_waiting'] or '-',
                proc['uptime']
            )
        return table
    
    def generate_locks_table(self) -> Table:
        """Genera la tabla de locks"""
        table = Table(title="Bank Locks Status", show_header=True, header_style="bold blue")
        table.add_column("Lock Name", width=20)
        table.add_column("Owner PID", width=10)
        table.add_column("State", width=12)
        table.add_column("Held For", width=10)
        
        locks = self.process_tracker.get_locks()
        for name, lock in locks.items():
            state_style = 'green' if lock['state'] == 'acquired' else 'yellow'
            held_for = "-"
            if lock['acquired_time']:
                held_for = f"{time.time() - lock['acquired_time']:.2f}s"
            
            table.add_row(
                name,
                str(lock['owner_pid']),
                f"[{state_style}]{lock['state']}[/]",
                held_for
            )
        return table
    
    def generate_events_table(self) -> Table:
        """Genera la tabla de eventos"""
        table = Table(title="Bank System Events", show_header=True, header_style="bold blue")
        table.add_column("Timestamp", width=12)
        table.add_column("PID", width=8)
        table.add_column("Operation", width=20)
        table.add_column("Details", width=40)
        
        events = self.event_console.get_events(15)
        for event in events:
            table.add_row(
                event['timestamp'],
                str(event['pid']),
                event['operation'],
                event['details']
            )
        return table
    
    def run(self):
        """Ejecuta la interfaz de monitoreo en la consola"""
        layout = Layout()
        layout.split(
            Layout(name="processes", size=10),
            Layout(name="locks", size=6),
            Layout(name="events", size=14)
        )
        
        with Live(layout, refresh_per_second=4, screen=True) as live:
            while self.running:
                try:
                    layout["processes"].update(Panel(self.generate_process_table()))
                    layout["locks"].update(Panel(self.generate_locks_table()))
                    layout["events"].update(Panel(self.generate_events_table()))
                    time.sleep(0.25)
                except KeyboardInterrupt:
                    self.running = False
                    break