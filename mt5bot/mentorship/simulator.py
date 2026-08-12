import json
import os
import time
from datetime import datetime, timezone
import pandas as pd
import MetaTrader5 as mt5

from mt5bot.core import logger, config
from mt5bot.engine.indicators import add_all_indicators

_REJECTIONS_FILE = os.path.join(os.path.expanduser(os.getenv('APPDATA') or os.path.join('~')), 'mt5bot', 'virtual_rejections.json')
_ENRICHED_FILE = os.path.join(os.path.expanduser(os.getenv('APPDATA') or os.path.join('~')), 'mt5bot', 'virtual_rejections_enriched.json')

def load_rejections(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_enriched(data, filepath):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def _get_sim_data(symbol, start_time_iso, duration_hours=4, timeframe_name="M5"):
    """
    Baixa histórico do timeframe original para indicadores e M1 para simulação.
    """
    dt = datetime.fromisoformat(start_time_iso)
    ts_start = int(dt.timestamp())
    
    # 1. Puxa histórico longo no timeframe original para calcular indicadores precisos
    tf_const = config.AVAILABLE_TIMEFRAMES.get(timeframe_name, mt5.TIMEFRAME_M5)
    # 10 dias para garantir médias longas (ex: SMA200)
    ts_start_history = ts_start - (10 * 24 * 3600)
    
    rates_hist = mt5.copy_rates_range(symbol, tf_const, ts_start_history, ts_start)
    fallback_atr = 0.0
    if rates_hist is not None and len(rates_hist) > 0:
        df_hist = pd.DataFrame(rates_hist)
        df_hist['time'] = pd.to_datetime(df_hist['time'], unit='s', utc=True)
        df_hist = add_all_indicators(df_hist)
        fallback_atr = df_hist.iloc[-1].get('atr', 0.0) if 'atr' in df_hist.columns else 0.0
        
    # 2. Puxa o M1 apenas para o futuro (trajetória cirúrgica)
    ts_end = ts_start + (duration_hours * 3600)
    rates_m1 = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, ts_start, ts_end)
    
    if rates_m1 is None or len(rates_m1) == 0:
        return None, fallback_atr
        
    df_m1 = pd.DataFrame(rates_m1)
    df_m1['time'] = pd.to_datetime(df_m1['time'], unit='s', utc=True)
    
    return df_m1, fallback_atr

def run_simulation(symbol, side, entry_price, sl_price, df_m1):
    """
    Simula o trade candle a candle (M1).
    Condições de saída:
    - Stop Loss atingido
    - EMA9 vira contra a posição (Trailing Stop do bot)
    """
    # Calcula EMA9 para ter o trailing stop
    df_m1 = add_all_indicators(df_m1)
    
    for i in range(1, len(df_m1)):
        candle = df_m1.iloc[i]
        high = float(candle['high'])
        low = float(candle['low'])
        close = float(candle['close'])
        
        liquidar = False
        exit_price = 0.0
        
        if side == 'BUY':
            if sl_price > 0 and low <= sl_price:
                liquidar = True
                exit_price = sl_price
            elif candle.get('ema9_down', False):
                liquidar = True
                exit_price = close
        else: # SELL
            if sl_price > 0 and high >= sl_price:
                liquidar = True
                exit_price = sl_price
            elif candle.get('ema9_up', False):
                liquidar = True
                exit_price = close
                
        if liquidar:
            # Calcula PnL pips
            if side == 'BUY':
                pnl_pips = exit_price - entry_price
            else:
                pnl_pips = entry_price - exit_price
                
            return {
                "result": "win" if pnl_pips > 0 else "loss" if pnl_pips < 0 else "breakeven",
                "pnl_pips": round(pnl_pips, 5),
                "exit_price": exit_price,
                "exit_time": candle['time'].isoformat(),
                "duration_m1_candles": i
            }
            
    # Chegou no fim das 4 horas sem sair
    return {
        "result": "timeout",
        "pnl_pips": 0.0,
        "exit_price": entry_price,
        "exit_time": df_m1.iloc[-1]['time'].isoformat(),
        "duration_m1_candles": len(df_m1)
    }

def simulate_rejections():
    """Roda backtest para cada rejeicao pendente."""
    if not mt5.initialize():
        logger.error("Falha ao inicializar MT5 para simulacao.")
        return

    # Tenta carregar o enriquecido se existir, senão pega o raw
    if os.path.exists(_ENRICHED_FILE):
        rejections = load_rejections(_ENRICHED_FILE)
    else:
        rejections = load_rejections(_REJECTIONS_FILE)

    if not rejections:
        logger.info("Nenhuma rejeição encontrada para simular.")
        mt5.shutdown()
        return

    simulated_count = 0
    for rej in rejections:
        if "result" in rej:
            continue # ja simulado
            
        symbol = rej['symbol']
        side = rej['side']
        entry_price = rej['entry_price']
        sl_price = rej.get('sl_price', 0.0)
        start_time = rej['time']
        
        logger.info(f"[Simulator] Simulando {symbol} {side} as {start_time} (Entry: {entry_price}, SL original: {sl_price})")
        
        timeframe = rej.get('timeframe', 'M5')
        
        # Puxa os dados e o ATR de fallback
        result = _get_sim_data(symbol, start_time, duration_hours=4, timeframe_name=timeframe)
        if result is None:
            logger.warning(f"  Sem dados M1 para {symbol} em {start_time}")
            continue
            
        df_m1, fallback_atr = result
        
        if df_m1.empty or len(df_m1) < 10:
            logger.warning(f"  Sem dados futuros M1 para {symbol} em {start_time}")
            continue
            
        # Aplica a reciclagem de dados (Fallback SL) se não houver SL registrado
        if sl_price == 0.0:
            if fallback_atr > 0:
                if side == 'BUY':
                    sl_price = entry_price - (fallback_atr * 2)
                else:
                    sl_price = entry_price + (fallback_atr * 2)
                logger.info(f"  -> [RECICLAGEM] SL reconstruído usando ATRx2: {sl_price:.5f}")
            else:
                # Fallback extremo se ATR falhar (0.2%)
                if side == 'BUY':
                    sl_price = entry_price * 0.998
                else:
                    sl_price = entry_price * 1.002
                logger.info(f"  -> [RECICLAGEM] SL reconstruído usando % fixo: {sl_price:.5f}")

        outcome = run_simulation(symbol, side, entry_price, sl_price, df_m1)
        
        # Merge outcome into rejection dict
        rej.update(outcome)
        simulated_count += 1
        
        # Rate limit to not spam mt5
        time.sleep(0.1)

    if simulated_count > 0:
        save_enriched(rejections, _ENRICHED_FILE)
        logger.info(f"Simulados {simulated_count} novos trades. Salvo em {_ENRICHED_FILE}")
    else:
        logger.info("Nenhum novo trade precisou ser simulado.")

    mt5.shutdown()

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
    simulate_rejections()
