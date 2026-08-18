import json
from pathlib import Path
from datetime import datetime, timedelta

def run_show_performance():
    print("="*60)
    print("             RESUMO FINANCEIRO (ULTIMOS 7 DIAS)             ")
    print("="*60)
    
    hist_file = Path("data/mt5bot_history.json")
    if not hist_file.exists():
        print("Nenhum historico de trades encontrado.")
        return
        
    try:
        with open(hist_file, "r") as f:
            history = json.load(f)
            
        cutoff = datetime.now() - timedelta(days=7)
        trades_semana = []
        
        for trade in history:
            # Pega exit_time ou fall-back entry_time
            dt_str = trade.get("exit_time") or trade.get("entry_time")
            if dt_str:
                try:
                    dt = datetime.strptime(dt_str[:16], "%Y-%m-%d %H:%M")
                    if dt >= cutoff:
                        trades_semana.append(trade)
                except:
                    pass
                    
        total = len(trades_semana)
        if total == 0:
            print("Nenhum trade nos ultimos 7 dias.")
        else:
            wins = sum(1 for t in trades_semana if t.get("profit", 0) > 0)
            lucro_liquido = sum(t.get("profit", 0) for t in trades_semana)
            win_rate = (wins / total) * 100
            
            print(f"Trades Realizados: {total}")
            print(f"Vitorias: {wins} ({win_rate:.1f}%)")
            print(f"Lucro Liquido: ${lucro_liquido:.2f}")
            
    except Exception as e:
        print(f"Erro ao ler historico: {e}")
        
    print("="*60)

if __name__ == "__main__":
    run_show_performance()
