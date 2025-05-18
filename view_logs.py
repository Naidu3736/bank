import json
from pathlib import Path

def view_logs(log_dir="logs"):
    log_dir = Path(log_dir)
    latest_log = sorted(log_dir.glob('bank_*.log'))[-1]
    
    print(f"\nMostrando logs de {latest_log.name}:\n")
    with open(latest_log, 'r', encoding='utf-8') as f:
        for line in f:
            log = json.loads(line)
            print(f"[{log['timestamp']}] [{log['level']}] {log['type']}: {log['message']}")

if __name__ == "__main__":
    view_logs()