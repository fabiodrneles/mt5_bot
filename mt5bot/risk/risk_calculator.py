"""Modulo de Calculo de Risco e Protecao de Capital.

Responsavel pelo dimensionamento dinamico de posicoes, travamento de limite de risco
por operacao e validacao de limites diarios de perda proporcional ao saldo da conta.
"""

from datetime import datetime
from decimal import Decimal, ROUND_DOWN
from typing import Tuple, Optional, Dict, Any
import MetaTrader5 as mt5
from mt5bot.core import config
from mt5bot.core import logger


def get_account_balance() -> float:
    """Obtem o saldo atual da conta no MetaTrader 5.
    
    Caso o MT5 nao esteja conectado ou em ambiente de teste sem conta,
    retorna o valor de saldo padrao definido em config.DEFAULT_ACCOUNT_BALANCE.
    """
    try:
        acc_info = mt5.account_info()
        if acc_info is not None and hasattr(acc_info, "balance") and acc_info.balance > 0:
            return float(acc_info.balance)
    except Exception as e:
        logger.debug(f"Nao foi possivel obter saldo via MT5: {e}")
    
    return float(config.DEFAULT_ACCOUNT_BALANCE)


def calculate_risk_limits(balance: Optional[float] = None) -> Dict[str, float]:
    """Retorna o mapa de limites financeiros de risco com base no saldo informado ou obtido."""
    if balance is None:
        balance = get_account_balance()
    
    max_trade_risk_curr = balance * (config.MAX_RISK_PER_TRADE_PERCENT / 100.0)
    abs_max_trade_risk_curr = balance * (config.ABSOLUTE_MAX_TRADE_RISK_PERCENT / 100.0)
    max_daily_loss_curr = balance * (config.MAX_DAILY_LOSS_PERCENT / 100.0)
    
    return {
        "balance": balance,
        "max_trade_risk_currency": max_trade_risk_curr,
        "absolute_max_trade_risk_currency": abs_max_trade_risk_curr,
        "max_daily_loss_currency": max_daily_loss_curr,
    }

def calculate_dynamic_kelly_risk(prob_win: float, rrr: float) -> float:
    """
    Calcula a fracao Half-Kelly otimizada e aplica limites de seguranca (Clamping).
    Retorna o percentual do saldo a ser arriscado (ex: 1.5).
    """
    if prob_win <= 0 or prob_win >= 1.0 or rrr <= 0:
        return config.MAX_RISK_PER_TRADE_PERCENT  # Fallback
        
    kelly_fraction = prob_win - ((1.0 - prob_win) / rrr)
    half_kelly = kelly_fraction / 2.0
    
    # Clamping de seguranca (0.5% a 2.0%)
    safe_risk = max(0.005, min(0.02, half_kelly))
    return safe_risk * 100.0  # Retorna em percentual (ex: 1.5%)



def calculate_position_size(
    symbol: str,
    entry_price: float,
    sl_price: float,
    balance: Optional[float] = None,
    risk_percent: Optional[float] = None,
    prob_win: Optional[float] = None,
    tp_price: Optional[float] = None,
) -> Tuple[float, float, bool, str]:
    """Calcula o volume (lote) ideal para a operacao respeitar o risco percentual do saldo.

    Returns:
        Tuple[volume, risk_currency, is_safe, reason]
    """
    if balance is None:
        balance = get_account_balance()
    
    # --- Bloqueio de Garagem (Capital Mínimo) ---
    min_balance_reqs = getattr(config, 'MIN_BALANCE_REQUIREMENTS', {})
    if symbol in min_balance_reqs:
        required_balance = min_balance_reqs[symbol]
        if balance < required_balance:
            reason = f"[GARAGE LOCK] {symbol} bloqueado na garagem. Saldo atual (${balance:.2f}) e menor que a margem de seguranca exigida (${required_balance:.2f})."
            logger.info(reason)
            return 0.0, 0.0, False, reason

    # --- Phase 3: Dynamic Half-Kelly Override ---
    if prob_win is not None and tp_price is not None:
        sl_distance = abs(entry_price - sl_price)
        tp_distance = abs(entry_price - tp_price)
        if sl_distance > 0:
            rrr = tp_distance / sl_distance
            dynamic_risk = calculate_dynamic_kelly_risk(prob_win, rrr)
            if risk_percent is None or dynamic_risk != config.MAX_RISK_PER_TRADE_PERCENT:
                logger.info(f"[{symbol}] Kelly Criterion ATIVADO. Win Prob: {prob_win:.2f}, RRR: {rrr:.2f} -> Risco Alocado: {dynamic_risk:.2f}%")
                risk_percent = dynamic_risk

    if risk_percent is None:
        risk_percent = config.MAX_RISK_PER_TRADE_PERCENT
        
    limits = calculate_risk_limits(balance)
    target_risk_currency = balance * (risk_percent / 100.0)
    abs_max_risk_currency = limits["absolute_max_trade_risk_currency"]
    
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        logger.warning(f"[RISK SHIELD] Informacoes do simbolo '{symbol}' nao encontradas. Usando volume inicial padrao.")
        return config.VOLUME_INITIAL, target_risk_currency, True, "OK (Default volume fallback)"
        
    sl_distance = abs(entry_price - sl_price)
    if sl_distance <= 0:
        return 0.0, 0.0, False, "Distancia do Stop Loss invalida ou zero."
        
    tick_size = getattr(symbol_info, "trade_tick_size", 0.01) or 0.01
    tick_value = getattr(symbol_info, "trade_tick_value", 0.01) or 0.01
    vol_min = getattr(symbol_info, "volume_min", 0.01) or 0.01
    vol_max = getattr(symbol_info, "volume_max", 100.0) or 100.0
    vol_step = getattr(symbol_info, "volume_step", 0.01) or 0.01

    # Perda monetaria por 1.0 lote inteiro
    ticks_in_sl = sl_distance / tick_size
    loss_per_lot = ticks_in_sl * tick_value

    # --- CONVERSAO DE MOEDA (FIX HK50): tick_value pode estar em moeda do simbolo
    # (ex: HKD), enquanto a conta e USD. order_calc_profit retorna o valor real
    # na moeda da conta. Usa-lo quando disponivel evita risco superestimado
    # que faz o RISK SHIELD rejeitar operacoes validas com saldo pequeno.
    try:
        side = mt5.ORDER_TYPE_SELL if sl_price > entry_price else mt5.ORDER_TYPE_BUY
        probe_loss = mt5.order_calc_profit(side, symbol, 1.0, entry_price, sl_price)
        if probe_loss is not None and probe_loss < 0:
            loss_per_lot = abs(float(probe_loss))
    except Exception:
        pass  # mantem o calculo por ticks se a API falhar

    if loss_per_lot <= 0:
        return vol_min, 0.0, False, "Cálculo de perda por lote inválido."

    # Lote teorico ideal para bater o risco desejado
    raw_volume = target_risk_currency / loss_per_lot
    
    # Normalizacao do volume de acordo com volume_step e limites
    step_dec = Decimal(str(vol_step))
    steps = Decimal(str(raw_volume)) / step_dec
    steps = steps.quantize(Decimal("1"), rounding=ROUND_DOWN)
    calculated_volume = float(steps * step_dec)
    
    # Garantir que respeite volume_min e volume_max
    final_volume = max(vol_min, min(vol_max, calculated_volume))
    
    # --- Roteamento por Ativo (Fase 3: Lote Override para Indices/Centavos) ---
    asset_min_lots = getattr(config, 'ASSET_MIN_LOTS', {})
    if symbol in asset_min_lots:
        override_lot = asset_min_lots[symbol]
        final_volume = max(final_volume, override_lot)
        final_volume = min(final_volume, vol_max)
    
    # Risco real em dinheiro para o volume final ajustado
    actual_risk_currency = final_volume * loss_per_lot
    
    # --- FILTRO SPREAD TRAP ---
    # Protege contra Stops muito curtos que seriam pegos imediatamente pelo spread (mercado ilíquido)
    ask = getattr(symbol_info, "ask", 0.0)
    bid = getattr(symbol_info, "bid", 0.0)
    point = getattr(symbol_info, "point", 0.00001) or 0.00001
    
    if ask > 0 and bid > 0:
        spread_pts = (ask - bid) / point
        sl_distance_pts = sl_distance / point
        min_multiplier = getattr(config, "MIN_STOP_SPREAD_MULTIPLIER", 1.5)
        
        limit_pts = spread_pts * min_multiplier
        if sl_distance_pts < limit_pts:
            reason = "Spread Trap"
            logger.warning(f"[RISK SHIELD REJECTED] Operacao cancelada: {reason}. SL {sl_distance_pts:.1f} pts < Mínimo {limit_pts:.1f} pts (Spread: {spread_pts:.1f} x {min_multiplier})")
            return 0.0, 0.0, False, reason
    
    # FILTRO DE SEGURANCA MAXIMA:
    # Se o risco real em dinheiro exceder a trava de corte absoluto (ex: > 1.5% do saldo), REJEITA A ORDEM!
    if actual_risk_currency > abs_max_risk_currency:
        reason = (
            f"[RISK SHIELD REJECTED] Operacao cancelada: Risco do Stop Loss (R$ {actual_risk_currency:.2f}) "
            f"excede o limite seguro de {config.ABSOLUTE_MAX_TRADE_RISK_PERCENT}% do saldo (R$ {abs_max_risk_currency:.2f})."
        )
        logger.warning(reason)
        return final_volume, actual_risk_currency, False, reason
        
    reason = f"OK (Risco: R$ {actual_risk_currency:.2f} / {risk_percent}% do saldo)"
    logger.info(f"[RISK SHIELD APPROVED] Simbolo: {symbol} | Volume: {final_volume} | {reason}")
    return final_volume, actual_risk_currency, True, reason


def is_within_trading_hours(
    symbol: Optional[str] = None,
    current_time_str: Optional[str] = None,
    start_str: Optional[str] = None,
    end_str: Optional[str] = None,
) -> bool:
    """Verifica se a hora atual esta dentro da janela operacional permitida para o ativo.
    Suporta busca especifica por simbolo em SYMBOL_TRADING_HOURS (ex: HK50 22:15-12:00 BRT, WIN 09:15-17:15 BRT)
    e suporta sessoes de negociacao que atravessam a meia-noite.
    """
    if not getattr(config, "TRADING_HOURS_ENABLED", True):
        return True

    try:
        # Se symbol for informado, buscar horario especifico em SYMBOL_TRADING_HOURS
        if symbol and hasattr(config, "SYMBOL_TRADING_HOURS"):
            sym_clean = symbol.upper()
            sym_map = config.SYMBOL_TRADING_HOURS
            matching_key = None
            for key in sym_map:
                if key in sym_clean:
                    matching_key = key
                    break
            
            if matching_key:
                hours = sym_map[matching_key]
                if start_str is None:
                    start_str = hours.get("start")
                if end_str is None:
                    end_str = hours.get("end")

        if start_str is None:
            start_str = getattr(config, "TRADING_START_TIME", "09:15")
        if end_str is None:
            end_str = getattr(config, "TRADING_END_TIME", "16:45")

        if current_time_str is None:
            now = datetime.now()
            current_time = now.time()
        else:
            current_time = datetime.strptime(current_time_str, "%H:%M").time()
            
        start_time = datetime.strptime(start_str, "%H:%M").time()
        end_time = datetime.strptime(end_str, "%H:%M").time()
        
        # Sessao diurna convencional (ex: 09:15 as 17:15)
        if start_time <= end_time:
            return start_time <= current_time <= end_time
        else:
            # Sessao noturna que cruza a meia-noite (ex: HK50 das 22:15 as 12:00)
            return current_time >= start_time or current_time <= end_time

    except Exception as e:
        logger.error(f"Erro ao verificar horario de negociacao para {symbol}: {e}")
        return True


def get_trading_session_info(symbol: Optional[str] = None) -> Dict[str, Any]:
    """Retorna informacoes detalhadas e formatadas da sessao operacional do ativo no fuso Horario de Brasilia (BRT).
    
    Returns:
        Dict com status operacional, janela de horario, hora atual e badge formatado com cores.
    """
    start_str = getattr(config, "TRADING_START_TIME", "09:15")
    end_str = getattr(config, "TRADING_END_TIME", "16:45")
    
    if symbol and hasattr(config, "SYMBOL_TRADING_HOURS"):
        sym_clean = symbol.upper()
        sym_map = config.SYMBOL_TRADING_HOURS
        for key, hours in sym_map.items():
            if key in sym_clean:
                start_str = hours.get("start", start_str)
                end_str = hours.get("end", end_str)
                break

    now = datetime.now()
    curr_str = now.strftime("%H:%M")
    is_open = is_within_trading_hours(symbol=symbol)
    
    # Cores ANSI para feedback visual no terminal
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

    sym_display = symbol.upper() if symbol else "GERAL"

    if is_open:
        badge = (
            f"{BOLD}{GREEN}[#] [SESSAO OPERACIONAL ATIVA]{RESET} "
            f"{CYAN}{sym_display}{RESET} | Janela BRT: {start_str} as {end_str} | Hora Atual: {curr_str}"
        )
    else:
        badge = (
            f"{BOLD}{YELLOW}[#] [FORA DO HORARIO OPERACIONAL]{RESET} "
            f"{CYAN}{sym_display}{RESET} | Janela BRT: {start_str} as {end_str} | Hora Atual: {curr_str}"
        )


    return {
        "is_open": is_open,
        "symbol": sym_display,
        "start_time": start_str,
        "end_time": end_str,
        "current_time": curr_str,
        "formatted_badge": badge,
    }


def get_account_currency() -> str:
    """Obtem a moeda oficial da conta no MetaTrader 5 (ex: USD, BRL, EUR)."""
    try:
        acc_info = mt5.account_info()
        if acc_info is not None and hasattr(acc_info, "currency") and acc_info.currency:
            return str(acc_info.currency)
    except Exception:
        pass
    return "USD"


def calculate_required_margin(symbol: str, volume: float = 0.01) -> Dict[str, Any]:
    """Calcula a margem exigida na moeda da conta do usuario para abrir posicao no ativo.
    
    Returns:
        Dict com symbol, volume, margin, currency, price, is_available.
    """
    currency = get_account_currency()
    try:
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is not None:
            price = getattr(symbol_info, "ask", 0.0) or getattr(symbol_info, "last", 0.0)
            if price <= 0:
                price = getattr(symbol_info, "bid", 1.0)
            
            margin = mt5.order_calc_margin(mt5.ORDER_TYPE_BUY, symbol, volume, price)
            if margin is not None and margin > 0:
                return {
                    "symbol": symbol,
                    "volume": volume,
                    "margin": float(margin),
                    "currency": currency,
                    "price": price,
                    "is_available": True,
                }
    except Exception as e:
        logger.debug(f"Nao foi possivel obter margem via MT5 para {symbol}: {e}")

    # Fallback estimativo para testes / sem conexao MT5
    return {
        "symbol": symbol,
        "volume": volume,
        "margin": 15.0,
        "currency": currency,
        "price": 100.0,
        "is_available": True,
    }


SUGGESTED_GLOBAL_ASSETS = getattr(config, "AVAILABLE_SYMBOLS", [
    "HK50", "HKG50", "USDJPY", "AUDUSD", "EURUSD", "GBPUSD", "USDCAD", "USDCHF", "NZDUSD",
    "EURGBP", "EURJPY", "GBPJPY", "AUDJPY", "EURAUD", "US500", "SP500", "NAS100", "USTEC",
    "US30", "DJ30", "GER40", "DAX40", "UK100", "JPN225", "XAUUSD", "XAGUSD", "WTI", "USOIL",
    "WIN", "WDO", "PETR4", "VALE3", "ITUB4", "BBDC4"
])



def check_all_symbols_closed(symbols: list) -> bool:
    """Verifica se TODOS os simbolos configurados pelo usuario estao fora do horario operacional."""
    if not symbols:
        return False
    return all(not is_within_trading_hours(sym) for sym in symbols)


def get_open_market_suggestions(configured_symbols: list) -> Dict[str, Any]:
    """Analisa ativos abertos no momento e retorna sugestoes com margem calculada na moeda da conta."""
    all_closed = check_all_symbols_closed(configured_symbols)
    if not all_closed:
        return {"all_closed": False, "suggestions": []}

    currency = get_account_currency()
    suggestions = []
    
    for candidate in SUGGESTED_GLOBAL_ASSETS:
        if candidate not in configured_symbols and is_within_trading_hours(candidate):
            sym_info = mt5.symbol_info(candidate)
            if sym_info is not None or not hasattr(mt5, "account_info"):
                margin_info = calculate_required_margin(candidate, volume=0.01)
                suggestions.append(margin_info)


    return {
        "all_closed": True,
        "currency": currency,
        "suggestions": suggestions,
    }


def opening_gap_filter(symbol: str, max_gap_pips: float = 50.0, safe_minutes: int = 5) -> Tuple[bool, str]:
    """
    Filtro de Gap de Abertura (Fase 2).
    Bloqueia operações nos primeiros minutos do pregão se o gap de abertura for violento.
    """
    try:
        if not mt5.initialize():
            return True, "Gap ignorado (Mock)"
            
        sym_info = mt5.symbol_info(symbol)
        if sym_info is None:
            return True, "Gap ignorado (Info ausente)"
            
        # Pega a vela do dia atual e a de ontem
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1, 0, 2)
        if rates is None or len(rates) < 2:
            return True, "Gap ignorado (Sem histórico D1)"
            
        yesterday_close = rates[0]['close']
        today_open = rates[1]['open']
        
        # Pega a hora atual do servidor
        last_tick = mt5.symbol_info_tick(symbol)
        if last_tick is None:
            return True, "Gap ignorado (Sem tick)"
            
        current_time = datetime.fromtimestamp(last_tick.time)
        open_time = datetime.fromtimestamp(rates[1]['time'])
        
        # Se ainda estivermos na janela inicial (ex: primeiros 5 min)
        if (current_time - open_time).total_seconds() <= (safe_minutes * 60):
            gap_size = abs(today_open - yesterday_close)
            
            # Converte pips/pontos (simplificado pelo point do ativo)
            point = sym_info.point
            gap_in_pips = gap_size / point if point > 0 else 0
            
            if gap_in_pips > max_gap_pips:
                reason = f"[GAP FILTER] Rejeitado. Gap de {gap_in_pips:.1f} pips excede limite seguro de {max_gap_pips} pips na abertura."
                logger.warning(reason)
                return False, reason
                
        return True, "OK (Fora da janela de gap ou gap seguro)"
    except Exception as e:
        logger.error(f"Erro no opening_gap_filter: {e}")
        return True, "Gap ignorado (Erro)"


def check_correlation_risk(symbol: str, open_positions: list) -> Tuple[bool, str]:
    """
    Proteção de Risco de Correlação (Fase 5).
    Evita dobrar o risco financeiro em ativos que andam quase idênticos (correlação > 0.8).
    Ex: Se tem EURUSD aberto comprado, bloqueia GBPUSD na mesma direção para não inflar a exposição a 2%.
    """
    # Matriz de pares altamente correlacionados (positiva ou inversamente)
    HIGH_CORRELATION_GROUPS = [
        {"EURUSD", "GBPUSD", "NZDUSD", "AUDUSD"}, # Risco contra USD
        {"USDCHF", "USDJPY"}, # Risco a favor do USD (Inverso ao de cima)
        {"US30", "US500", "USTEC", "NAS100"}, # Índices Americanos
        {"WTI", "USOIL"} # Petróleo
    ]
    
    # Descobre a qual grupo de correlação o simbolo pretendido pertence
    target_group = None
    for group in HIGH_CORRELATION_GROUPS:
        if symbol in group:
            target_group = group
            break
            
    if not target_group:
        return True, "Sem risco de correlação conhecido."
        
    # Verifica se já temos posição em algum ativo do mesmo grupo
    for pos in open_positions:
        # A API de posições pode retornar objeto ou dict, dependendo do mock
        pos_symbol = getattr(pos, 'symbol', None)
        if pos_symbol is None and isinstance(pos, dict):
            pos_symbol = pos.get('symbol')
            
        if pos_symbol and pos_symbol in target_group and pos_symbol != symbol:
            reason = f"[CORRELATION RISK] Operação em {symbol} bloqueada. Posição já aberta em {pos_symbol} (Mesmo cluster sistêmico)."
            logger.warning(reason)
            return False, reason
            
    return True, "OK (Risco sistêmico pulverizado)"



