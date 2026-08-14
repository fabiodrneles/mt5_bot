import os
import json
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
from collections import defaultdict

def main():
    if not mt5.initialize():
        print("❌ Falha ao conectar ao MT5")
        return

    f = os.path.expandvars('%APPDATA%/mt5bot/virtual_rejections.json')
    if not os.path.exists(f):
        print("❌ Arquivo de rejeições não encontrado.")
        mt5.shutdown()
        return

    try:
        with open(f, 'r') as file:
            data = json.load(file)
    except Exception as e:
        print(f"❌ Erro ao ler json: {e}")
        mt5.shutdown()
        return

    print(f"[+] Analisando {len(data)} trades rejeitados...")

    results_by_filter = defaultdict(lambda: {"wins": 0, "losses": 0, "pending": 0})

    for r in data:
        symbol = r.get('symbol')
        side = r.get('side')
        entry_price = r.get('entry_price')
        sl = r.get('sl_price')
        reason = r.get('reason', 'Unknown')
        time_str = r.get('time')
        
        if not all([symbol, side, entry_price, sl, time_str]):
            continue
            
        entry_price = float(entry_price)
        sl = float(sl)
        dist = abs(entry_price - sl)
        
        # Alvo padrão 1:1
        if side == 'BUY':
            tp = entry_price + dist
        else:
            tp = entry_price - dist
            
        # Parse time
        try:
            dt_str = time_str.split('.')[0].replace('+00:00', '').replace('Z', '')
            dt_obj = datetime.strptime(dt_str, '%Y-%m-%dT%H:%M:%S')
            rates = mt5.copy_rates_from(symbol, mt5.TIMEFRAME_M1, dt_obj, 500)
        except:
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 500)
            
        if rates is None or len(rates) == 0:
            results_by_filter[reason]["pending"] += 1
            continue
            
        df = pd.DataFrame(rates)
        
        result = 'PENDING'
        for _, row in df.iterrows():
            high = row['high']
            low = row['low']
            
            if side == 'BUY':
                if low <= sl:
                    result = 'LOSS'
                    break
                if high >= tp:
                    result = 'WIN'
                    break
            else:
                if high >= sl:
                    result = 'LOSS'
                    break
                if low <= tp:
                    result = 'WIN'
                    break
                    
        if result == 'WIN':
            results_by_filter[reason]["wins"] += 1
        elif result == 'LOSS':
            results_by_filter[reason]["losses"] += 1
        else:
            results_by_filter[reason]["pending"] += 1

    print("\n" + "="*50)
    print("[ RESULTADO DA SIMULACAO SE OS FILTROS FOSSEM DESLIGADOS ]")
    print("="*50)
    
    for reason, stats in results_by_filter.items():
        w = stats['wins']
        l = stats['losses']
        p = stats['pending']
        total = w + l
        wr = (w / total * 100) if total > 0 else 0.0
        
        print(f"\n[Filtro: {reason}]")
        print(f"   Trades Rejeitados Testados: {total + p}")
        print(f"   Desempenho (se o filtro nao existisse): {w} WINS x {l} LOSSES")
        print(f"   Win Rate: {wr:.1f}%")
        
        if wr < 50 and total > 0:
            print("   -> Veredito: O filtro funcionou muito bem e protegeu a conta!")
        elif wr >= 50 and total > 0:
            print("   -> Veredito: O filtro pode estar muito rigido. Bloqueou trades rentaveis.")
        else:
            print("   -> Veredito: Trades ainda estao em andamento ou sem liquidez.")

    print("\n" + "="*50)
    mt5.shutdown()

if __name__ == "__main__":
    main()
