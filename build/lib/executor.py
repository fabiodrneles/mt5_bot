import MetaTrader5 as mt5
import config
import logger
from decimal import Decimal, ROUND_DOWN


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
    return round(price, symbol_info.digits)


def _get_filling_type(symbol_info):
    """Determina o filling type suportado pelo simbolo."""
    filling = symbol_info.filling_mode
    if filling & mt5.ORDER_FILLING_FOK:
        return mt5.ORDER_FILLING_FOK
    elif filling & mt5.ORDER_FILLING_IOC:
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


def place_buy_stop(symbol, entry_price, sl_price):
    symbol_info = get_symbol_info(symbol)
    if symbol_info is None:
        return None

    volume = _normalize_volume(config.VOLUME_INITIAL, symbol_info)
    filling = _get_filling_type(symbol_info)

    request = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": volume,
        "type": mt5.ORDER_TYPE_BUY_STOP,
        "price": _format_price(entry_price, symbol_info),
        "sl": _format_price(sl_price, symbol_info),
        "deviation": 20,
        "type_filling": filling,
        "comment": "Setup 9.1 Buy Stop",
        "magic": config.MAGIC,
        "expiration": 0,
    }
    return _send_order(request)


def place_sell_stop(symbol, entry_price, sl_price):
    symbol_info = get_symbol_info(symbol)
    if symbol_info is None:
        return None

    volume = _normalize_volume(config.VOLUME_INITIAL, symbol_info)
    filling = _get_filling_type(symbol_info)

    request = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": volume,
        "type": mt5.ORDER_TYPE_SELL_STOP,
        "price": _format_price(entry_price, symbol_info),
        "sl": _format_price(sl_price, symbol_info),
        "deviation": 20,
        "type_filling": filling,
        "comment": "Setup 9.1 Sell Stop",
        "magic": config.MAGIC,
        "expiration": 0,
    }
    return _send_order(request)


def place_buy_stop_92(symbol, entry_price, sl_price):
    """Coloca ordem BUY STOP para Setup 9.2."""
    symbol_info = get_symbol_info(symbol)
    if symbol_info is None:
        return None

    volume = _normalize_volume(config.VOLUME_INITIAL, symbol_info)
    filling = _get_filling_type(symbol_info)

    request = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": volume,
        "type": mt5.ORDER_TYPE_BUY_STOP,
        "price": _format_price(entry_price, symbol_info),
        "sl": _format_price(sl_price, symbol_info),
        "deviation": 20,
        "type_filling": filling,
        "comment": "Setup 9.2 Buy Stop",
        "magic": config.MAGIC,
        "expiration": 0,
    }
    return _send_order(request)


def place_sell_stop_92(symbol, entry_price, sl_price):
    """Coloca ordem SELL STOP para Setup 9.2."""
    symbol_info = get_symbol_info(symbol)
    if symbol_info is None:
        return None

    volume = _normalize_volume(config.VOLUME_INITIAL, symbol_info)
    filling = _get_filling_type(symbol_info)

    request = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": volume,
        "type": mt5.ORDER_TYPE_SELL_STOP,
        "price": _format_price(entry_price, symbol_info),
        "sl": _format_price(sl_price, symbol_info),
        "deviation": 20,
        "type_filling": filling,
        "comment": "Setup 9.2 Sell Stop",
        "magic": config.MAGIC,
        "expiration": 0,
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
    position_type: TradeSide enum (BUY ou SELL) da strategy.
    Converte internamente para comparacao com mt5 constants.
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

    # position_type e TradeSide enum; comparar pelo valor ou nome
    # TradeSide.BUY.value == 1, TradeSide.SELL.value == 2
    is_buy = (hasattr(position_type, 'value') and position_type.value == 1) or position_type == mt5.ORDER_TYPE_BUY
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