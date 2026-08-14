import MetaTrader5 as mt5
import pandas as pd
import numpy as np

def calculate_indicators(df):
    # Bollinger Bands
    window = 20
    rolling_mean = df['close'].rolling(window=window).mean()
    rolling_std = df['close'].rolling(window=window).std()
    df['bb_mid'] = rolling_mean
    df['bb_upper'] = rolling_mean + (rolling_std * 2)
    df['bb_lower'] = rolling_mean - (rolling_std * 2)
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # EMA 9
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    return df

def main():
    if not mt5.initialize():
        print("Failed to connect to MT5")
        return
        
    rates = mt5.copy_rates_from_pos('HK50', mt5.TIMEFRAME_M5, 0, 5000)
    if rates is None or len(rates) == 0:
        print("Failed to get data")
        return
        
    df = pd.DataFrame(rates)
    df = calculate_indicators(df)
    
    # SETUP 1: Russian Bollinger Bands Mean Reversion
    # Buy at Lower Band, Sell at Upper Band. Target: Mid Band. Stop: 100 points.
    bb_wins, bb_losses = 0, 0
    in_bb = False
    bb_side, bb_entry = 0, 0
    
    # SETUP 2: RSI Extremes Reversal
    # Buy when RSI drops below 30 and crosses back up. Sell above 70 and cross down.
    # Target: 50 points, Stop: 50 points (1:1)
    rsi_wins, rsi_losses = 0, 0
    in_rsi = False
    rsi_side, rsi_entry = 0, 0
    
    # SETUP 3: Trend Following (MME9) - Similar to our current 9.1
    # Buy when close > ema9, Sell when close < ema9 (simplified)
    # Target: 50, Stop: 50
    ema_wins, ema_losses = 0, 0
    in_ema = False
    ema_side, ema_entry = 0, 0

    for i in range(25, len(df)):
        row = df.iloc[i]
        prev_row = df.iloc[i-1]
        
        # --- BB Logic ---
        if not in_bb:
            if row['low'] < row['bb_lower']:
                in_bb = True
                bb_side = 1
                bb_entry = row['close']
            elif row['high'] > row['bb_upper']:
                in_bb = True
                bb_side = -1
                bb_entry = row['close']
        else:
            if bb_side == 1:
                if row['high'] >= row['bb_mid']: bb_wins += 1; in_bb = False
                elif row['low'] <= bb_entry - 100: bb_losses += 1; in_bb = False
            elif bb_side == -1:
                if row['low'] <= row['bb_mid']: bb_wins += 1; in_bb = False
                elif row['high'] >= bb_entry + 100: bb_losses += 1; in_bb = False
                
        # --- RSI Logic ---
        if not in_rsi:
            if prev_row['rsi'] < 30 and row['rsi'] >= 30:
                in_rsi = True; rsi_side = 1; rsi_entry = row['close']
            elif prev_row['rsi'] > 70 and row['rsi'] <= 70:
                in_rsi = True; rsi_side = -1; rsi_entry = row['close']
        else:
            if rsi_side == 1:
                if row['high'] >= rsi_entry + 50: rsi_wins += 1; in_rsi = False
                elif row['low'] <= rsi_entry - 50: rsi_losses += 1; in_rsi = False
            elif rsi_side == -1:
                if row['low'] <= rsi_entry - 50: rsi_wins += 1; in_rsi = False
                elif row['high'] >= rsi_entry + 50: rsi_losses += 1; in_rsi = False
                
        # --- EMA Logic ---
        if not in_ema:
            if prev_row['close'] < prev_row['ema9'] and row['close'] > row['ema9']:
                in_ema = True; ema_side = 1; ema_entry = row['close']
            elif prev_row['close'] > prev_row['ema9'] and row['close'] < row['ema9']:
                in_ema = True; ema_side = -1; ema_entry = row['close']
        else:
            if ema_side == 1:
                if row['high'] >= ema_entry + 50: ema_wins += 1; in_ema = False
                elif row['low'] <= ema_entry - 50: ema_losses += 1; in_ema = False
            elif ema_side == -1:
                if row['low'] <= ema_entry - 50: ema_wins += 1; in_ema = False
                elif row['high'] >= ema_entry + 50: ema_losses += 1; in_ema = False

    print("="*50)
    print("RESULTADO DO BACKTEST HK50 (5000 Candles M5 - Aprox 1 mes)")
    print("="*50)
    
    print(f"\n1. Setup Russo (Bollinger Bands Mean Reversion):")
    bb_total = bb_wins + bb_losses
    print(f"   WINS: {bb_wins} | LOSSES: {bb_losses}")
    print(f"   Win Rate: {(bb_wins/bb_total*100) if bb_total > 0 else 0:.1f}%")
    
    print(f"\n2. Setup Oscilador (RSI Reversao 30/70):")
    rsi_total = rsi_wins + rsi_losses
    print(f"   WINS: {rsi_wins} | LOSSES: {rsi_losses}")
    print(f"   Win Rate: {(rsi_wins/rsi_total*100) if rsi_total > 0 else 0:.1f}%")
    
    print(f"\n3. Setup Tendencia (Rompimento MME9 - O nosso atual):")
    ema_total = ema_wins + ema_losses
    print(f"   WINS: {ema_wins} | LOSSES: {ema_losses}")
    print(f"   Win Rate: {(ema_wins/ema_total*100) if ema_total > 0 else 0:.1f}%")
    print("="*50)
    
    mt5.shutdown()

if __name__ == '__main__':
    main()
