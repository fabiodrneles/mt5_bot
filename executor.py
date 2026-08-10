
import MetaTrader5 as mt5
import config
import logger
from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN

def get_symbol_info(symbol):
    info = mt5.symbol_info(symbol)
    if info is None:
        logger.error(f"Falha ao obter informacoes do simbolo {symbol}")
        return None
    return info


def get_tick_size(symbol_info):
    return symbol_info.trade_tick_size if symbol_info.trade_tick_size != 0.0 else symbol_info.point


def _format_price(price, symbol_info):
    if symbol_info is None:
        return price

    tick_size = symbol_info.trade_tick_size if symbol_info.trade_tick_size != 0.0 else symbol_info.point
    if tick_size <= 0:
        tick_size = 10 ** -symbol_info.digits

    dec_tick = Decimal(str(tick_size))
    dec_price = Decimal(str(price))
    quantized = (dec_price / dec_tick).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * dec_tick
    return float(quantized)


def _get_filling_type(symbol_info):
    """Determina o filling type suportado pelo simbolo."""
    filling = symbol_info.filling_mode
    if hasattr(mt5, "SYMBOL_FILLING_FOK") and (filling & mt5.SYMBOL_FILLING_FOK):
        return mt5.ORDER_FILLING_FOK
    elif hasattr(mt5, "SYMBOL_FILLING_IOC") and (filling & mt5.SYMBOL_FILLING_IOC):
        return mt5.ORDER_FILLING_IOC
    return mt5.ORDER_FILLING_RETURN


def _normalize_volume(volume, symbol_info):
    """Ajusta o volume para o múltiplo do step do símbolo.
    Ex: se volume_step = 0.01, volume 0.015 vira 0.01 (trunca para baixo).
    """
    step = symbol_info.volume_step
    if step <= 0:
        step = 0.01

    dec_step = Decimal(str(step))
    dec_volume = Decimal(str(volume))

    # Truncar para o múltiplo de step mais próximo abaixo do volume
    normalized_dec = (dec_volume / dec_step).to_integral_value(rounding=ROUND_DOWN) * dec_step

    # Garantir volume mínimo e máximo usando Decimal
    dec_min = Decimal(str(symbol_info.volume_min))
    dec_max = Decimal(str(symbol_info.volume_max))

    if normalized_dec < dec_min:
        normalized_dec = dec_min

    if normalized_dec > dec_max:
        normalized_dec = dec_max

    # Ajustar precisão para corresponder ao step
    normalized_dec = normalized_dec.quantize(dec_step)

    return float(normalized_dec)


def _send_order(request):
    result = mt5.order_send(request)
    if result is None:
        logger.error(f"order_send retornou None. Request: {request}. Erro MT5: {mt5.last_error()}")
        return None
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logger.error(f"Falha ao enviar ordem: action={request.get('action')} type={request.get('type')} "
                     f"symbol={request.get('symbol')} volume={request.get('volume')} "
                     f"price={request.get('price')} sl={request.get('sl')} "
                     f"Erro: {result.retcode} - {result.comment}")
    else:
        logger.info(f"Ordem enviada: type={request.get('type')} symbol={request.get('symbol')} "
                    f"volume={request.get('volume')} price={request.get('price')} "
                    f"sl={request.get('sl')} ticket={result.order}")
    return result


def get_current_spread(symbol):
    """Calcula o spread atual do símbolo em pontos."""
    info = get_symbol_info(symbol)
    if info is None:
        return None
    tick = mt5.symbol_info_tick(symbol)
    if tick is None or tick.ask == 0 or tick.bid == 0:
        return None
    point = info.point if info.point > 0 else 0.00001
    spread_points = int(round(abs(tick.ask - tick.bid) / point))
    return spread_points


def _place_stop_order(symbol, entry_price, sl_price, order_type, comment, volume=None):
    """Função auxiliar centralizada para colocar ordens pendentes (BUY/SELL STOP)."""
    symbol_info = get_symbol_info(symbol)
    if symbol_info is None:
        return None

    # FILTRO DE SPREAD:
    if config.MAX_SPREAD_POINTS is not None:
        current_spread = get_current_spread(symbol)
        if current_spread is not None and current_spread > config.MAX_SPREAD_POINTS:
            logger.warning(
                f"[SPREAD FILTER REJECTED] Simbolo {symbol}: Spread atual ({current_spread} pts) "
                f"excede o limite maximo de {config.MAX_SPREAD_POINTS} pontos."
            )
            return None

    if volume is None:
        volume = config.VOLUME_INITIAL
    volume = _normalize_volume(volume, symbol_info)
    filling = _get_filling_type(symbol_info)

    request = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "price": _format_price(entry_price, symbol_info),
        "sl": _format_price(sl_price, symbol_info),
        "deviation": 20,
        "type_filling": filling,
        "comment": comment,
        "magic": config.MAGIC,
        "expiration": 0,
    }
    return _send_order(request)


def place_buy_stop(symbol, entry_price, sl_price, volume=None):
    return _place_stop_order(symbol, entry_price, sl_price, mt5.ORDER_TYPE_BUY_STOP, "Setup 9.1 Buy Stop", volume=volume)


def place_sell_stop(symbol, entry_price, sl_price, volume=None):
    return _place_stop_order(symbol, entry_price, sl_price, mt5.ORDER_TYPE_SELL_STOP, "Setup 9.1 Sell Stop", volume=volume)


def place_buy_stop_92(symbol, entry_price, sl_price, volume=None):
    """Coloca ordem BUY STOP para Setup 9.2."""
    return _place_stop_order(symbol, entry_price, sl_price, mt5.ORDER_TYPE_BUY_STOP, "Setup 9.2 Buy Stop", volume=volume)


def place_sell_stop_92(symbol, entry_price, sl_price, volume=None):
    """Coloca ordem SELL STOP para Setup 9.2."""
    return _place_stop_order(symbol, entry_price, sl_price, mt5.ORDER_TYPE_SELL_STOP, "Setup 9.2 Sell Stop", volume=volume)


def modify_position_sl(position_ticket, symbol, new_sl):
    """Ajusta o Stop Loss de uma posição aberta existente (ex: para Breakeven)."""
    symbol_info = get_symbol_info(symbol)
    if symbol_info is None:
        return None

    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "position": position_ticket,
        "symbol": symbol,
        "sl": _format_price(new_sl, symbol_info),
        "magic": config.MAGIC,
    }
    return _send_order(request)



def cancel_order(order_ticket):
    request = {
        "action": mt5.TRADE_ACTION_REMOVE,
        "order": order_ticket,
        "comment": "Cancel Setup Order",
        "magic": config.MAGIC,
    }
    return _send_order(request)


def close_partial_position(position_ticket, symbol, volume_to_close):
    symbol_info = get_symbol_info(symbol)
    if symbol_info is None:
        return None

    positions = mt5.positions_get(ticket=position_ticket)
    if not positions:
        logger.warning(f"Posicao {position_ticket} nao encontrada para fechamento parcial.")
        return None
    position = positions[0]

    # Normalizar volume para step do simbolo
    volume_to_close = _normalize_volume(volume_to_close, symbol_info)
    if volume_to_close <= 0:
        logger.warning(f"Volume para fechar ({volume_to_close}) invalido apos normalizacao.")
        return None

    filling = _get_filling_type(symbol_info)

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        logger.error(f"Sem dados de tick para {symbol}. Impossivel fechar parcial.")
        return None

    if position.type == mt5.POSITION_TYPE_BUY:
        type_deal = mt5.ORDER_TYPE_SELL
        price = tick.bid
    else:
        type_deal = mt5.ORDER_TYPE_BUY
        price = tick.ask

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume_to_close,
        "type": type_deal,
        "position": position_ticket,
        "price": _format_price(price, symbol_info),
        "deviation": 20,
        "type_filling": filling,
        "comment": "Close Partial",
        "magic": config.MAGIC,
    }
    return _send_order(request)


def close_full_position(position_ticket, symbol, position_type):
    """Fecha posicao inteira.
    position_type: TradeSide enum (BUY ou SELL) da strategy ou constante MT5.
    """
    symbol_info = get_symbol_info(symbol)
    if symbol_info is None:
        return None

    # Obter volume da posicao com protecao contra None/vazio
    positions = mt5.positions_get(ticket=position_ticket)
    if not positions:
        logger.warning(f"Posicao {position_ticket} nao encontrada para fechamento total.")
        return None
    volume = positions[0].volume

    filling = _get_filling_type(symbol_info)

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        logger.error(f"Sem dados de tick para {symbol}. Impossivel fechar posicao.")
        return None

    is_buy = (
        (hasattr(position_type, "name") and position_type.name == "BUY")
        or (hasattr(position_type, "value") and position_type.value == 1)
        or position_type in (mt5.ORDER_TYPE_BUY, getattr(mt5, "POSITION_TYPE_BUY", 0))
    )
    if is_buy:
        type_deal = mt5.ORDER_TYPE_SELL
        price = tick.bid
    else:
        type_deal = mt5.ORDER_TYPE_BUY
        price = tick.ask

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": type_deal,
        "position": position_ticket,
        "price": _format_price(price, symbol_info),
        "deviation": 20,
        "type_filling": filling,
        "comment": "Close Full",
        "magic": config.MAGIC,
    }
    return _send_order(request)


def get_current_orders(symbol):
    orders = mt5.orders_get(symbol=symbol)
    if orders is None:
        logger.error(f"Falha ao obter ordens pendentes para {symbol}: {mt5.last_error()}")
        return []
    return list(orders)


def get_current_positions(symbol):
    positions = mt5.positions_get(symbol=symbol)
    if positions is None:
        logger.error(f"Falha ao obter posicoes abertas para {symbol}: {mt5.last_error()}")
        return []
    return list(positions)