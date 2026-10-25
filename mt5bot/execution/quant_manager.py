"""Caminho de execucao das rotas quant (config.QUANT_ROUTES).

Executa a regra exatamente como foi validada no backtest: sinal no candle
fechado, entrada a mercado logo apos o fechamento, lote minimo, SL/TP no MT5 e
saida pela regra do setup. So enxerga posicoes com o MAGIC do bot, entao uma
posicao manual do usuario no mesmo ativo (conta hedging) nunca e tocada.
"""
import logging
import os

import MetaTrader5 as mt5

from mt5bot.core import config
from mt5bot.data import tracker
from mt5bot.engine import quant_setups
from mt5bot.execution import executor
from mt5bot.risk import risk_calculator

TF_SECONDS = {"M1": 60, "M5": 300, "M15": 900, "M30": 1800, "H1": 3600, "H4": 14400, "D1": 86400}
# Atraso maximo (fracao do candle) entre o fechamento do candle de sinal e a
# entrada. O backtest entra na abertura do candle seguinte: entrar horas depois
# seria outra estrategia.
MAX_ENTRY_DELAY_FRACTION = 0.10
TF_CONST = {60: mt5.TIMEFRAME_M1, 300: mt5.TIMEFRAME_M5, 900: mt5.TIMEFRAME_M15, 1800: mt5.TIMEFRAME_M30,
            3600: mt5.TIMEFRAME_H1, 14400: mt5.TIMEFRAME_H4, 86400: mt5.TIMEFRAME_D1}

_last_signal_candle = {}
_last_log = {}


def route_symbol(key, route) -> str:
    """Ativo da rota. A chave de QUANT_ROUTES e o nome da rota; por padrao, o proprio ativo. Para ter mais de
    uma rota no mesmo ativo (em timeframes diferentes), use uma chave propria e "symbol" (ex.: "USDJPY_IFR2")."""
    return (route or {}).get("symbol", key)


def get_route(symbol, timeframe_name):
    for key, route in (getattr(config, "QUANT_ROUTES", None) or {}).items():
        if route_symbol(key, route) == symbol and route.get("timeframe", "").upper() == str(timeframe_name).upper():
            return route
    return None


def signal_key(symbol, tf_secs) -> str:
    """Chave do ultimo candle avaliado: por ativo E timeframe (duas rotas no mesmo ativo nao se atropelam)."""
    return f"{symbol}:{tf_secs}"


def max_risk_pct(route) -> float:
    """Perda maxima no SL (% do saldo): limite proprio da rota ou o global."""
    pct = (route or {}).get("max_risk_pct")
    return float(pct if pct is not None else getattr(config, "QUANT_MAX_RISK_PCT", 2.0))


UNCONFIRMED_STATE = "🔒 CONFIRME A CONTA REAL (bot.bat setup)"
_unconfirmed_warned = False


def real_account_unconfirmed() -> bool:
    """Conta REAL sem confirmacao no assistente: nao abre posicao (spec 006 FR-2)."""
    global _unconfirmed_warned
    acc = mt5.account_info()
    if getattr(acc, "trade_mode", 0) != 2 or getattr(config, "LIVE_CONFIRMED", False):
        return False
    if not _unconfirmed_warned:
        _unconfirmed_warned = True
        logging.warning("Conta REAL sem confirmacao: o robo NAO abre posicoes. Rode 'bot.bat setup' "
                        "para revisar o risco e confirmar (posicoes ja abertas seguem geridas).")
    return True


def is_quant_position(position) -> bool:
    prefix = getattr(config, "QUANT_COMMENT_PREFIX", "Q ")
    return (getattr(position, "magic", None) == getattr(config, "MAGIC", 0)
            and str(getattr(position, "comment", "") or "").startswith(prefix))


def _log_once(key, msg, level=logging.INFO):
    if _last_log.get(key) != msg:
        logging.log(level, msg)
        _last_log[key] = msg


def _bar_epoch(ts):
    """Epoch (s) do candle; aceita pandas Timestamp ou numero."""
    if hasattr(ts, "timestamp"):
        return int(ts.timestamp())
    return int(ts)


def entry_window(symbol, setup, last_time, tf_secs):
    """Pode entrar agora? Devolve (estado de espera ou None, tick, symbol_info).

    Entrada so na abertura do candle seguinte (como no backtest), mesmo que ele abra depois de fim de
    semana/pausa de sessao: mede o atraso a partir da abertura do candle em formacao, nao do relogio.
    Usada pelas rotas ao vivo e pelas de estudo (mesma regra de tempo nas duas).
    """
    tick = mt5.symbol_info_tick(symbol)
    info = mt5.symbol_info(symbol)
    if tick is None or info is None or not tick.ask or not tick.bid:
        return "🔴 SEM TICK", None, None
    forming = mt5.copy_rates_from_pos(symbol, TF_CONST.get(tf_secs), 0, 1)
    if forming is None or len(forming) == 0 or int(forming[-1]["time"]) <= _bar_epoch(last_time):
        return "⏳ AGUARDANDO MERCADO", None, None
    delay = int(tick.time) - int(forming[-1]["time"])
    if delay < 0:
        return "⏳ AGUARDANDO MERCADO", None, None
    if delay > tf_secs * MAX_ENTRY_DELAY_FRACTION:
        _last_signal_candle[signal_key(symbol, tf_secs)] = last_time
        logging.info(f"[{symbol}] {setup}: sinal de {last_time} expirou (entrada {delay}s apos o fechamento). Ignorado.")
        return "🔵 SINAL EXPIRADO", None, None
    return None, tick, info


def is_study_route(route) -> bool:
    """Rota em estudo (mode = "study"): sinais e saidas reais, ordens VIRTUAIS (nada vai ao MT5)."""
    return str((route or {}).get("mode", "live")).lower() == "study"


def quant_cycle(symbol, df, timeframe_name, route):
    if is_study_route(route):
        from mt5bot.execution import quant_study
        return quant_study.study_cycle(symbol, df, timeframe_name, route)

    from mt5bot.execution.execution_manager import _reconcile_closed_trades
    _reconcile_closed_trades(symbol, df)

    setup = route["setup"]
    params = route.get("params", {})
    tf_secs = TF_SECONDS.get(str(timeframe_name).upper(), 3600)

    positions = [p for p in (mt5.positions_get(symbol=symbol) or []) if is_quant_position(p)]
    if positions:
        return _manage_quant_position(symbol, positions[0], df, setup, params, tf_secs)
    return _scan_quant(symbol, df, setup, params, tf_secs, max_risk_pct(route))


def _manage_quant_position(symbol, position, df, setup, params, tf_secs):
    is_buy = position.type == mt5.POSITION_TYPE_BUY
    side = "BUY" if is_buy else "SELL"
    entry_bar = int(position.time) - int(position.time) % tf_secs
    times = [_bar_epoch(t) for t in df["time"]]
    # Candles FECHADOS desde a entrada (o candle de sinal nao conta).
    held = sum(1 for t in times if t >= entry_bar)

    if held >= 1 and quant_setups.should_exit(setup, df, is_buy, params):
        logging.info(f"[{symbol}] {setup}: regra de saida atingida no fechamento. Liquidando {position.ticket}.")
        executor.close_full_position(position.ticket, symbol, position.type)
        return f"🟢 SAIDA {setup}"

    max_bars = params.get("max_bars")
    if max_bars and held >= max_bars:
        logging.info(f"[{symbol}] {setup}: {held} candles na posicao (limite {max_bars}). Liquidando {position.ticket}.")
        executor.close_full_position(position.ticket, symbol, position.type)
        return f"🟢 SAIDA {setup} (tempo)"

    return f"🟢 IN_POSITION ({setup} {side})"


def _scan_quant(symbol, df, setup, params, tf_secs, risk_pct):
    skey = signal_key(symbol, tf_secs)
    if df is None or len(df) < 200:
        return "🔴 WAIT_DATA"

    # /quit wait-flat (shutdown_manager) cria esta trava: nada de novas entradas.
    if os.path.exists(".no_new_trades"):
        return "🔴 BLOQUEADO"
    if real_account_unconfirmed():
        return UNCONFIRMED_STATE

    last_time = df["time"].iloc[-1]
    if _last_signal_candle.get(skey) == last_time:
        return "🔵 AGUARDANDO PRÓXIMO CANDLE"

    sig = quant_setups.evaluate(setup, df, params)
    if sig is None:
        _last_signal_candle[skey] = last_time
        _log_once(f"{symbol}_scan", f"[{symbol}] {setup}: sem sinal no candle {last_time}.")
        return "🔵 SCANNING"

    waiting, tick, info = entry_window(symbol, setup, last_time, tf_secs)
    if waiting:
        return waiting

    # Daily Max Loss Shield (novas entradas).
    try:
        limits = risk_calculator.calculate_risk_limits()
        daily_pnl = tracker.get_daily_pnl()
        if daily_pnl is not None and daily_pnl <= -limits["max_daily_loss_currency"]:
            _last_signal_candle[skey] = last_time
            logging.warning(f"[{symbol}] {setup}: Daily Max Loss atingido ({daily_pnl:.2f}). Sinal ignorado.")
            return "🔴 MAX LOSS DIÁRIO"
    except Exception as e:
        logging.warning(f"[{symbol}] Falha ao avaliar Daily Max Loss: {e}")

    is_buy = sig["action"] == "buy"
    side = "BUY" if is_buy else "SELL"
    price = tick.ask if is_buy else tick.bid
    sl = price - sig["sl_dist"] if is_buy else price + sig["sl_dist"]
    tp = None
    if sig.get("tp_dist"):
        tp = price + sig["tp_dist"] if is_buy else price - sig["tp_dist"]
    volume = info.volume_min
    order_type = mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL

    min_stop = (info.trade_stops_level or 0) * info.point
    if sig["sl_dist"] <= min_stop:
        _last_signal_candle[skey] = last_time
        logging.warning(f"[{symbol}] {setup}: SL ({sig['sl_dist']:.2f}) menor que o stops level ({min_stop:.2f}). Ignorado.")
        return "🟡 SINAL REJEITADO"

    # Risco: perda no SL com o lote minimo nao pode passar de risk_pct do saldo.
    account = mt5.account_info()
    balance = float(getattr(account, "balance", 0.0) or 0.0)
    loss = mt5.order_calc_profit(order_type, symbol, volume, price, sl)
    max_loss = balance * risk_pct / 100.0
    if loss is None or abs(loss) > max_loss:
        _last_signal_candle[skey] = last_time
        logging.warning(f"[{symbol}] {setup} {side}: perda no SL ${abs(loss or 0):.2f} > limite ${max_loss:.2f}"
                        f" ({risk_pct}% de ${balance:.2f}). Sinal ignorado para preservar margem.")
        return "🟡 SINAL REJEITADO"

    # Margem: precisa sobrar folga para as proximas tentativas.
    margin = mt5.order_calc_margin(order_type, symbol, volume, price)
    free = float(getattr(account, "margin_free", 0.0) or 0.0)
    reserve = getattr(config, "QUANT_MARGIN_RESERVE_MULT", 3.0)
    if margin is None or free - margin < margin * reserve:
        _last_signal_candle[skey] = last_time
        logging.warning(f"[{symbol}] {setup}: margem livre ${free:.2f} insuficiente (posicao usa ${margin or 0:.2f},"
                        f" reserva {reserve}x). Sinal ignorado.")
        return "🟡 SEM MARGEM"

    _last_signal_candle[skey] = last_time
    comment = f"{getattr(config, 'QUANT_COMMENT_PREFIX', 'Q ')}{setup}"
    logging.info(f"[{symbol}] {setup} {side} @ {price} SL={sl:.2f} TP={tp if tp is None else round(tp, 2)}"
                 f" lote={volume} risco=${abs(loss):.2f}. Enviando a mercado.")
    result = executor.place_market_order(symbol, side, sl, tp_price=tp, volume=volume, comment=comment)
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        logging.error(f"[{symbol}] {setup}: falha ao abrir posicao ({getattr(result, 'retcode', 'N/A')}).")
        return "🔴 ERRO DE ORDEM"

    tracker.record_entry(symbol=symbol, side=side, setup_type=setup, entry_price=price,
                         sl_price=sl, volume=volume, ticket=result.order)
    return f"🟢 EM POSIÇÃO ({setup} {side})"
