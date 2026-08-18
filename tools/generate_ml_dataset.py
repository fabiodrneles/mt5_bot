import argparse
import sys
import pandas as pd
import numpy as np
import MetaTrader5 as mt5
from datetime import datetime
from pathlib import Path

# Adiciona o caminho principal para os imports do mt5bot funcionarem
sys.path.append(str(Path(__file__).parent.parent))
from mt5bot.engine.indicators import add_all_indicators

def get_historical_data(symbol, timeframe, count):
    while count >= 5000:
        print(f"Baixando {count} candles de {symbol}...")
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
        if rates is not None and len(rates) > 0:
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            return df
        print("Corretora não tem histórico suficiente. Reduzindo count...")
        count -= 10000
    
    print("Nenhum dado retornado do MT5 após tentativas.")
    return None

def generate_dataset(df, symbol):
    print("Calculando indicadores matemáticos...")
    df = add_all_indicators(df)
    
    # Criar colunas de microestrutura (body_size, wicks)
    df['body_size'] = abs(df['close'] - df['open']) / df['atr']
    df['upper_wick'] = (df['high'] - df[['close', 'open']].max(axis=1)) / df['atr']
    df['lower_wick'] = (df[['close', 'open']].min(axis=1) - df['low']) / df['atr']
    
    # Distâncias relativas
    df['dist_ema9'] = (df['close'] - df['ema9']) / df['ema9']
    df['dist_sma21'] = (df['close'] - df['sma21']) / df['sma21']
    df['dist_sma200'] = (df['close'] - df['sma200']) / df['sma200']
    if 'vwap' in df.columns:
        df['dist_vwap'] = (df['close'] - df['vwap']) / df['vwap']
    else:
        df['dist_vwap'] = 0.0
    
    # Largura de bollinger (Bandwidth) absoluto (como no backtest.py) e normalizado
    if 'bollinger_upper' in df.columns and 'bollinger_lower' in df.columns and 'bollinger_mid' in df.columns:
        df['bb_width_abs'] = df['bollinger_upper'] - df['bollinger_lower']
        df['bollinger_bandwidth'] = df['bb_width_abs'] / df['bollinger_mid']
    else:
        df['bb_width_abs'] = 0.0
        df['bollinger_bandwidth'] = 0.0

    print("Varrendo histórico e simulando entradas via StrategyScorer...")
    dataset = []
    
    from mt5bot.engine.strategy import StrategyScorer
    from mt5bot.engine.scoring import aplicar_scoring

    info = mt5.symbol_info(symbol)
    tick_size = info.trade_tick_size if info and info.trade_tick_size > 0 else (info.point if info else 0.01)
    
    for i in range(250, len(df) - 50):
        # Passa um sub-dataframe das últimas 10 velas para o motor
        sub_df = df.iloc[i-10:i+1]
        
        setups_found, _ = StrategyScorer.evaluate_all(sub_df, tick_size=tick_size, tick_offset=1, symbol=symbol)
        
        if not setups_found:
            continue
            
        # Aplica o scoring para gerar targets (ex: 1x risco) se o setup não tiver
        setups_found = aplicar_scoring(setups_found, sub_df)
        if not setups_found:
            continue
            
        best_setup = setups_found[0]
        
        entry_price = best_setup['trigger_price']
        side = str(best_setup['action']).upper()
        sl = best_setup['stop_loss']
        tp = best_setup.get('target')
        
        if tp is None:
            continue
        
        row = sub_df.iloc[-1]
        setup_name = best_setup['setup']
        
        # Forward Tracking: 50 candles no futuro
        result = -1 
        pnl_pips = 0.0
        
        for j in range(i+1, i+50):
            future = df.iloc[j]
            
            if side == 'BUY':
                if future['low'] <= sl:
                    result = 0
                    pnl_pips = sl - entry_price
                    break
                elif future['high'] >= tp:
                    result = 1
                    pnl_pips = tp - entry_price
                    break
            else:
                if future['high'] >= sl:
                    result = 0
                    pnl_pips = entry_price - sl
                    break
                elif future['low'] <= tp:
                    result = 1
                    pnl_pips = entry_price - tp
                    break
                    
        if result == -1:
            continue 
            
        data_row = {
            'symbol': symbol,
            'side': side,
            'setup': 'Russian',
            'result': result,
            'pnl_pips': pnl_pips,
            'body_size': row['body_size'],
            'upper_wick': row['upper_wick'],
            'lower_wick': row['lower_wick'],
            'adx': row.get('adx', 0.0),
            'z_score': row.get('z_score', 0.0),
            'atr': row.get('atr', 0.0),
            'rsi14': row.get('rsi14', 0.0),
            'bollinger_bandwidth': row['bollinger_bandwidth'],
            'dist_ema9': row['dist_ema9'],
            'dist_sma21': row['dist_sma21'],
            'dist_sma200': row['dist_sma200'],
            'dist_vwap': row['dist_vwap'],
            'hour': row['time'].hour,
            'day_of_week': row['time'].dayofweek
        }
        
        is_clean = True
        for k, v in data_row.items():
            if pd.isna(v):
                is_clean = False
                break
        
        if is_clean:
            dataset.append(data_row)
            
    return dataset

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", type=str, default="HK50", help="Símbolo a ser baixado")
    parser.add_argument("--tf", type=str, default="M5", help="Timeframe (ex: H1, M5, M15)")
    parser.add_argument("--count", type=int, default=100000, help="Número de candles para baixar")
    args = parser.parse_args()

    if not mt5.initialize():
        print("Falha ao inicializar o MT5")
        sys.exit(1)
        
    tf_map = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1
    }
    mt5_tf = tf_map.get(args.tf, mt5.TIMEFRAME_M5)
    
    df = get_historical_data(args.symbol, mt5_tf, args.count)
    if df is None:
        mt5.shutdown()
        sys.exit(1)
        
    dataset = generate_dataset(df, args.symbol)
    
    if len(dataset) > 0:
        out_df = pd.DataFrame(dataset)
        
        out_dir = Path("data")
        out_dir.mkdir(exist_ok=True)
        
        out_file = out_dir / "dataset_massive.csv"
        out_df.to_csv(out_file, index=False)
        print(f"\nSucesso! Foram geradas {len(dataset)} operações (features e labels).")
        print(f"Salvo em: {out_file}")
        
        wins = out_df['result'].sum()
        losses = len(out_df) - wins
        print("\n=== DISTRIBUIÇÃO DO DATASET ===")
        print(f"Vitórias (1): {wins} ({(wins/len(out_df))*100:.1f}%)")
        print(f"Derrotas (0): {losses} ({(losses/len(out_df))*100:.1f}%)")
    else:
        print("Nenhuma operação pôde ser extraída dos dados.")

    mt5.shutdown()

if __name__ == "__main__":
    main()
