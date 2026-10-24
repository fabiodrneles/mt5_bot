import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from mt5bot.core import config


def _balance():
    """Saldo atual do MT5 (None se o terminal nao estiver disponivel)."""
    try:
        import MetaTrader5 as mt5
        if not mt5.initialize():
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
    print(f"Risco por Trade: {risco}% (teto {risco_abs}%) | Max Perda Diaria: {risco_max}%")

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
            print(f"         limite proprio: {pct}% do saldo{em_usd}")
    limite = f" = ${saldo * max_pct / 100:.2f} com saldo ${saldo:.2f}" if saldo else ""
    print(f"  Perda max. no SL (padrao): {max_pct}% do saldo{limite} | Reserva de margem: {reserva}x")

    # Setups classicos (Maestro)
    print("-"*50)
    setups = getattr(config, 'CONFIG_SETUPS', {})
    ligados = [s for s, on in setups.items() if on]
    print(f"Setups Classicos Habilitados: {ligados}")
    print("Setups por Ativo (Maestro):")
    for ativo, lista in (getattr(config, 'ASSET_SETUPS', {}) or {}).items():
        print(f"  {ativo:8} {lista}")

    print("="*50)

if __name__ == "__main__":
    run_show_config()
