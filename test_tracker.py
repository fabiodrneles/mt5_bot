import os
import json
import types
from datetime import datetime, timezone
import tracker


def test_record_entry_and_exit(tmp_path, monkeypatch):
    # Forcar arquivo de trades para tmp_path
    trades_file = tmp_path / "trades.json"
    monkeypatch.setattr(tracker, '_TRADES_FILE', str(trades_file))

    # Garantir diretorio
    os.makedirs(os.path.dirname(str(trades_file)), exist_ok=True)

    # Registrar entrada
    tid = tracker.record_entry('TEST', 'BUY', '9.1', 1.1000, 1.0900, 0.01, 555)
    assert isinstance(tid, int) and tid == 1

    # Verificar arquivo salvo
    with open(str(trades_file), 'r', encoding='utf-8') as f:
        data = json.load(f)
    assert len(data) == 1
    t = data[0]
    assert t['symbol'] == 'TEST'
    assert t['side'] == 'BUY'
    assert t['entry_price'] == 1.1
    assert t['ticket'] == 555

    # Registrar saida com lucro
    tracker.record_exit(555, 1.1200, result='win')

    with open(str(trades_file), 'r', encoding='utf-8') as f:
        data = json.load(f)
    t = data[0]
    assert t['exit_price'] == 1.12
    assert t['result'] == 'win'
    assert 'pnl_pips' in t and t['pnl_pips'] is not None


def test_save_trades_converts_numpy(tmp_path, monkeypatch):
    try:
        import numpy as np
    except Exception:
        np = None

    trades_file = tmp_path / "trades.json"
    monkeypatch.setattr(tracker, '_TRADES_FILE', str(trades_file))
    os.makedirs(os.path.dirname(str(trades_file)), exist_ok=True)

    # Construir trades com numpy types se possivel
    if np is not None:
        sample = {
            'id': np.int64(1),
            'symbol': 'TEST',
            'entry_price': np.float64(1.2345),
            'partial_volume': np.array([1, 2, 3])
        }
    else:
        sample = {'id': 1, 'symbol': 'TEST', 'entry_price': 1.2345, 'partial_volume': [1, 2, 3]}

    tracker._save_trades([sample])

    with open(str(trades_file), 'r', encoding='utf-8') as f:
        data = json.load(f)

    assert isinstance(data, list)
    saved = data[0]
    # IDs must be native int after serialization
    assert isinstance(saved['id'], int)
    assert isinstance(saved['entry_price'], float)
    assert isinstance(saved['partial_volume'], list)


def _make_trade_file(tmp_path, monkeypatch, trades):
    trades_file = tmp_path / "trades.json"
    os.makedirs(os.path.dirname(str(trades_file)), exist_ok=True)
    monkeypatch.setattr(tracker, '_TRADES_FILE', str(trades_file))
    with open(str(trades_file), "w", encoding="utf-8") as f:
        json.dump(trades, f)
    return trades_file


def test_load_trades_missing_file_returns_empty(tmp_path, monkeypatch):
    trades_file = tmp_path / "missing.json"
    monkeypatch.setattr(tracker, '_TRADES_FILE', str(trades_file))
    assert tracker._load_trades() == []


def test_load_trades_corrupt_json_returns_empty(tmp_path, monkeypatch):
    trades_file = tmp_path / "trades.json"
    os.makedirs(os.path.dirname(str(trades_file)), exist_ok=True)
    with open(str(trades_file), "w", encoding="utf-8") as f:
        f.write("{invalid json!!!")
    monkeypatch.setattr(tracker, '_TRADES_FILE', str(trades_file))
    assert tracker._load_trades() == []


def test_record_partial_exit_atualiza_trade_aberto(tmp_path, monkeypatch):
    _make_trade_file(tmp_path, monkeypatch, [{
        "ticket": 10, "result": "open", "symbol": "WIN",
        "entry_price": 100.0, "sl_price": 99.0, "volume": 0.02,
        "side": "BUY", "pnl_pips": None, "pnl_money": None,
        "exit_price": None, "exit_time": None,
        "partial_exit_price": None, "partial_volume": None,
    }])
    tracker.record_partial_exit(10, 101.0, 0.01)
    data = tracker.get_all_trades()
    assert data[0]["partial_exit_price"] == 101.0
    assert data[0]["partial_volume"] == 0.01


def test_record_exit_loss_e_breakeven_e_sell(tmp_path, monkeypatch):
    _make_trade_file(tmp_path, monkeypatch, [
        {"ticket": 11, "result": "open", "symbol": "WIN", "side": "BUY",
         "entry_price": 100.0, "volume": 0.01, "pnl_pips": None,
         "pnl_money": None, "exit_price": None, "exit_time": None},
        {"ticket": 12, "result": "open", "symbol": "WIN", "side": "SELL",
         "entry_price": 100.0, "volume": 0.01, "pnl_pips": None,
         "pnl_money": None, "exit_price": None, "exit_time": None},
        {"ticket": 13, "result": "open", "symbol": "WIN", "side": "BUY",
         "entry_price": 100.0, "volume": 0.01, "pnl_pips": None,
         "pnl_money": None, "exit_price": None, "exit_time": None},
    ])
    tracker.record_exit(11, 99.0)          # loss (BUY)
    tracker.record_exit(12, 99.0)          # win (SELL)
    tracker.record_exit(13, 100.0)         # breakeven

    closed = tracker.get_closed_trades()
    by_ticket = {t["ticket"]: t for t in closed}
    assert by_ticket[11]["result"] == "loss"
    assert by_ticket[11]["pnl_pips"] == -1.0
    assert by_ticket[12]["result"] == "win"
    assert by_ticket[12]["pnl_pips"] == 1.0
    assert by_ticket[13]["result"] == "breakeven"
    assert by_ticket[13]["pnl_pips"] == 0.0


def test_record_exit_forca_converte_resultado(tmp_path, monkeypatch):
    _make_trade_file(tmp_path, monkeypatch, [
        {"ticket": 20, "result": "open", "symbol": "WIN", "side": "BUY",
         "entry_price": 100.0, "volume": 0.01, "pnl_pips": None,
         "pnl_money": None, "exit_price": None, "exit_time": None},
    ])
    tracker.record_exit(20, 105.0, result="breakeven")
    assert tracker.get_closed_trades()[0]["result"] == "win"  # pnl > 0 manda


def test_calculate_pnl_money_fallback_sem_mt5(tmp_path, monkeypatch):
    # O mock do MT5 nao expoe trade_tick_value -> fallback retorna None
    assert tracker._calculate_pnl_money("WIN", 10.0, 0.01) is None


def test_calculate_pnl_money_com_mt5_mock(tmp_path, monkeypatch):
    class SymbolInfo:
        trade_tick_value = 0.10
        trade_tick_size = 0.001
        point = 0.001

    import MetaTrader5 as mt5_mock
    monkeypatch.setattr(mt5_mock, "symbol_info", lambda s: SymbolInfo())
    pnl = tracker._calculate_pnl_money("WIN", 0.005, 1.0)
    assert pnl == round((0.005 / 0.001) * 0.10 * 1.0, 2)


def test_get_open_trades_filtra(tmp_path, monkeypatch):
    _make_trade_file(tmp_path, monkeypatch, [
        {"ticket": 1, "result": "open", "symbol": "WIN"},
        {"ticket": 2, "result": "win", "symbol": "WIN"},
    ])
    open_trades = tracker.get_open_trades()
    assert len(open_trades) == 1
    assert open_trades[0]["ticket"] == 1


def test_get_daily_pnl_filtra_por_data_e_aceita_pips(tmp_path, monkeypatch):
    now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    other_day = "2020-01-01T00:00:00"
    _make_trade_file(tmp_path, monkeypatch, [
        {"ticket": 1, "pnl_money": 25.0, "exit_time": now},
        {"ticket": 2, "pnl_money": -5.0, "exit_time": now},
        {"ticket": 3, "pnl_money": 99.0, "exit_time": other_day},
        # sem pnl_money -> usa pips como fallback
        {"ticket": 4, "pnl_money": None, "pnl_pips": 2.5, "exit_time": now},
    ])
    assert tracker.get_daily_pnl() == 22.5   # 25 - 5 + 2.5
    assert tracker.get_daily_pnl("2020-01-01") == 99.0


def test_performance_summary_estatisticas_completas(tmp_path, monkeypatch):
    _make_trade_file(tmp_path, monkeypatch, [
        {"ticket": 1, "result": "win", "symbol": "WIN", "setup": "9.1",
         "pnl_pips": 10.0, "pnl_money": 10.0},
        {"ticket": 2, "result": "win", "symbol": "WIN", "setup": "9.1",
         "pnl_pips": 20.0, "pnl_money": 20.0},
        {"ticket": 3, "result": "loss", "symbol": "WIN", "setup": "9.1",
         "pnl_pips": -5.0, "pnl_money": -5.0},
        {"ticket": 4, "result": "loss", "symbol": "HK50", "setup": "PC",
         "pnl_pips": -5.0, "pnl_money": -5.0},
        {"ticket": 5, "result": "win", "symbol": "WIN", "setup": "9.1",
         "pnl_pips": 5.0, "pnl_money": 5.0},
        {"ticket": 6, "result": "loss", "symbol": "WIN", "setup": "9.1",
         "pnl_pips": -10.0, "pnl_money": -10.0},
        {"ticket": 7, "result": "open", "symbol": "WIN", "setup": "9.1",
         "pnl_pips": None, "pnl_money": None},
    ])
    s = tracker.get_performance_summary()
    assert s["total_trades"] == 6
    assert s["open_trades"] == 1
    assert s["wins"] == 3
    assert s["losses"] == 3
    assert s["win_rate"] == 50.0
    assert s["total_pnl_pips"] == 15.0          # 10+20-5-5+5-10
    assert s["total_pnl_money"] == 15.0
    assert s["largest_win_pips"] == 20.0
    assert s["largest_loss_pips"] == 10.0       # abs max
    assert s["profit_factor"] == round(35.0 / 20.0, 2)
    assert s["avg_win_pips"] == round(35.0 / 3, 5)
    assert s["avg_loss_pips"] == round(20.0 / 3, 5)
    assert s["consecutive_wins"] == 2
    assert s["consecutive_losses"] == 2
    assert s["max_drawdown_pips"] == 15.0
    assert set(s["by_symbol"].keys()) == {"WIN", "HK50"}
    assert s["by_symbol"]["WIN"]["wins"] == 3
    assert set(s["by_setup"].keys()) == {"9.1", "PC"}


def test_performance_summary_vazio(tmp_path, monkeypatch):
    _make_trade_file(tmp_path, monkeypatch, [])
    s = tracker.get_performance_summary()
    assert s["total_trades"] == 0
    assert s["wins"] == 0
    assert s["profit_factor"] == 0.0
    assert s["by_symbol"] == {}
    assert s["by_setup"] == {}


def test_performance_summary_profit_factor_infinito(tmp_path, monkeypatch):
    _make_trade_file(tmp_path, monkeypatch, [
        {"ticket": 1, "result": "win", "symbol": "WIN", "setup": "9.1",
         "pnl_pips": 10.0, "pnl_money": 10.0},
    ])
    s = tracker.get_performance_summary()
    assert s["profit_factor"] == 999.99


def test_print_report_sem_trades(tmp_path, monkeypatch, capsys):
    _make_trade_file(tmp_path, monkeypatch, [])
    tracker.print_report()
    out = capsys.readouterr().out
    assert "Nenhuma operacao fechada ainda" in out


def test_print_report_com_trades_e_money(tmp_path, monkeypatch, capsys):
    _make_trade_file(tmp_path, monkeypatch, [
        {"id": 1, "symbol": "WIN", "side": "BUY", "setup": "9.1",
         "result": "win", "pnl_pips": 10.0, "pnl_money": 10.0},
        {"id": 2, "symbol": "WIN", "side": "SELL", "setup": "PC",
         "result": "loss", "pnl_pips": -4.0, "pnl_money": -4.0},
    ])
    tracker.print_report()
    out = capsys.readouterr().out
    assert "RESULTADO FINANCEIRO" in out
    assert "+$10.00" in out or "$+10.00" in out
    assert "POR ATIVO" in out
    assert "POR SETUP" in out
    assert "ULTIMAS 10 OPERACOES" in out


def test_print_report_sem_pnl_money_usa_pips(tmp_path, monkeypatch, capsys):
    _make_trade_file(tmp_path, monkeypatch, [
        {"id": 1, "symbol": "WIN", "side": "BUY", "setup": "9.1",
         "result": "win", "pnl_pips": 10.0, "pnl_money": None},
    ])
    tracker.print_report()
    out = capsys.readouterr().out
    assert "+10.00000" in out


def test_save_trades_converte_datetime(tmp_path, monkeypatch):
    trades_file = tmp_path / "trades.json"
    os.makedirs(os.path.dirname(str(trades_file)), exist_ok=True)
    monkeypatch.setattr(tracker, '_TRADES_FILE', str(trades_file))
    tracker._save_trades([{"when": datetime(2024, 5, 1, 10, 30, tzinfo=timezone.utc)}])
    with open(str(trades_file), "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data[0]["when"] == "2024-05-01T10:30:00+00:00"
