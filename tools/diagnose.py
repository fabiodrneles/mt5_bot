import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

def run_diagnose():
    print("="*40)
    print("  DIAGNOSTICO RAPIDO DO MT5BOT  ")
    print("="*40)
    
    # 1. Tentar conectar ao MT5
    try:
        import MetaTrader5 as mt5
        if not mt5.initialize():
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
        
    # 2. Ler ultimas 24h de logs buscando ERROR
    log_file = Path("logs/bot.log")
    errors = 0
    if log_file.exists():
        cutoff = datetime.now() - timedelta(hours=24)
        cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M")
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                if "ERROR" in line and cutoff_str <= line[:16]:
                    errors += 1
    
    print(f"Erros nas ultimas 24h (bot.log): {errors}")
    
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
