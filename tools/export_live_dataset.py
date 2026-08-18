import sys
import os
import json
import argparse
import pandas as pd

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

def get_trades_file():
    appdata = os.getenv('APPDATA') or os.path.join(os.path.expanduser('~'))
    fpath = os.path.join(appdata, 'mt5bot', 'virtual_trades.json')
    if not os.path.exists(fpath):
        fpath = os.path.join(os.path.expanduser('~'), '.mt5bot', 'virtual_trades.json')
    if not os.path.exists(fpath):
        fpath = os.path.join(_ROOT, 'mt5bot', 'data', 'virtual_trades.json')
    return fpath

def export_live_dataset(symbol=None):
    fpath = get_trades_file()
    if not os.path.exists(fpath):
        print(f"Arquivo virtual_trades.json não encontrado em {fpath}")
        return

    with open(fpath, "r", encoding="utf-8") as f:
        try:
            trades = json.load(f)
        except json.JSONDecodeError:
            print(f"Erro ao ler JSON de {fpath}")
            return
            
    dataset = []
    
    for trade in trades:
        # Apenas trades fechados
        if trade.get("result") == "open" or not trade.get("exit_time"):
            continue
            
        # Filtro por símbolo
        if symbol and trade.get("symbol") != symbol:
            continue
            
        ml_ctx = trade.get("ml_context")
        if not ml_ctx:
            continue
            
        # Determinar a label real (result) a partir do futuro do mercado (trade)
        # 1 = Win, 0 = Loss
        result_label = 1 if trade.get("result") == "win" else 0
        
        # O ml_context já tem as colunas, vamos nivelá-las
        data_row = {
            'time': trade.get('entry_time'),
            'side': trade.get('side'),
            'setup': trade.get('setup'),
            'result': result_label,
            'pnl_pips': trade.get('pnl_pips', 0.0),
            'is_vetoed': trade.get('is_vetoed', False),
            'veto_reason': trade.get('veto_reason', "")
        }
        
        # features 
        for k, v in ml_ctx.items():
            if isinstance(v, (int, float, str, bool)):
                data_row[k] = v
                
        dataset.append(data_row)
        
    if not dataset:
        print("Nenhum dado válido com ml_context encontrado.")
        return
        
    df = pd.DataFrame(dataset)
    
    # Remover entradas nulas
    df = df.dropna()
    
    sym_suffix = f"_{symbol}" if symbol else ""
    out_file = os.path.join(_ROOT, f"dataset_live_experience{sym_suffix}.csv")
    df.to_csv(out_file, index=False)
    
    print(f"[SUCCESS] Dataset de experiência ao vivo gerado: {out_file}")
    print(f"Total de trades (Ghost + Reais): {len(df)}")
    
    vetos = df[df['is_vetoed'] == True]
    print(f"Fantasmas (Vetados pela IA e Rastreados): {len(vetos)}")
    if len(vetos) > 0:
        wins_fantasmas = len(vetos[vetos['result'] == 1])
        print(f"   -> Desses vetados, {wins_fantasmas} deram WIN (IA perdeu oportunidade)")
        losses_fantasmas = len(vetos) - wins_fantasmas
        print(f"   -> Desses vetados, {losses_fantasmas} deram LOSS (IA salvou a banca)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", type=str, default=None, help="Símbolo a ser extraído (ex: HK50, WIN)")
    args = parser.parse_args()
    
    export_live_dataset(args.symbol)
