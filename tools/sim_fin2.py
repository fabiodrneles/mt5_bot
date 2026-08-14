import MetaTrader5 as mt5
import pandas as pd

def calculate_indicators(df):
    window = 20
    rm = df['close'].rolling(window=window).mean()
    rs = df['close'].rolling(window=window).std()
    df['bb_mid'] = rm
    df['bb_upper'] = rm + (rs * 2)
    df['bb_lower'] = rm - (rs * 2)
    df['bb_width'] = df['bb_upper'] - df['bb_lower']
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs_val = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs_val))
    
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['sma21'] = df['close'].rolling(window=21).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    return df

if not mt5.initialize(): exit()

# Simulate Trades
rates = mt5.copy_rates_from_pos('HK50', mt5.TIMEFRAME_M5, 0, 5000)
df = pd.DataFrame(rates)
df = calculate_indicators(df)

wins, losses = 0, 0
balance = 16.00
lot = 0.10  # Lote Ajustado para HK50 para bater os 20 USD
in_trade = False
side, entry_price, sl = 0, 0.0, 0.0

MIN_WIDTH = 50.0  

for i in range(50, len(df)):
    row = df.iloc[i]
    
    if not in_trade:
        width_ok = row['bb_width'] >= MIN_WIDTH
        
        # Filtro de Congruência (se as médias estão alinhadas perfeitamente, a tendência está forte. Não faça Mean Reversion)
        uptrend = row['ema9'] > row['sma21'] and row['sma21'] > row['ema50']
        downtrend = row['ema9'] < row['sma21'] and row['sma21'] < row['ema50']
        
        if row['low'] < row['bb_lower'] and width_ok and not downtrend:
            if row['rsi'] < 30:
                in_trade = True
                side = mt5.ORDER_TYPE_BUY
                entry_price = row['close']
                sl = entry_price - (row['bb_width'] / 2)
                
        elif row['high'] > row['bb_upper'] and width_ok and not uptrend:
            if row['rsi'] > 70:
                in_trade = True
                side = mt5.ORDER_TYPE_SELL
                entry_price = row['close']
                sl = entry_price + (row['bb_width'] / 2)
    else:
        close_price = None
        if side == mt5.ORDER_TYPE_BUY:
            if row['high'] >= row['bb_upper']:
                close_price = row['bb_upper']; wins += 1
            elif row['low'] <= sl:
                close_price = sl; losses += 1
        elif side == mt5.ORDER_TYPE_SELL:
            if row['low'] <= row['bb_lower']:
                close_price = row['bb_lower']; wins += 1
            elif row['high'] >= sl:
                close_price = sl; losses += 1
                
        if close_price is not None:
            calc = mt5.order_calc_profit(side, 'HK50', lot, entry_price, close_price)
            if calc is not None: balance += calc
            in_trade = False

print('FINAL_BALANCE_WITH_0.10: ' + str(balance))
print('TRADES: ' + str(wins+losses) + ' (' + str(wins) + 'W / ' + str(losses) + 'L)')
mt5.shutdown()
