"""bot.bat tail: ultimas 15 linhas do log mais recente (pasta de dados do usuario)."""
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mt5bot.core import paths  # noqa: E402


def latest_log():
    logs = glob.glob(os.path.join(paths.logs_dir(), "*.log"))
    return max(logs, key=os.path.getmtime) if logs else None


def run_tail_logs(n=15):
    print("=" * 60)
    print("                LEITURA CIRURGICA DE LOGS                ")
    print("=" * 60)
    log_file = latest_log()
    if not log_file:
        print(f"Nenhum log ainda em {paths.logs_dir()}")
        return
    with open(log_file, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    print(f"{log_file} (ultimas {min(n, len(lines))} de {len(lines)} linhas)")
    print("-" * 60)
    for line in lines[-n:]:
        print(line.rstrip())
    print("=" * 60)


if __name__ == "__main__":
    run_tail_logs()
