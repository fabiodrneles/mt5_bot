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
    current_time_str: Optional[str] = None,
    start_str: str = config.TRADING_START_TIME,
    end_str: str = config.TRADING_END_TIME,
) -> bool:
    """Verifica se a hora atual esta dentro da janela operacional configurada."""
    if not getattr(config, "TRADING_HOURS_ENABLED", True):
        return True

    try:
        if current_time_str is None:
            now = datetime.now()
            current_time = now.time()
        else:
            current_time = datetime.strptime(current_time_str, "%H:%M").time()
            
        start_time = datetime.strptime(start_str, "%H:%M").time()
        end_time = datetime.strptime(end_str, "%H:%M").time()
        
        return start_time <= current_time <= end_time
    except Exception as e:
        logger.error(f"Erro ao verificar horario de negociacao: {e}")
        return True  # Fallback permissivo em caso de falha de parse
