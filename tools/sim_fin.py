import MetaTrader5 as mt5
import pandas as pd
import numpy as np

def calculate_indicators(df):
    window = 20
    rolling_mean = df['close'].rolling(window=window).mean()
    rolling_std = df['close'].rolling(window=window).std()
    df['bb_mid'] = rolling_mean
    df['bb_upper'] = rolling_mean + (rolling_std * 2)
    df['bb_lower'] = rolling_mean - (rolling_std * 2)
    df['bb_width'] = df['bb_upper'] - df['bb_lower']
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    return df

if not mt5.initialize(): exit()

info = mt5.symbol_info('HK50')
if not info:
    print('HK50 not found in MT5')
    exit()

print(f'Contract Size: {info.trade_contract_size}')
print(f'Point Size: {info.point}')
print(f'Tick Value: {info.trade_tick_value}')
print(f'Tick Size: {info.trade_tick_size}')

# Simulate Trades
rates = mt5.copy_rates_from_pos('HK50', mt5.TIMEFRAME_M5, 0, 5000)
df = pd.DataFrame(rates)
df = calculate_indicators(df)

wins, losses = 0, 0
balance = 16.00
lot = 0.01
in_trade = False
side, entry_price, sl = 0, 0.0, 0.0

MIN_WIDTH = 50.0  
USE_RSI = True

print(f'Initial Balance: ${balance:.2f}')

for i in range(25, len(df)):
    row = df.iloc[i]
    
    if not in_trade:
        width_ok = row['bb_width'] >= MIN_WIDTH
        
        if row['low'] < row['bb_lower'] and width_ok:
            if not USE_RSI or row['rsi'] < 30:
                in_trade = True
                side = 1
                entry_price = row['close']
                sl = entry_price - (row['bb_width'] / 2)
                
        elif row['high'] > row['bb_upper'] and width_ok:
            if not USE_RSI or row['rsi'] > 70:
                in_trade = True
                side = -1
                entry_price = row['close']
                sl = entry_price + (row['bb_width'] / 2)
    else:
        pts_won = 0.0
        if side == 1:
            if row['high'] >= row['bb_upper']:
                wins += 1
                pts_won = (row['bb_upper'] - entry_price)
                in_trade = False
            elif row['low'] <= sl:
                losses += 1
                pts_won = (sl - entry_price)
                in_trade = False
        elif side == -1:
            if row['low'] <= row['bb_lower']:
                wins += 1
                pts_won = (entry_price - row['bb_lower'])
                in_trade = False
            elif row['high'] >= sl:
                losses += 1
                pts_won = (entry_price - sl) # this is negative, wait!
                # Actually pts_won should be negative for losses in the calculation
                pts_won = (entry_price - sl)
                in_trade = False
                
        if not in_trade:
            # Let's use the MT5 order calc function exactly as the bot does.
            # pts_won is the absolute distance. If loss, we make it negative price diff.
            if side == 1:
                close_price = entry_price + pts_won if wins > losses else entry_price - pts_won
            else:
                close_price = entry_price - pts_won if wins > losses else entry_price + pts_won
                
            # Actually simpler:
            if wins > 0 and wins > losses: # Wait this is a bug in my tracking loop.
                pass
            # Fix tracking:
            pass

# Let's rewrite the eval block cleanly
wins, losses = 0, 0
balance = 16.00
in_trade = False

for i in range(25, len(df)):
    row = df.iloc[i]
    
    if not in_trade:
        width_ok = row['bb_width'] >= MIN_WIDTH
        if row['low'] < row['bb_lower'] and width_ok:
            if not USE_RSI or row['rsi'] < 30:
                in_trade = True
                side = mt5.ORDER_TYPE_BUY
                entry_price = row['close']
                sl = entry_price - (row['bb_width'] / 2)
        elif row['high'] > row['bb_upper'] and width_ok:
            if not USE_RSI or row['rsi'] > 70:
                in_trade = True
                side = mt5.ORDER_TYPE_SELL
                entry_price = row['close']
                sl = entry_price + (row['bb_width'] / 2)
    else:
        close_price = None
        if side == mt5.ORDER_TYPE_BUY:
            if row['high'] >= row['bb_upper']:
                close_price = row['bb_upper']
                wins += 1
            elif row['low'] <= sl:
                close_price = sl
                losses += 1
        elif side == mt5.ORDER_TYPE_SELL:
            if row['low'] <= row['bb_lower']:
                close_price = row['bb_lower']
                wins += 1
            elif row['high'] >= sl:
                close_price = sl
                losses += 1
                
        if close_price is not None:
            calc_profit = mt5.order_calc_profit(side, 'HK50', lot, entry_price, close_price)
            if calc_profit is not None:
                balance += calc_profit
            if balance <= 0:
                print('MARGIN CALL! Conta Quebrada.')
                break
            in_trade = False

print(f'Final Balance: ${balance:.2f}')
print(f'Trades: {wins+losses} ({wins}W / {losses}L)')
mt5.shutdown()
