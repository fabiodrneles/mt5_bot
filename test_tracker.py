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
