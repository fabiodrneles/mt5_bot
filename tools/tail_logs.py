import os
from pathlib import Path

def run_tail_logs():
    print("="*60)
    print("                LEITURA CIRURGICA DE LOGS                ")
    print("="*60)
    
    log_file = Path("logs/bot.log")
    if not log_file.exists():
        print("Arquivo logs/bot.log não encontrado.")
        return
        
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        print(f"Lendo as últimas 15 linhas do log (Total: {len(lines)} linhas):")
        print("-" * 60)
        for line in lines[-15:]:
            print(line.strip())
            
    except Exception as e:
        print(f"Erro ao ler log: {e}")
        
    print("="*60)

if __name__ == "__main__":
    run_tail_logs()
