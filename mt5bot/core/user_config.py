"""config.toml do usuario sobrepondo os padroes de config.py (spec 003 FR-3/FR-4).

Exemplo (<pasta de dados>/config.toml):

    quant_max_risk_pct = 2.0          # perda maxima no SL, % do saldo (padrao das rotas)
    max_daily_loss_percent = 2.0

    [routes.US500]
    max_risk_pct = 12.0               # limite proprio da rota
    enabled = true                    # false desliga a rota

    [routes.US100]
    mode = "live"                     # "study" = ordens virtuais; "live" = opera de verdade

Valores invalidos (tipo errado ou fora da faixa) sao recusados com mensagem que
cita o arquivo e a chave; o padrao de config.py e mantido. Nunca derruba o robo.
"""
import logging
import os

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

from mt5bot.core import paths

# chave no toml -> (nome em config.py, tipo, minimo, maximo)
GLOBAL_KEYS = {
    "quant_max_risk_pct": ("QUANT_MAX_RISK_PCT", float, 0.1, 50.0),
    "quant_margin_reserve_mult": ("QUANT_MARGIN_RESERVE_MULT", float, 1.0, 20.0),
    "max_daily_loss_percent": ("MAX_DAILY_LOSS_PERCENT", float, 0.1, 50.0),
    "max_risk_per_trade_percent": ("MAX_RISK_PER_TRADE_PERCENT", float, 0.1, 10.0),
    "ml_filter_enabled": ("ML_FILTER_ENABLED", bool, None, None),
    "allow_unvalidated_live": ("ALLOW_UNVALIDATED_LIVE", bool, None, None),
    "live_confirmed": ("LIVE_CONFIRMED", bool, None, None),
}
ROUTE_KEYS = {
    "max_risk_pct": (float, 0.1, 50.0),
    "enabled": (bool, None, None),
    "mode": (str, None, None),  # "study" (ordens virtuais) ou "live"
}
ROUTE_MODES = ("study", "live")


def _check(value, kind, lo, hi):
    """Valor convertido ou None. bool nao e aceito como numero (True == 1)."""
    if kind is bool:
        return value if isinstance(value, bool) else None
    if kind is str:
        return value.lower() if isinstance(value, str) and value.lower() in ROUTE_MODES else None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if lo <= value <= hi else None


def _fmt_range(kind, lo, hi):
    if kind is str:
        return " ou ".join(f'"{m}"' for m in ROUTE_MODES)
    return "true/false" if kind is bool else f"numero entre {lo:g} e {hi:g}"


def apply(cfg: dict, path: str = None) -> list:
    """Aplica o config.toml sobre o namespace de config.py. Devolve os erros."""
    path = path or paths.config_file()
    sources = cfg.setdefault("CONFIG_SOURCES", {})
    cfg["USER_CONFIG_FILE"] = path
    if not os.path.exists(path):
        return []
    try:
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError) as e:
        msg = f"{path}: arquivo invalido ({e}). Usando os padroes."
        logging.warning(msg)
        return [msg]

    errors = []

    def bad(key, value, kind, lo, hi):
        msg = f"{path}: '{key}' = {value!r} recusado ({_fmt_range(kind, lo, hi)}). Mantido o padrao."
        logging.warning(msg)
        errors.append(msg)

    for key, value in data.items():
        if key == "routes":
            continue
        if key not in GLOBAL_KEYS:
            msg = f"{path}: chave desconhecida '{key}' ignorada."
            logging.warning(msg)
            errors.append(msg)
            continue
        name, kind, lo, hi = GLOBAL_KEYS[key]
        checked = _check(value, kind, lo, hi)
        if checked is None:
            bad(key, value, kind, lo, hi)
        else:
            cfg[name] = checked
            sources[name] = "config.toml"

    routes = cfg.get("QUANT_ROUTES", {})
    for symbol, overrides in (data.get("routes") or {}).items():
        if symbol not in routes or not isinstance(overrides, dict):
            msg = f"{path}: rota '{symbol}' nao existe em QUANT_ROUTES; ignorada."
            logging.warning(msg)
            errors.append(msg)
            continue
        for key, value in overrides.items():
            full = f"routes.{symbol}.{key}"
            if key not in ROUTE_KEYS:
                msg = f"{path}: chave desconhecida '{full}' ignorada."
                logging.warning(msg)
                errors.append(msg)
                continue
            kind, lo, hi = ROUTE_KEYS[key]
            checked = _check(value, kind, lo, hi)
            if checked is None:
                bad(full, value, kind, lo, hi)
            elif key == "enabled":
                if not checked:
                    routes.pop(symbol)
                    sources[f"QUANT_ROUTES.{symbol}"] = "config.toml (desligada)"
                    break
            else:
                routes[symbol] = dict(routes[symbol], **{key: checked})
                sources[f"QUANT_ROUTES.{symbol}.{key}"] = "config.toml"
    return errors


def set_value(key: str, value, path: str = None) -> str:
    """Grava `key = value` (chave global) no config.toml, preservando o resto.

    Substitui a linha da chave, comentada ou nao; se nao existir, acrescenta no
    topo (antes das secoes [routes.*], onde chaves globais precisam ficar).
    """
    import re
    if key not in GLOBAL_KEYS:
        raise KeyError(key)
    path = path or paths.config_file()
    literal = str(value).lower() if isinstance(value, bool) else repr(value)
    line = f"{key} = {literal}"
    text = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
    pattern = re.compile(rf"(?m)^[ \t]*#?[ \t]*{re.escape(key)}[ \t]*=.*$")
    if pattern.search(text):
        text = pattern.sub(line, text, count=1)
    else:
        text = line + "\n" + text
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path

