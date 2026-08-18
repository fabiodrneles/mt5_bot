import json
from pathlib import Path

def run_show_positions():
    print("="*60)
    print("             POSICOES E ESTADO DO MT5BOT             ")
    print("="*60)
    
    # Posições reais
    state_file = Path("data/mt5bot_state.json")
    open_reais = 0
    detalhes_reais = ""
    if state_file.exists():
        try:
            with open(state_file, "r") as f:
                state = json.load(f)
            posicoes = state.get("open_positions", {})
            open_reais = len(posicoes)
            for sym, pos in posicoes.items():
                detalhes_reais += f" [{sym} {pos.get('side', '')} | Preço: {pos.get('entry_price', 0)}]"
        except Exception as e:
            detalhes_reais = f" (Erro lendo state: {e})"
            
    # Paper / Fantasmas
    paper_file = Path("data/paper_tracker/virtual_trades.json")
    fantasmas = 0
    if paper_file.exists():
        try:
            with open(paper_file, "r") as f:
                virtual_trades = json.load(f)
            fantasmas = len(virtual_trades)
        except:
            pass
            
    print(f"Posicoes Reais Abertas: {open_reais}{detalhes_reais}")
    print(f"Operacoes Fantasmas Guardadas (Paper): {fantasmas}")
    print("="*60)

if __name__ == "__main__":
    run_show_positions()
