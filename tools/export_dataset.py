import os
import json
import csv
from pathlib import Path

def flatten_dict(d, parent_key='', sep='_'):
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def export_dataset():
    appdata = os.environ.get('APPDATA', '')
    if not appdata:
        print("Erro: Variável de ambiente APPDATA não encontrada.")
        return

    data_dir = Path(appdata) / "mt5bot"
    trades_file = data_dir / "virtual_trades.json"

    if not trades_file.exists():
        print(f"Erro: Arquivo {trades_file} não encontrado.")
        return

    print(f"Lendo trades de: {trades_file}")
    with open(trades_file, 'r', encoding='utf-8') as f:
        try:
            trades = json.load(f)
        except json.JSONDecodeError:
            print("Erro ao decodificar JSON.")
            return

    dataset = []
    
    for trade in trades:
        # Pular trades que ainda estão abertos (sem result final definido)
        if trade.get('result') not in ['win', 'loss', 'breakeven']:
            continue
            
        # Pegar metadados básicos
        # Convertemos win para 1, loss para 0 (breakeven vamos considerar como 0 ou ignorar)
        result_label = 1 if trade.get('result') == 'win' else 0
        
        row = {
            'symbol': trade.get('symbol', ''),
            'side': trade.get('side', ''),
            'setup': trade.get('setup', ''),
            'result': result_label,
            'result_raw': trade.get('result', ''),
            'pnl_pips': trade.get('pnl_pips', 0.0),
        }
        
        # Achatar o ml_context inteiro
        ml_context = trade.get('ml_context', {})
        if not ml_context:
            continue # Pular dados antigos que não tinham ml_context
            
        flat_context = flatten_dict(ml_context)
        row.update(flat_context)
        dataset.append(row)
        
    if not dataset:
        print("Nenhum dado com ml_context encontrado para exportar.")
        return
        
    headers = set()
    for row in dataset:
        headers.update(row.keys())
        
    headers_list = list(headers)
    
    priority = ['symbol', 'side', 'setup', 'result', 'result_raw', 'pnl_pips']
    final_headers = []
    for p in priority:
        if p in headers_list:
            final_headers.append(p)
            headers_list.remove(p)
            
    final_headers.extend(sorted(headers_list))

    # Cria pasta data na raiz do projeto (caminho atual)
    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "dataset.csv"
    
    print(f"Exportando {len(dataset)} registros para {output_file}...")
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=final_headers)
        writer.writeheader()
        writer.writerows(dataset)
        
    print("Exportação concluída com sucesso!")

if __name__ == "__main__":
    export_dataset()
