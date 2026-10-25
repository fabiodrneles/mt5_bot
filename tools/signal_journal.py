"""Diario de sinais (bot.bat anotar / bot.bat diario).

  bot.bat anotar                                   pergunta tudo
  bot.bat anotar US500 M15 venda bom "motivo"      direto (alvo 2x; use --alvo 1 para 1x)
  bot.bat diario                                   mede os resultados e mostra a estatistica

A hora e o preco de entrada sao gravados no momento da anotacao (nao da para anotar sinal passado).
Stop padrao: maxima (venda) / minima (compra) do ultimo candle FECHADO do tempo grafico. O resultado e
medido com candles de 1 minuto do MT5, com o spread na venda e o valor no lote minimo (order_calc_profit).
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import MetaTrader5 as mt5  # noqa: E402

from mt5bot.data import signal_journal as J  # noqa: E402
from mt5bot.core import terminal  # noqa: E402

TFS = {"M1": "TIMEFRAME_M1", "M5": "TIMEFRAME_M5", "M15": "TIMEFRAME_M15", "M30": "TIMEFRAME_M30",
       "H1": "TIMEFRAME_H1", "H4": "TIMEFRAME_H4", "D1": "TIMEFRAME_D1"}
EXPIRE_DAYS = 5
MAX_QUOTE_AGE = 600  # segundos


def connect():
    if not terminal.initialize():
        raise SystemExit(f"MT5 indisponivel: {mt5.last_error()}. Abra o terminal e faca login.")


def ask(prompt, valid=None, default=None):
    while True:
        v = input(f"{prompt}{f' [{default}]' if default else ''}: ").strip() or (default or "")
        if not valid or v.lower() in valid:
            return v
        print(f"  Opcoes: {', '.join(valid)}")


def annotate(args):
    alvo_r = 2.0
    if "--alvo" in args:
        i = args.index("--alvo")
        alvo_r = float(args[i + 1])
        args = args[:i] + args[i + 2:]
    if len(args) >= 4:
        sym, tf, lado, aval = args[0], args[1].upper(), args[2].lower(), args[3].lower()
        motivo = " ".join(args[4:])
    else:
        sym = ask("Ativo (ex.: US500)")
        tf = ask("Tempo grafico", [k.lower() for k in TFS], "m15").upper()
        lado = ask("Direcao", ["compra", "venda"])
        aval = ask("Voce acha que e um sinal bom ou ruim", ["bom", "ruim"])
        motivo = ask("Por que? (o que voce viu: tendencia, volume, horario...)", default="-")
    if tf not in TFS or lado not in ("compra", "venda") or aval not in ("bom", "ruim"):
        raise SystemExit("Uso: bot.bat anotar ATIVO TF compra|venda bom|ruim \"motivo\" [--alvo 2]")
    connect()
    if not mt5.symbol_select(sym, True):
        raise SystemExit(f"Ativo {sym} nao encontrado no MT5.")
    tick = mt5.symbol_info_tick(sym)
    bars = mt5.copy_rates_from_pos(sym, getattr(mt5, TFS[tf]), 1, 1)  # ultimo candle FECHADO
    if tick is None or bars is None or len(bars) == 0:
        raise SystemExit("Sem cotacao agora (mercado fechado?). Anote quando o mercado estiver aberto.")
    last_quote = max((x["time"] for x in (mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M1, 0, 1) or [])), default=0)
    if time.time() - max(int(tick.time), int(last_quote)) > MAX_QUOTE_AGE:
        # Mercado fechado: a ultima cotacao e antiga e o resultado seria medido a partir de um preco
        # que nao da para executar.
        raise SystemExit("Mercado fechado (a ultima cotacao tem mais de 10 minutos). Anote com o mercado aberto.")
    d = 1 if lado == "compra" else -1
    entry = tick.ask if d > 0 else tick.bid
    stop, alvo = J.default_levels(d, entry, float(bars[0]["high"]), float(bars[0]["low"]), alvo_r)
    vmin = mt5.symbol_info(sym).volume_min
    order = mt5.ORDER_TYPE_BUY if d > 0 else mt5.ORDER_TYPE_SELL
    risk_usd = abs(mt5.order_calc_profit(order, sym, vmin, entry, stop) or 0.0)
    entries = J.load()
    e = J.Entry(id=max([x.id for x in entries], default=0) + 1, anotado_em_utc=int(tick.time), ativo=sym, tf=tf,
                lado=lado, avaliacao=aval, motivo=motivo, preco_entrada=entry, stop=stop, alvo=alvo, alvo_r=alvo_r,
                candle_sinal_utc=int(bars[0]["time"]), risco_usd=round(risk_usd, 4))
    path = J.save(entries + [e])
    print(f"Anotado #{e.id}: {lado.upper()} {sym} {tf} a {entry} | stop {stop} | alvo {alvo:.5g} ({alvo_r:g}x) | "
          f"risco no lote minimo ${risk_usd:.2f} | avaliacao: {aval}")
    print(f"Arquivo: {path}")


def evaluate(entries):
    connect()
    now = int(time.time())
    changed = False
    for e in entries:
        if e.status != J.OPEN:
            continue
        rates = mt5.copy_rates_range(e.ativo, mt5.TIMEFRAME_M1, e.anotado_em_utc + 60, now)
        info = mt5.symbol_info(e.ativo)
        if rates is None or info is None:
            continue
        rates = [r for r in rates if int(r["time"]) > e.anotado_em_utc]  # so o que veio DEPOIS da anotacao
        status, px, i = J.evaluate_path(e.direction, e.preco_entrada, e.stop, e.alvo,
                                        [r["high"] for r in rates], [r["low"] for r in rates],
                                        [r["spread"] * info.point for r in rates])
        if status == J.OPEN and rates and now - e.anotado_em_utc > EXPIRE_DAYS * 86400:
            status, px, i = J.EXPIRED, float(rates[-1]["close"]), len(rates) - 1
        if status != J.OPEN:
            order = mt5.ORDER_TYPE_BUY if e.direction > 0 else mt5.ORDER_TYPE_SELL
            e.resultado_usd = round(mt5.order_calc_profit(order, e.ativo, info.volume_min, e.preco_entrada, px) or 0.0, 4)
            e.status, e.saida_em_utc = status, int(rates[i]["time"])
            changed = True
    if changed:
        J.save(entries)
    return entries


def report(entries):
    if not entries:
        print("Diario vazio. Anote um sinal com: bot.bat anotar")
        return
    print(f"{'#':>3} {'anotado (UTC)':<17} {'ativo':<8} {'tf':<4} {'lado':<6} {'aval.':<5} {'status':<9} {'resultado':>9}  motivo")
    for e in entries:
        when = time.strftime("%d/%m/%Y %H:%M", time.gmtime(e.anotado_em_utc))
        res = f"${e.resultado_usd:+.2f}" if e.status != J.OPEN else "-"
        print(f"{e.id:>3} {when:<17} {e.ativo:<8} {e.tf:<4} {e.lado:<6} {e.avaliacao:<5} {e.status:<9} {res:>9}  {e.motivo}")
    s = J.summary(entries)
    print()
    for label in ("bom", "ruim"):
        x = s[label]
        if x["n"] == 0:
            print(f"Sinais '{label}': nenhum encerrado ainda.")
            continue
        print(f"Sinais '{label}': {x['n']} encerrados, acerto {x['win_rate'] * 100:.0f}% "
              f"(empate exige {x['breakeven'] * 100:.0f}%), resultado ${x['total_usd']:+.2f}, "
              f"chance de ser sorte {x['p_sorte'] * 100:.0f}%")
    b = s["bom"]
    if b["n"] < 30:
        print(f"\nAinda e cedo: com {b['n']} sinais 'bom' encerrados, a sorte explica quase qualquer resultado. "
              "Meta: 30 ou mais.")
    elif b["p_sorte"] < 0.05 and b["total_usd"] > 0:
        print("\nO seu olho mostra vantagem estatistica (chance de sorte < 5%). Hora de transformar o criterio em robo.")
    else:
        print("\nAte aqui, o acerto dos sinais 'bom' nao se distingue da sorte.")


def main(argv):
    if not argv or argv[0] not in ("anotar", "diario"):
        print(__doc__)
        return 1
    if argv[0] == "anotar":
        annotate(argv[1:])
    else:
        report(evaluate(J.load()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
