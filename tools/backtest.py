import argparse
import sys
from datetime import datetime
import pandas as pd
import MetaTrader5 as mt5
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from mt5bot.engine.indicators import add_all_indicators
from mt5bot.mentorship.ml_xgboost import MLSupervisor
from mt5bot.core import config

def calc_indicators(df):
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
    
    # Largura de bollinger (Bandwidth)
    if 'bollinger_upper' in df.columns and 'bollinger_lower' in df.columns and 'bollinger_mid' in df.columns:
        df['bb_width'] = df['bollinger_upper'] - df['bollinger_lower']
        df['bollinger_bandwidth'] = df['bb_width'] / df['bollinger_mid']
        df['bb_upper'] = df['bollinger_upper']
        df['bb_lower'] = df['bollinger_lower']
    else:
        df['bb_width'] = 0.0
        df['bollinger_bandwidth'] = 0.0
        df['bb_upper'] = 0.0
        df['bb_lower'] = 0.0
        
    df['rsi'] = df.get('rsi14', 0.0)
    return df

def run_simulation(df, initial_balance, symbol):
    balance = initial_balance
    wins = 0
    losses = 0
    ml_rejections = 0
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
                # Tenta pegar valor exato via MT5
                profit_points = exit_price - entry_price if side == mt5.ORDER_TYPE_BUY else entry_price - exit_price
                profit = mt5.order_calc_profit(side, symbol, current_trade_lot, entry_price, exit_price)
                if profit is None:
                    # Fallback matematico generico se broker offline
                    info = mt5.symbol_info(symbol)
                    tick_size = info.trade_tick_size if info else 0.01
                    tick_value = info.trade_tick_value if info else 1.0
                    points = abs(exit_price - entry_price)
                    profit = (points / tick_size) * tick_value * current_trade_lot
                    if is_loss: profit = -profit
                
                # Profit is already calculated accurately by MT5 or fallback
                
                # Custo real do spread no MT5 (Spread atual do broker)
                spread_cost = None
                try:
                    info = mt5.symbol_info(symbol)
                    spread_points = info.spread * info.point if info else 0.0
                    if spread_points == 0:
                        # Fallbacks caso fds/mercado fechado
                        spread_points = 4.5 if "HK50" in symbol else 0.00015
                        
                    spread_cost = mt5.order_calc_profit(
                        mt5.ORDER_TYPE_BUY, symbol, current_trade_lot,
                        entry_price, entry_price + spread_points
                    )
                except Exception:
                    spread_cost = None
                    
                if spread_cost is None:
                    # Fallback generico
                    tick_size = info.trade_tick_size if info else 0.01
                    tick_value = info.trade_tick_value if info else 1.0
                    spread_points = 4.5 if "HK50" in symbol else 0.00015
                    # Correct fallback spread cost calculation without volume_step division
                    spread_cost = (spread_points / tick_size) * tick_value * current_trade_lot
                profit -= spread_cost
                
                balance += profit
                total_profit_usd += profit
                
                if profit > 0:
                    wins += 1
                else:
                    losses += 1
                
                in_trade = False
            continue
            
        # Chamada à engine dinâmica
        from mt5bot.engine.strategy import StrategyScorer
        from mt5bot.engine.scoring import aplicar_scoring

        # Pega as últimas 10 velas para o motor
        sub_df = df.iloc[i-10:i+1]
        
        info = mt5.symbol_info(symbol)
        tick_size = info.trade_tick_size if info and info.trade_tick_size > 0 else (info.point if info else 0.01)
        
        setups_found, _ = StrategyScorer.evaluate_all(sub_df, tick_size=tick_size, tick_offset=1, symbol=symbol)
        
        if setups_found:
            setups_found = aplicar_scoring(setups_found, sub_df)
            if not setups_found:
                continue
                
            best_setup = setups_found[0]
            setup_name = best_setup['setup']
            
            ml_context = {
                'microstructure': {
                    'body_size': row['body_size'],
                    'upper_wick': row['upper_wick'],
                    'lower_wick': row['lower_wick']
                },
                'trend': {
                    'adx': row.get('adx', 0.0)
                },
                'regime': {
                    'z_score': row.get('z_score', 0.0)
                },
                'volatility': {
                    'atr': row.get('atr', 0.0),
                    'bollinger_bandwidth': row['bollinger_bandwidth']
                },
                'momentum': {
                    'rsi14': row['rsi']
                },
                'relative_distances': {
                    'dist_ema9': row['dist_ema9'],
                    'dist_sma21': row['dist_sma21'],
                    'dist_sma200': row['dist_sma200'],
                    'dist_vwap': row['dist_vwap']
                },
                'time': {
                    'hour': row['time'].hour,
                    'day_of_week': row['time'].dayofweek
                }
            }
            
            is_approved, prob, reason = MLSupervisor.predict_trade(symbol, setup_name, ml_context)
            
            if is_approved:
                in_trade = True
                side = mt5.ORDER_TYPE_BUY if str(best_setup['action']).upper() == 'BUY' else mt5.ORDER_TYPE_SELL
                entry_price = best_setup['trigger_price']
                sl = best_setup['stop_loss']
                tp = best_setup.get('target')
                if tp is None:
                    # Se, mesmo após aplicar scoring, não tiver alvo (algo muito raro), não opera
                    in_trade = False
                else:
                    # --- Kelly Dynamic Sizing ---
                    risco_pts = abs(entry_price - sl)
                    alvo_pts = abs(entry_price - tp)
                    rrr = alvo_pts / risco_pts if risco_pts > 0 else 0
                    
                    from mt5bot.risk.risk_calculator import calculate_dynamic_kelly_risk
                    risk_percent = calculate_dynamic_kelly_risk(prob, rrr)
                    risk_money = balance * (risk_percent / 100.0)
                    
                    info = mt5.symbol_info(symbol)
                    tick_size = info.trade_tick_size if info and info.trade_tick_size > 0 else (info.point if info else 0.01)
                    tick_value = info.trade_tick_value if info else 1.0
                    volume_step = info.volume_step if info else 0.01
                    
                    tick_cost = tick_value / tick_size
                    ticks_to_sl = risco_pts / tick_size
                    money_lost_per_lot = ticks_to_sl * tick_value
                    
                    if money_lost_per_lot > 0:
                        raw_lot = risk_money / money_lost_per_lot
                        # Simulate the broker limitation logic: if lot < minimum, use minimum and check if risk > max allowed.
                        # For simulation purposes, we will strictly enforce the volume step
                        lot = max(volume_step, round(raw_lot / volume_step) * volume_step)
                    else:
                        lot = volume_step
                    
                    # Store the dynamic lot in the state so when trade closes, it uses the dynamic lot
                    current_trade_lot = lot
            else:
                ml_rejections += 1
                
    return balance, wins, losses, total_profit_usd, ml_rejections

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
    final_balance, wins, losses, total_profit, ml_rejections = run_simulation(
        df, args.balance, args.symbol
    )
    
    total_trades = wins + losses
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    
    print("\n" + "="*40)
    print("          RESULTADO DO BACKTEST")
    print("="*40)
    print(f"Periodo:         {start_date.date()} a {end_date.date()}")
    print(f"Estrategia:      Setup Russo Original (BB + RSI + EMAs Anti-Trend) + IA (XGBoost)")
    print(f"Ativo:           {args.symbol}")
    print(f"Lote:            Dinamico (Half-Kelly)")
    print(f"Operacoes:       {total_trades}")
    print(f"Vitorias:        {wins} ({win_rate:.1f}%)")
    print(f"Derrotas:        {losses} ({100 - win_rate:.1f}%)")
    print(f"Sinais Vetados:  {ml_rejections} (Filtro IA)")
    print("-" * 40)
    print(f"Saldo Inicial:   ${args.balance:.2f}")
    print(f"Lucro Liquido:   ${total_profit:.2f}")
    print(f"Saldo Final:     ${final_balance:.2f}")
    print("="*40)
    
    mt5.shutdown()

if __name__ == "__main__":
    main()
