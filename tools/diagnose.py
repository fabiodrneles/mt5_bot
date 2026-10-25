import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mt5bot.core import paths  # noqa: E402
from mt5bot.core import terminal  # noqa: E402

def count_recent_errors(hours=24):
    """Conta linhas ERROR/CRITICAL dos logs modificados nas ultimas `hours` horas."""
    import glob
    import time
    cutoff = time.time() - hours * 3600
    total = 0
    for log in glob.glob(os.path.join(paths.logs_dir(), "*.log")):
        if os.path.getmtime(log) < cutoff:
            continue
        with open(log, "r", encoding="utf-8", errors="replace") as f:
            total += sum(1 for line in f if "ERROR" in line or "CRITICAL" in line)
    return total


def run_diagnose():
    print("="*40)
    print("  DIAGNOSTICO RAPIDO DO MT5BOT  ")
    print("="*40)
    
    # 1. Tentar conectar ao MT5
    try:
        import MetaTrader5 as mt5
        if not terminal.initialize():
            print("MT5: DESCONECTADO (Erro de inicializacao)")
        else:
            acc = mt5.account_info()
            if acc:
                print(f"MT5: Conectado | Saldo: ${acc.balance:.2f} | Margem Livre: ${acc.margin_free:.2f}")
            else:
                print("MT5: Conectado (sem info de conta)")
            mt5.shutdown()
    except Exception as e:
        print(f"MT5: Erro ({e})")
        
    # 2. Erros nas ultimas 24h em todos os logs da pasta de dados
    errors = count_recent_errors()
    print(f"Erros nas ultimas 24h (logs em {paths.logs_dir()}): {errors}")
    
    # 3. Ler o estado atual
    state_file = Path("data/mt5bot_state.json")
    if state_file.exists():
        try:
            with open(state_file, "r") as f:
                state = json.load(f)
            open_pos = len(state.get("open_positions", {}))
            print(f"Posicoes Reais Abertas: {open_pos}")
        except:
            print("Posicoes Reais Abertas: ? (Erro ao ler state)")
            
    print("="*40)

if __name__ == "__main__":
    run_diagnose()
