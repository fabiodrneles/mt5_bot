"""Assistente de primeiro uso do MT5Bot (spec 006).

Uso:  bot.bat setup      (ou: python tools/setup_wizard.py)

Passos:
  1. Conecta no MT5; sem terminal aberto, explica e sai (nunca trava).
  2. Confere o botao Algo Trading e os ativos das rotas na Observacao do Mercado.
  3. Mostra conta (REAL/DEMO), saldo e, por rota, o risco por trade x limite.
  4. Em conta REAL, so libera o modo ao vivo com confirmacao explicita
     (digitar CONFIRMO), gravada no config.toml como live_confirmed = true.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import MetaTrader5 as mt5  # noqa: E402
import pandas as pd  # noqa: E402

from mt5bot.core import config, telemetry, user_config  # noqa: E402
from mt5bot.core import terminal  # noqa: E402

TF = {"M15": mt5.TIMEFRAME_M15, "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4, "D1": mt5.TIMEFRAME_D1}
CONFIRM_WORD = "CONFIRMO"


def check_environment():
    """Diagnostico sem efeitos colaterais. Devolve dict com problemas e rotas."""
    report = {"connected": False, "problems": [], "routes": [], "account": None}
    if not terminal.initialize():
        report["problems"].append(
            "Nao consegui conectar no MetaTrader 5. Abra o terminal, faca login na corretora e rode de novo.")
        return report
    report["connected"] = True
    term = mt5.terminal_info()
    if term is not None and not getattr(term, "trade_allowed", True):
        report["problems"].append(
            "O botao 'Algo Trading' esta DESLIGADO no MT5. Clique nele na barra de ferramentas (fica verde).")
    acc = telemetry.account_snapshot()
    report["account"] = acc
    balance = (acc or {}).get("balance", 0.0)
    for key, route in (getattr(config, "QUANT_ROUTES", {}) or {}).items():
        symbol = route.get("symbol", key)
        row = {"symbol": key, "tf": route["timeframe"], "setup": route["setup"], "risk": None, "limit": None,
               "study": str(route.get("mode", "live")).lower() == "study"}
        if not mt5.symbol_select(symbol, True):
            report["problems"].append(
                f"O ativo {symbol} nao esta disponivel na sua corretora/Observacao do Mercado.")
            report["routes"].append(row)
            continue
        rates = mt5.copy_rates_from_pos(symbol, TF.get(route["timeframe"], mt5.TIMEFRAME_H1), 1, 200)
        if rates is not None and len(rates):
            row["risk"], row["limit"] = telemetry.route_risk(symbol, route, pd.DataFrame(rates), balance)
        report["routes"].append(row)
    return report


def render(report):
    out = []
    acc = report["account"]
    if acc:
        kind = "REAL (dinheiro de verdade)" if acc["real"] else "DEMO (sem risco)"
        out.append(f"Conta {acc['login']}: {kind} | saldo ${acc['balance']:.2f} | margem livre ${acc['margin_free']:.2f}")
    if report["routes"]:
        out.append("")
        out.append("Rotas validadas e o risco de cada trade no seu saldo:")
    for r in report["routes"]:
        name = f"{r['symbol']} {r['tf']} {r['setup']}"
        if r.get("study"):
            out.append(f"  - {name}: ESTUDO -> simula as entradas e saidas sem enviar ordens (nao usa dinheiro)")
        elif r["risk"] is None:
            out.append(f"  - {name}: sem dados agora")
        elif r["risk"] <= r["limit"]:
            out.append(f"  - {name}: perde ate ${r['risk']:.2f} por trade (limite ${r['limit']:.2f}) -> OPERA")
        else:
            out.append(f"  - {name}: perderia ${r['risk']:.2f} (limite ${r['limit']:.2f}) -> TRAVADA para proteger a margem")
    if report["problems"]:
        out.append("")
        out.append("Precisa de atencao:")
        out += [f"  ! {p}" for p in report["problems"]]
    return "\n".join(out)


def confirm_real(ask=input):
    """Pede a confirmacao explicita; grava live_confirmed no config.toml."""
    print()
    print("ATENCAO: esta e uma conta REAL. Resultados passados nao garantem resultados futuros,")
    print("e cada trade pode perder o valor mostrado acima. Recomendado: teste antes numa conta DEMO.")
    try:
        answer = ask(f"Para liberar o robo nesta conta REAL, digite {CONFIRM_WORD} (ou Enter para nao liberar): ")
    except (EOFError, KeyboardInterrupt):
        # Entrada fechada (script, pipe) ou Ctrl+C: nunca libera por omissao.
        answer = ""
        print()
    if answer.strip().upper() != CONFIRM_WORD:
        print("Nao liberado. O robo continua sem abrir posicoes nesta conta. Rode 'bot.bat setup' quando quiser.")
        return False
    path = user_config.set_value("live_confirmed", True)
    print(f"Liberado. Gravei live_confirmed = true em {path}.")
    print("Para desfazer: bot.bat config --edit e troque para false.")
    return True


def main(ask=input):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print("=" * 64)
    print("  MT5Bot - assistente de configuracao")
    print("=" * 64)
    report = check_environment()
    print(render(report))
    if not report["connected"]:
        return 1
    acc = report["account"] or {}
    if acc.get("real"):
        if getattr(config, "LIVE_CONFIRMED", False):
            print("\nConta REAL ja confirmada anteriormente (live_confirmed = true).")
        elif sys.stdin is None or not sys.stdin.isatty():
            print("\nConta REAL sem confirmacao. Rode 'bot.bat setup' numa janela interativa para liberar.")
            return 2
        elif not confirm_real(ask):
            return 2
    else:
        print("\nConta DEMO: o robo pode operar sem confirmacao. Bom lugar para testar!")
    print("\nPronto. Para ligar: bot.bat quant  |  painel web: bot.bat dashboard")
    return 0


if __name__ == "__main__":
    sys.exit(main())
