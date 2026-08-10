import os
import json
import time
from types import SimpleNamespace
import persistence


def make_symbol_state():
    return SimpleNamespace(
        state=SimpleNamespace(name="IN_POSITION"),
        pending_order_ticket=123,
        position_ticket=456,
        position_type=SimpleNamespace(name="BUY"),
        candle_referencia=(1, 2, 3, 4, 5, 6, 7, 8),
        entry_price=1.2345,
        sl_price=1.2300,
        partial_exit_done=False,
        watching_92_candles=0,
        setup_type="9.1",
        exit_profit=None
    )


def test_save_and_load_states(tmp_path, monkeypatch):
    # Forçar APPDATA para tmp_path
    monkeypatch.setenv('APPDATA', str(tmp_path))

    # Construir estado de simbolos
    ss = {'TEST': make_symbol_state()}

    # Salvar
    persistence.save_states(ss)

    # Verificar arquivo existe
    path = persistence._get_path()
    assert os.path.exists(path)

    # Carregar e verificar conteudo basico
    loaded = persistence.load_states()
    assert isinstance(loaded, dict)
    assert 'TEST' in loaded
    saved = loaded['TEST']
    assert saved['state'] == 'IN_POSITION'
    assert saved['entry_price'] == 1.2345


def test_load_corrupted_creates_backup(tmp_path, monkeypatch):
    monkeypatch.setenv('APPDATA', str(tmp_path))

    # Garantir diretorio
    data_dir = persistence._get_data_dir()
    os.makedirs(data_dir, exist_ok=True)
    path = persistence._get_path()

    # Escrever conteudo invalido
    with open(path, 'w', encoding='utf-8') as f:
        f.write('{ this is not: valid json,,, }')

    # Carregar -> deve retornar None e criar backup com sufixo .corrupt.<timestamp>
    loaded = persistence.load_states()
    assert loaded is None

    # Procurar backup
    files = os.listdir(data_dir)
    corrupts = [f for f in files if f.startswith('state.json.corrupt')]
    assert len(corrupts) >= 1
