import os, json
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime

# Conectar ao MT5
if not mt5.initialize():
    print('Falha ao conectar ao MT5')
    exit()

f = os.path.expandvars('%APPDATA%/mt5bot/virtual_rejections.json')
if not os.path.exists(f):
    print('Sem arquivo de rejeicoes')
    mt5.shutdown()
    exit()

data = json.load(open(f))
rvol_rejections = [d for d in data if d.get('reason') == 'RVOL']

print(f'Total de rejeicoes por RVOL hoje: {len(rvol_rejections)}')

wins = 0
losses = 0

for r in rvol_rejections:
    symbol = r['symbol']
    side = r['side']
    entry_price = float(r['entry_price'])
    sl = float(r['sl_price'])
    # Estimando alvo 1:1
    dist = abs(entry_price - sl)
    if side == 'BUY':
        tp = entry_price + dist
    else:
        tp = entry_price - dist
    
    # Pegar tempo
    try:
        dt_str = r['time'].split('.')[0].replace('+00:00', '').replace('Z', '')
        dt_obj = datetime.strptime(dt_str, '%Y-%m-%dT%H:%M:%S')
        rates = mt5.copy_rates_from(symbol, mt5.TIMEFRAME_M1, dt_obj, 300)
    except:
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 300)
        
    if rates is None or len(rates) == 0:
        print(f"Sem dados para {symbol}")
        continue
        
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    result = 'PENDING (Nao atingiu Alvo nem Stop)'
    
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
                
    print(f"[{symbol}] {side} Entrada: {entry_price:.5f} SL: {sl:.5f} TP: {tp:.5f} -> {result}")
    if result == 'WIN': wins += 1
    elif result == 'LOSS': losses += 1

print(f'\\n>> Placar Estimado (se RVOL fosse brando): {wins} WINS x {losses} LOSSES')
mt5.shutdown()
