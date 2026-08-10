import json
import os
import time
import logger
import config


def _get_data_dir():
    """Retorna o diretório onde salvar arquivos de estado/trades.
    Por padrão usa '%APPDATA%/mt5bot' no Windows ou '~/.mt5bot' em outros sistemas.
    Isso evita gravar em site-packages onde o usuário não tem controle fácil e onde
    arquivos podem ficar corrompidos após reinstalação.
    """
    appdata = os.getenv('APPDATA') or os.getenv('LOCALAPPDATA')
    if appdata:
        base = os.path.join(appdata, 'mt5bot')
    else:
        base = os.path.join(os.path.expanduser('~'), '.mt5bot')
    try:
        os.makedirs(base, exist_ok=True)
    except Exception:
        base = os.path.dirname(os.path.abspath(__file__))
    return base


def _get_path():
    return os.path.join(_get_data_dir(), config.STATE_FILE)

def _json_default(obj):
    """Converte tipos numpy para tipos nativos do Python (serializaveis por JSON)."""
    try:
        import numpy as np
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
    except ImportError:
        pass
    return str(obj)


def save_states(symbol_states):
    """Salva o estado de todos os simbolos em JSON."""
    # Construir dicionario de estados e garantir que todos os valores sejam
    # nativos do Python (int, float, str, list, dict) para evitar erros do
    # json.dump com tipos como numpy.int64 provenientes do MetaTrader5.
    def _convert_value(v):
        try:
            import numpy as _np
        except Exception:
            _np = None

        # Tipos numpy
        if _np is not None:
            if isinstance(v, _np.integer):
                return int(v)
            if isinstance(v, _np.floating):
                return float(v)
            if isinstance(v, _np.ndarray):
                return v.tolist()

        # Tipos compostos
        if isinstance(v, dict):
            return {k: _convert_value(val) for k, val in v.items()}
        if isinstance(v, (list, tuple)):
            return [_convert_value(x) for x in v]

        # Datetimes -> isoformat
        if hasattr(v, "isoformat"):
            try:
                return v.isoformat()
            except Exception:
                pass

        return v

    data = {}
    for symbol, s_state in symbol_states.items():
        data[symbol] = {
            "state": _convert_value(s_state.state.name),
            "pending_order_ticket": _convert_value(s_state.pending_order_ticket),
            "position_ticket": _convert_value(s_state.position_ticket),
            "position_type": _convert_value(s_state.position_type.name if s_state.position_type else None),
            "candle_referencia": _convert_value(list(s_state.candle_referencia) if s_state.candle_referencia else None),
            "entry_price": _convert_value(s_state.entry_price),
            "sl_price": _convert_value(s_state.sl_price),
            "partial_exit_done": _convert_value(s_state.partial_exit_done),
            "watching_92_candles": _convert_value(getattr(s_state, "watching_92_candles", 0)),
            "setup_type": _convert_value(getattr(s_state, "setup_type", "9.1")),
            "exit_profit": _convert_value(getattr(s_state, "exit_profit", None)),
        }

    try:
        path = _get_path()
        tmp_path = path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=_json_default)
        os.replace(tmp_path, path)
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
        backup_path = path + f".corrupt.{int(time.time())}"
        try:
            os.replace(path, backup_path)
            logger.warning(f"Arquivo de estado corrompido. Backup salvo em {backup_path}")
            logger.warning("Verifique posicoes abertas no MT5 manualmente antes de reiniciar o bot.")
        except Exception as backup_error:
            logger.error(f"Falha ao criar backup do state corrompido: {backup_error}", exc_info=True)
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