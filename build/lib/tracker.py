"""
Rastreador de operacoes — registra todas as entradas/saidas e calcula performance.
Salva historico em trades.json para relatorio financeiro.
"""
import json
import os
from datetime import datetime, timezone

import logger

_TRADES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trades.json")


def _load_trades():
    """Carrega historico de trades do arquivo."""
    if not os.path.exists(_TRADES_FILE):
        return []
    try:
        with open(_TRADES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def _save_trades(trades):
    """Salva historico de trades."""
    try:
        with open(_TRADES_FILE, "w", encoding="utf-8") as f:
            json.dump(trades, f, indent=2, ensure_ascii=False)
    except IOError as e:
        logger.error(f"Erro ao salvar trades: {e}", exc_info=True)


def record_entry(symbol, side, setup_type, entry_price, sl_price, volume, ticket):
    """Registra uma entrada (posicao aberta)."""
    trades = _load_trades()
    trade = {
        "id": len(trades) + 1,
        "symbol": symbol,
        "side": side,
        "setup": setup_type,
        "entry_price": entry_price,
        "sl_price": sl_price,
        "volume": volume,
        "ticket": ticket,
        "entry_time": datetime.now(tz=timezone.utc).isoformat(),
        "exit_price": None,
        "exit_time": None,
        "pnl": None,
        "pnl_pips": None,
        "result": "open",
        "partial_exit_price": None,
        "partial_volume": None,
    }
    trades.append(trade)
    _save_trades(trades)
    logger.debug(f"[Tracker] Entrada registrada: {symbol} {side} {setup_type} @ {entry_price}")
    return trade["id"]


def record_partial_exit(ticket, exit_price, volume_closed):
    """Registra saida parcial."""
    trades = _load_trades()
    for trade in reversed(trades):
        if trade.get("ticket") == ticket and trade["result"] == "open":
            trade["partial_exit_price"] = exit_price
            trade["partial_volume"] = volume_closed
            break
    _save_trades(trades)


def _calculate_pnl_money(symbol, pnl_pips, volume):
    """Calcula P&L em dinheiro (moeda da conta).

    Formula: pnl_money = (pnl_em_pontos / point) * tick_value * volume
    Onde tick_value = quanto vale 1 tick de movimento no lote minimo.

    Se MT5 nao estiver disponivel, usa estimativa simplificada.
    """
    try:
        import MetaTrader5 as mt5
        sym_info = mt5.symbol_info(symbol)
        if sym_info and sym_info.trade_tick_value > 0:
            # tick_value = valor monetario de 1 tick para 1 lote
            # pnl_em_ticks = pnl_pips / tick_size
            tick_size = sym_info.trade_tick_size if sym_info.trade_tick_size > 0 else sym_info.point
            pnl_ticks = pnl_pips / tick_size
            pnl_money = pnl_ticks * sym_info.trade_tick_value * volume
            return round(pnl_money, 2)
    except Exception:
        pass

    # Fallback: estimativa grosseira (funciona razoavelmente para forex com conta USD)
    # Para indices (HK50, US500), o valor por ponto varia muito
    return None


def record_exit(ticket, exit_price, result="win"):
    """Registra saida total (fecha o trade).
    result: 'win', 'loss', ou 'breakeven'
    """
    trades = _load_trades()
    for trade in reversed(trades):
        if trade.get("ticket") == ticket and trade["result"] == "open":
            trade["exit_price"] = exit_price
            trade["exit_time"] = datetime.now(tz=timezone.utc).isoformat()

            # Calcular P&L em pips (diferenca de preco)
            if trade["side"] == "BUY":
                pnl_pips = exit_price - trade["entry_price"]
            else:
                pnl_pips = trade["entry_price"] - exit_price

            trade["pnl_pips"] = round(pnl_pips, 5)

            # Determinar resultado
            if pnl_pips > 0:
                trade["result"] = "win"
            elif pnl_pips < 0:
                trade["result"] = "loss"
            else:
                trade["result"] = "breakeven"

            # Calcular P&L em dinheiro (moeda da conta)
            pnl_money = _calculate_pnl_money(trade["symbol"], pnl_pips, trade["volume"])
            trade["pnl_money"] = pnl_money

            if pnl_money is not None:
                logger.info(f"[Tracker] Saida: {trade['symbol']} {trade['side']} "
                           f"PnL={pnl_money:+.2f} USD ({trade['result']})")
            else:
                logger.info(f"[Tracker] Saida: {trade['symbol']} {trade['side']} "
                           f"PnL={trade['pnl_pips']:.5f} pips ({trade['result']})")
            break
    _save_trades(trades)


def get_all_trades():
    """Retorna todos os trades."""
    return _load_trades()


def get_open_trades():
    """Retorna trades abertos."""
    return [t for t in _load_trades() if t["result"] == "open"]


def get_closed_trades():
    """Retorna trades fechados."""
    return [t for t in _load_trades() if t["result"] != "open"]


def get_performance_summary():
    """Calcula metricas de performance completas."""
    trades = _load_trades()
    closed = [t for t in trades if t["result"] != "open"]
    open_trades = [t for t in trades if t["result"] == "open"]

    if not closed:
        return {
            "total_trades": 0,
            "open_trades": len(open_trades),
            "wins": 0,
            "losses": 0,
            "breakeven": 0,
            "win_rate": 0.0,
            "total_pnl_pips": 0.0,
            "avg_win_pips": 0.0,
            "avg_loss_pips": 0.0,
            "largest_win_pips": 0.0,
            "largest_loss_pips": 0.0,
            "profit_factor": 0.0,
            "consecutive_wins": 0,
            "consecutive_losses": 0,
            "max_drawdown_pips": 0.0,
            "by_symbol": {},
            "by_setup": {},
        }

    wins = [t for t in closed if t["result"] == "win"]
    losses = [t for t in closed if t["result"] == "loss"]
    breakevens = [t for t in closed if t["result"] == "breakeven"]

    win_pips = [t["pnl_pips"] for t in wins if t["pnl_pips"] is not None]
    loss_pips = [abs(t["pnl_pips"]) for t in losses if t["pnl_pips"] is not None]

    total_win_pips = sum(win_pips) if win_pips else 0
    total_loss_pips = sum(loss_pips) if loss_pips else 0

    # Profit factor
    profit_factor = (total_win_pips / total_loss_pips) if total_loss_pips > 0 else float('inf') if total_win_pips > 0 else 0

    # Sequencias consecutivas
    max_consec_wins = 0
    max_consec_losses = 0
    current_wins = 0
    current_losses = 0
    for t in closed:
        if t["result"] == "win":
            current_wins += 1
            current_losses = 0
            max_consec_wins = max(max_consec_wins, current_wins)
        elif t["result"] == "loss":
            current_losses += 1
            current_wins = 0
            max_consec_losses = max(max_consec_losses, current_losses)
        else:
            current_wins = 0
            current_losses = 0

    # Max drawdown
    cumulative = 0
    peak = 0
    max_dd = 0
    for t in closed:
        if t["pnl_pips"] is not None:
            cumulative += t["pnl_pips"]
            peak = max(peak, cumulative)
            dd = peak - cumulative
            max_dd = max(max_dd, dd)

    # P&L em dinheiro (quando disponivel)
    money_values = [t.get("pnl_money") for t in closed if t.get("pnl_money") is not None]
    total_pnl_money = round(sum(money_values), 2) if money_values else None

    # Por simbolo
    by_symbol = {}
    for t in closed:
        sym = t["symbol"]
        if sym not in by_symbol:
            by_symbol[sym] = {"wins": 0, "losses": 0, "pnl_pips": 0, "pnl_money": 0}
        if t["result"] == "win":
            by_symbol[sym]["wins"] += 1
        elif t["result"] == "loss":
            by_symbol[sym]["losses"] += 1
        if t["pnl_pips"] is not None:
            by_symbol[sym]["pnl_pips"] += t["pnl_pips"]
        if t.get("pnl_money") is not None:
            by_symbol[sym]["pnl_money"] += t["pnl_money"]

    # Por setup
    by_setup = {}
    for t in closed:
        setup = t.get("setup", "9.1")
        if setup not in by_setup:
            by_setup[setup] = {"wins": 0, "losses": 0, "pnl_pips": 0, "pnl_money": 0}
        if t["result"] == "win":
            by_setup[setup]["wins"] += 1
        elif t["result"] == "loss":
            by_setup[setup]["losses"] += 1
        if t["pnl_pips"] is not None:
            by_setup[setup]["pnl_pips"] += t["pnl_pips"]
        if t.get("pnl_money") is not None:
            by_setup[setup]["pnl_money"] += t["pnl_money"]

    return {
        "total_trades": len(closed),
        "open_trades": len(open_trades),
        "wins": len(wins),
        "losses": len(losses),
        "breakeven": len(breakevens),
        "win_rate": round((len(wins) / len(closed)) * 100, 1) if closed else 0,
        "total_pnl_pips": round(sum(t["pnl_pips"] for t in closed if t.get("pnl_pips") is not None), 5),
        "total_pnl_money": total_pnl_money,
        "avg_win_pips": round(sum(win_pips) / len(win_pips), 5) if win_pips else 0,
        "avg_loss_pips": round(sum(loss_pips) / len(loss_pips), 5) if loss_pips else 0,
        "largest_win_pips": round(max(win_pips), 5) if win_pips else 0,
        "largest_loss_pips": round(max(loss_pips), 5) if loss_pips else 0,
        "profit_factor": round(profit_factor, 2) if profit_factor != float('inf') else 999.99,
        "consecutive_wins": max_consec_wins,
        "consecutive_losses": max_consec_losses,
        "max_drawdown_pips": round(max_dd, 5),
        "by_symbol": by_symbol,
        "by_setup": by_setup,
    }


def print_report():
    """Imprime relatorio de performance no terminal."""
    summary = get_performance_summary()
    trades = get_closed_trades()

    print(f"\n{'=' * 60}")
    print(f"  RELATORIO DE PERFORMANCE — MT5Bot")
    print(f"{'=' * 60}\n")

    if summary["total_trades"] == 0:
        print("  Nenhuma operacao fechada ainda.\n")
        return

    print(f"  {'Operacoes fechadas:':<30} {summary['total_trades']}")
    print(f"  {'Operacoes abertas:':<30} {summary['open_trades']}")
    print(f"  {'Vitorias:':<30} {summary['wins']} ({summary['win_rate']}%)")
    print(f"  {'Derrotas:':<30} {summary['losses']}")
    print(f"  {'Breakeven:':<30} {summary['breakeven']}")
    print()

    # P&L em dinheiro (principal) e pips (detalhe)
    if summary.get("total_pnl_money") is not None:
        pnl_money = summary["total_pnl_money"]
        print(f"  {'RESULTADO FINANCEIRO:':<30} ${pnl_money:+.2f}")
        print()

    print(f"  {'PnL total (pips):':<30} {summary['total_pnl_pips']:+.5f}")
    print(f"  {'Media vitoria (pips):':<30} {summary['avg_win_pips']:.5f}")
    print(f"  {'Media derrota (pips):':<30} {summary['avg_loss_pips']:.5f}")
    print(f"  {'Maior vitoria (pips):':<30} {summary['largest_win_pips']:.5f}")
    print(f"  {'Maior derrota (pips):':<30} {summary['largest_loss_pips']:.5f}")
    print(f"  {'Profit Factor:':<30} {summary['profit_factor']:.2f}")
    print(f"  {'Max Drawdown (pips):':<30} {summary['max_drawdown_pips']:.5f}")
    print(f"  {'Sequencia vitorias:':<30} {summary['consecutive_wins']}")
    print(f"  {'Sequencia derrotas:':<30} {summary['consecutive_losses']}")

    if summary["by_symbol"]:
        print(f"\n  {'─' * 50}")
        print(f"  POR ATIVO:")
        for sym, data in summary["by_symbol"].items():
            total = data["wins"] + data["losses"]
            wr = round((data["wins"] / total) * 100, 1) if total > 0 else 0
            money_str = f"  ${data['pnl_money']:+.2f}" if data.get("pnl_money") else ""
            print(f"    {sym:<12} {data['wins']}W/{data['losses']}L ({wr}%){money_str}")

    if summary["by_setup"]:
        print(f"\n  {'─' * 50}")
        print(f"  POR SETUP:")
        for setup, data in summary["by_setup"].items():
            total = data["wins"] + data["losses"]
            wr = round((data["wins"] / total) * 100, 1) if total > 0 else 0
            money_str = f"  ${data['pnl_money']:+.2f}" if data.get("pnl_money") else ""
            print(f"    Setup {setup:<6} {data['wins']}W/{data['losses']}L ({wr}%){money_str}")

    if trades:
        print(f"\n  {'─' * 50}")
        print(f"  ULTIMAS 10 OPERACOES:")
        print(f"    {'#':<4} {'Ativo':<8} {'Lado':<5} {'Setup':<6} {'PnL':<12} {'Resultado'}")
        print(f"    {'─'*4} {'─'*8} {'─'*5} {'─'*6} {'─'*12} {'─'*9}")
        for t in trades[-10:]:
            # Mostrar em dinheiro se disponivel, senao em pips
            if t.get("pnl_money") is not None:
                pnl = f"${t['pnl_money']:+.2f}"
            elif t.get("pnl_pips") is not None:
                pnl = f"{t['pnl_pips']:+.5f}p"
            else:
                pnl = "—"
            result_icon = "+" if t['result'] == 'win' else "-" if t['result'] == 'loss' else "="
            print(f"    {t['id']:<4} {t['symbol']:<8} {t['side']:<5} {t.get('setup','9.1'):<6} {pnl:<12} {result_icon} {t['result']}")

    print(f"\n{'=' * 60}\n")