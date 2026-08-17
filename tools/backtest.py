import argparse
import sys
from datetime import datetime
import pandas as pd
import MetaTrader5 as mt5

def calc_indicators(df):
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
    df['sma200'] = df['close'].rolling(window=200).mean()
    return df

def run_simulation(df, initial_balance, pip_value, lot, symbol):
    balance = initial_balance
    wins = 0
    losses = 0
    in_trade = False
    side = 0
    entry_price = 0.0
    sl = 0.0
    tp = 0.0
    
    # Tracking
    total_profit_usd = 0.0
    
    # Pulamos os primeiros 250 candles para garantir que medias longas tenham se estabilizado
    start_idx = 250
    for i in range(start_idx, len(df)-1):
        row = df.iloc[i]
        next_row = df.iloc[i+1]
        
        if in_trade:
            is_win = False
            is_loss = False
            exit_price = 0.0
            
            if side == mt5.ORDER_TYPE_BUY:
                if next_row['high'] >= tp:
                    is_win = True
                    exit_price = tp
                elif next_row['low'] <= sl:
                    is_loss = True
                    exit_price = sl
            else:
                if next_row['low'] <= tp:
                    is_win = True
                    exit_price = tp
                elif next_row['high'] >= sl:
                    is_loss = True
                    exit_price = sl
            
            if is_win or is_loss:
                # Tenta pegar valor exato, senao calcula aproximado
                profit = mt5.order_calc_profit(side, symbol, lot, entry_price, exit_price)
                if profit is None:
                    points = abs(exit_price - entry_price)
                    # Estimativa para HK50 se broker estiver offline
                    profit = (points / 100.0) * 1.30 
                    if is_loss: profit = -profit
                
                # Custo real do spread (HK50: ~4.5 de preco no lote operado), em
                # moeda da conta via order_calc_profit. Fallback se API offline.
                spread_cost = None
                try:
                    spread_cost = mt5.order_calc_profit(
                        mt5.ORDER_TYPE_BUY, symbol, lot,
                        entry_price, entry_price + 4.5
                    )
                except Exception:
                    spread_cost = None
                if spread_cost is None:
                    spread_cost = (4.5 / 100.0) * 1.30 * (lot / 0.01)
                profit -= spread_cost
                
                balance += profit
                total_profit_usd += profit
                
                if profit > 0:
                    wins += 1
                else:
                    losses += 1
                
                in_trade = False
            continue
            
        # Filtro Institucional (MT5 Time: 04:15 a 07:00 == BRT: 22:15 a 01:00)
        h = row['time'].hour
        m = row['time'].minute
        is_institutional = (h == 4 and m >= 15) or (h == 5) or (h == 6) or (h == 7 and m == 0)

        # Filtro SMA200 (Somente a favor da macro)
        buy_sma200_ok = row['close'] > row['sma200']
        sell_sma200_ok = row['close'] < row['sma200']

        # Avaliacao do Setup Russo (HK50)
        width_ok = row['bb_width'] >= 50.0
        uptrend = row['ema9'] > row['sma21'] and row['sma21'] > row['ema50']
        downtrend = row['ema9'] < row['sma21'] and row['sma21'] < row['ema50']
        
        # BUY
        if is_institutional and buy_sma200_ok and row['low'] < row['bb_lower'] and width_ok and not downtrend and row['rsi'] < 30:
            in_trade = True
            side = mt5.ORDER_TYPE_BUY
            entry_price = row['close']
            sl = row['close'] - (row['bb_width'] / 2)
            tp = row['bb_upper']
                
        # SELL
        elif is_institutional and sell_sma200_ok and row['high'] > row['bb_upper'] and width_ok and not uptrend and row['rsi'] > 70:
            in_trade = True
            side = mt5.ORDER_TYPE_SELL
            entry_price = row['close']
            sl = row['close'] + (row['bb_width'] / 2)
            tp = row['bb_lower']
                
    return balance, wins, losses, total_profit_usd

def main():
    parser = argparse.ArgumentParser(description="Simulador financeiro retroativo para MT5Bot (Estrategia Original)")
    parser.add_argument("--months", type=int, default=1, help="Numero de meses para retroceder no backtest")
    parser.add_argument("--balance", type=float, default=16.47, help="Saldo inicial na conta")
    parser.add_argument("--lot", type=float, default=0.01, help="Tamanho do lote operado")
    parser.add_argument("--symbol", type=str, default="HK50", help="Ativo para simular")
    
    args = parser.parse_args()
    
    print(f"Iniciando simulacao MT5Bot...")
    print(f"Ativo: {args.symbol} | Meses: {args.months} | Lote: {args.lot} | Saldo: ${args.balance:.2f}")
    
    if not mt5.initialize():
        print("Erro: Nao foi possivel inicializar o MetaTrader 5.")
        sys.exit(1)
        
    info = mt5.symbol_info(args.symbol)
    if not info:
        print(f"Erro: Ativo {args.symbol} nao encontrado no MetaTrader 5.")
        mt5.shutdown()
        sys.exit(1)
        
    trade_tick_size = info.trade_tick_size
    trade_tick_value = info.trade_tick_value
    
    # Fallback se tick_size for 0
    if trade_tick_size == 0:
        trade_tick_size = info.point
        
    try:
        pip_value = (trade_tick_value / trade_tick_size) * args.lot
    except ZeroDivisionError:
        pip_value = 0.0
        
    # Calculando quantidade de candles aproximados
    # M5 = 12 por hora * 24h = 288 por dia * 30 dias = ~8640 candles por mes util
    candles_per_month = 9000 
    total_candles = args.months * candles_per_month
    
    # Limite maximo do MT5 para copy_rates_from_pos eh alto, mas bom nao abusar
    if total_candles > 100000:
        print("Aviso: Limitando a 100.000 candles por seguranca.")
        total_candles = 100000
        
    rates = None
    while total_candles >= 5000:
        print(f"Baixando ultimos {total_candles} candles (M5)... Aguarde.")
        rates = mt5.copy_rates_from_pos(args.symbol, mt5.TIMEFRAME_M5, 0, total_candles)
        if rates is not None and len(rates) > 0:
            break
        print("A corretora nao tem essa quantidade de dados historicos disponiveis. Reduzindo...")
        total_candles -= 10000
    
    if rates is None or len(rates) == 0:
        print("Erro: Nenhum dado retornado pelo MT5 mesmo apos reduzir quantidade.")
        mt5.shutdown()
        sys.exit(1)
        
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    print("Calculando indicadores tecnicos (Bollinger, RSI, EMAs)...")
    df = calc_indicators(df)
    
    start_date = df['time'].iloc[250] if len(df) > 250 else df['time'].iloc[0]
    end_date = df['time'].iloc[-1]
    
    print(f"Executando simulacao de {start_date} ate {end_date}...")
    final_balance, wins, losses, total_profit = run_simulation(
        df, args.balance, pip_value, args.lot, args.symbol
    )
    
    total_trades = wins + losses
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    
    print("\n" + "="*40)
    print("          RESULTADO DO BACKTEST")
    print("="*40)
    print(f"Periodo:         {start_date.date()} a {end_date.date()}")
    print(f"Estrategia:      Setup Russo Original (BB + RSI + EMAs Anti-Trend)")
    print(f"Ativo:           {args.symbol}")
    print(f"Lote Fixo:       {args.lot}")
    print(f"Operacoes:       {total_trades}")
    print(f"Vitorias:        {wins} ({win_rate:.1f}%)")
    print(f"Derrotas:        {losses} ({100 - win_rate:.1f}%)")
    print("-" * 40)
    print(f"Saldo Inicial:   ${args.balance:.2f}")
    print(f"Lucro Liquido:   ${total_profit:.2f}")
    print(f"Saldo Final:     ${final_balance:.2f}")
    print("="*40)
    
    mt5.shutdown()

if __name__ == "__main__":
    main()
