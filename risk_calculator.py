"""Modulo de Calculo de Risco e Protecao de Capital.

Responsavel pelo dimensionamento dinamico de posicoes, travamento de limite de risco
por operacao e validacao de limites diarios de perda proporcional ao saldo da conta.
"""

from datetime import datetime
from decimal import Decimal, ROUND_DOWN
from typing import Tuple, Optional, Dict, Any
import MetaTrader5 as mt5
import config
import logger


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


def calculate_position_size(
    symbol: str,
    entry_price: float,
    sl_price: float,
    balance: Optional[float] = None,
    risk_percent: Optional[float] = None,
) -> Tuple[float, float, bool, str]:
    """Calcula o volume (lote) ideal para a operacao respeitar o risco percentual do saldo.

    Returns:
        Tuple[volume, risk_currency, is_safe, reason]
    """
    if balance is None:
        balance = get_account_balance()
    
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
    
    # Risco real em dinheiro para o volume final ajustado
    actual_risk_currency = final_volume * loss_per_lot
    
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


SUGGESTED_GLOBAL_ASSETS = ["HK50", "HKG50", "USDJPY", "AUDUSD", "EURUSD", "GBPUSD", "US500", "BTCUSD", "WIN", "WDO"]


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
            margin_info = calculate_required_margin(candidate, volume=0.01)
            suggestions.append(margin_info)

    return {
        "all_closed": True,
        "currency": currency,
        "suggestions": suggestions,
    }



