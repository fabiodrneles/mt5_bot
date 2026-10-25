import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from mt5bot.core import config
from mt5bot.core import terminal


def _balance():
    """Saldo atual do MT5 (None se o terminal nao estiver disponivel)."""
    try:
        import MetaTrader5 as mt5
        if not terminal.initialize():
            return None
        acc = mt5.account_info()
        return float(acc.balance) if acc else None
    except Exception:
        return None


def run_show_config():
    print("="*50)
    print("            CONFIGURACOES DO MT5BOT            ")
    print("="*50)

    # Risco (Maestro / setups classicos)
    risco = getattr(config, 'MAX_RISK_PER_TRADE_PERCENT', 1.0)
    risco_abs = getattr(config, 'ABSOLUTE_MAX_TRADE_RISK_PERCENT', 1.5)
    risco_max = getattr(config, 'MAX_DAILY_LOSS_PERCENT', 2.0)
    src = getattr(config, "CONFIG_SOURCES", {})
    tag = lambda key: " [config.toml]" if key in src else ""
    print(f"Config do usuario: {getattr(config, 'USER_CONFIG_FILE', '?')}"
          + ("" if os.path.exists(getattr(config, "USER_CONFIG_FILE", "")) else " (nao existe; usando padroes)"))
    for erro in getattr(config, "USER_CONFIG_ERRORS", []):
        print(f"  ! {erro}")
    print(f"Risco por Trade: {risco}%{tag('MAX_RISK_PER_TRADE_PERCENT')} (teto {risco_abs}%)"
          f" | Max Perda Diaria: {risco_max}%{tag('MAX_DAILY_LOSS_PERCENT')}")

    # Filtro ML
    ml = getattr(config, 'ML_FILTER_ENABLED', False)
    ml_prob = getattr(config, 'ML_MIN_WIN_PROB', 0.40)
    print(f"Filtro XGBoost: {'ON' if ml else 'OFF'} | Probabilidade Minima: {ml_prob*100:.0f}%")

    # Rotas quant (bot.bat quant / Maestro /add ATIVO TF)
    rotas = getattr(config, 'QUANT_ROUTES', {}) or {}
    print("-"*50)
    print("ROTAS QUANT (bot.bat quant):")
    if not rotas:
        print("  (nenhuma)")
    max_pct = getattr(config, 'QUANT_MAX_RISK_PCT', 2.0)
    reserva = getattr(config, 'QUANT_MARGIN_RESERVE_MULT', 3.0)
    saldo = _balance()
    for simbolo, rota in rotas.items():
        params = ", ".join(f"{k}={v}" for k, v in (rota.get('params') or {}).items())
        print(f"  {simbolo:6} {rota.get('timeframe', '?'):3} {rota.get('setup', '?'):7} {params}")
        if rota.get('max_risk_pct') is not None:
            pct = float(rota['max_risk_pct'])
            em_usd = f" = ${saldo * pct / 100:.2f}" if saldo else ""
            print(f"         limite proprio: {pct}% do saldo{em_usd}{tag(f'QUANT_ROUTES.{simbolo}.max_risk_pct')}")
    limite = f" = ${saldo * max_pct / 100:.2f} com saldo ${saldo:.2f}" if saldo else ""
    print(f"  Perda max. no SL (padrao): {max_pct}% do saldo{limite}{tag('QUANT_MAX_RISK_PCT')}"
          f" | Reserva de margem: {reserva}x{tag('QUANT_MARGIN_RESERVE_MULT')}")

    # Setups classicos (Maestro)
    print("-"*50)
    setups = getattr(config, 'CONFIG_SETUPS', {})
    ligados = [s for s, on in setups.items() if on]
    print(f"Setups Classicos Habilitados: {ligados}")
    print("Setups por Ativo (Maestro):")
    for ativo, lista in (getattr(config, 'ASSET_SETUPS', {}) or {}).items():
        print(f"  {ativo:8} {lista}")

    print("="*50)

def config_template():
    """Modelo comentado e valido do config.toml (spec 003 FR-5).

    Tudo comentado: o arquivo novo nao muda nada ate o usuario descomentar.
    """
    lines = [
        "# config.toml do MT5Bot - sobrepoe os padroes de mt5bot/core/config.py.",
        "# Descomente (tire o #) so o que quiser mudar. Valores invalidos sao",
        "# recusados com aviso e o padrao e mantido. Confira com: bot.bat config",
        "",
        "# Perda maxima no stop, em % do saldo, para as rotas sem limite proprio.",
        f"# quant_max_risk_pct = {config.QUANT_MAX_RISK_PCT}",
        "",
        "# Margem livre que precisa sobrar depois de abrir (x margem da posicao).",
        f"# quant_margin_reserve_mult = {config.QUANT_MARGIN_RESERVE_MULT}",
        "",
        "# Trava diaria: bloqueia novas entradas depois de perder X% no dia.",
        f"# max_daily_loss_percent = {config.MAX_DAILY_LOSS_PERCENT}",
        "",
        "# Risco por trade dos setups classicos (Maestro).",
        f"# max_risk_per_trade_percent = {config.MAX_RISK_PER_TRADE_PERCENT}",
        "",
        "# Veto do XGBoost nos setups classicos.",
        f"# ml_filter_enabled = {str(config.ML_FILTER_ENABLED).lower()}",
        "",
        "# Setups SEM validacao fora da amostra operando ao vivo (risco maior).",
        f"# allow_unvalidated_live = {str(getattr(config, 'ALLOW_UNVALIDATED_LIVE', False)).lower()}",
        "",
        "# Confirmacao de conta REAL (prefira gravar pelo assistente: bot.bat setup).",
        f"# live_confirmed = {str(getattr(config, 'LIVE_CONFIRMED', False)).lower()}",
        "",
        "# Terminal MT5 da corretora (quando ha mais de um instalado, ex.: Hantec e Clear). Apague os dois '#'",
        "# e troque pelo caminho do terminal64.exe da corretora desejada; o login salvo nele e usado.",
        '## mt5_path = "C:/Program Files/MetaTrader 5/terminal64.exe"',
    ]
    for symbol, route in (getattr(config, "QUANT_ROUTES", {}) or {}).items():
        lines += ["", f"# Rota {symbol} {route['timeframe']} {route['setup']}",
                  f"# [routes.{symbol}]",
                  f"# max_risk_pct = {route.get('max_risk_pct', config.QUANT_MAX_RISK_PCT)}",
                  f'# mode = "{route.get("mode", "live")}"   # "study" = ordens virtuais; "live" = opera de verdade',
                  "# enabled = true"]
    return "\n".join(lines) + "\n"


def edit_config(open_editor=True):
    """Cria o config.toml comentado (se nao existir) e abre no editor."""
    import subprocess
    path = config.USER_CONFIG_FILE
    created = not os.path.exists(path)
    if created:
        with open(path, "w", encoding="utf-8") as f:
            f.write(config_template())
    print(("Criado: " if created else "Ja existe (nao foi alterado): ") + path)
    if open_editor:
        if sys.platform == "win32":
            subprocess.Popen(["notepad.exe", path])
        else:
            editor = os.environ.get("EDITOR") or ("open" if sys.platform == "darwin" else "xdg-open")
            subprocess.Popen([editor, path])
    return path, created


if __name__ == "__main__":
    if "--edit" in sys.argv[1:]:
        edit_config(open_editor="--no-open" not in sys.argv[1:])
    else:
        run_show_config()
