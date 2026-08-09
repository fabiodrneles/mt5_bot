import json
import os
import logger
import config


state_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), config.STATE_FILE)


def _get_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), config.STATE_FILE)


def save_states(symbol_states):
    """Salva o estado de todos os simbolos em JSON."""
    data = {}
    for symbol, s_state in symbol_states.items():
        data[symbol] = {
            "state": s_state.state.name,
            "pending_order_ticket": s_state.pending_order_ticket,
            "position_ticket": s_state.position_ticket,
            "position_type": s_state.position_type.name if s_state.position_type else None,
            "candle_referencia": list(s_state.candle_referencia) if s_state.candle_referencia else None,
            "entry_price": s_state.entry_price,
            "sl_price": s_state.sl_price,
            "partial_exit_done": s_state.partial_exit_done,
            "watching_92_candles": getattr(s_state, "watching_92_candles", 0),
            "setup_type": getattr(s_state, "setup_type", "9.1"),
            "exit_profit": getattr(s_state, "exit_profit", None),
        }

    try:
        path = _get_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.debug(f"Estados salvos em {path}")
    except Exception as e:
        logger.error(f"Erro ao salvar estados: {e}", exc_info=True)


def load_states():
    """Carrega estados do arquivo JSON. Retorna dict ou None se nao existir."""
    path = _get_path()
    if not os.path.exists(path):
        logger.info("Arquivo de estado nao encontrado. Iniciando do zero.")
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info(f"Estados carregados de {path}")
        return data
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Erro ao carregar estados: {e}", exc_info=True)
        return None


def apply_loaded_states(symbol_states, loaded_data, State, TradeSide):
    """Aplica dados carregados aos SymbolState objects.
    Retorna True se algum estado foi restaurado.
    """
    if loaded_data is None:
        return False

    restored = False
    for symbol, s_state in symbol_states.items():
        if symbol not in loaded_data:
            continue

        saved = loaded_data[symbol]
        try:
            s_state.state = State[saved["state"]]
            s_state.pending_order_ticket = saved.get("pending_order_ticket")
            s_state.position_ticket = saved.get("position_ticket")

            pt = saved.get("position_type")
            s_state.position_type = TradeSide[pt] if pt else None

            cr = saved.get("candle_referencia")
            s_state.candle_referencia = tuple(cr) if cr else None

            s_state.entry_price = saved.get("entry_price")
            s_state.sl_price = saved.get("sl_price")
            s_state.partial_exit_done = saved.get("partial_exit_done", False)
            s_state.watching_92_candles = saved.get("watching_92_candles", 0)
            s_state.setup_type = saved.get("setup_type", "9.1")
            s_state.exit_profit = saved.get("exit_profit")

            if s_state.state.name != "SCANNING":
                restored = True
                logger.info(f"[{symbol}] Estado restaurado: {s_state.state.name} "
                           f"(ticket={s_state.position_ticket or s_state.pending_order_ticket})")
        except (KeyError, ValueError) as e:
            logger.warning(f"[{symbol}] Erro ao restaurar estado, resetando: {e}")
            s_state.state = State.SCANNING

    return restored