"""Diario de sinais (mt5bot/data/signal_journal.py): anotar antes, medir depois."""
import pytest

from mt5bot.data import signal_journal as J


def entry(**kw):
    base = dict(id=1, anotado_em_utc=1000, ativo="US500", tf="M15", lado="venda", avaliacao="bom", motivo="teste",
                preco_entrada=100.0, stop=105.0, alvo=90.0, alvo_r=2.0, candle_sinal_utc=900)
    base.update(kw)
    return J.Entry(**base)


def test_default_levels_follow_owner_rule():
    # venda: stop na maxima do candle; alvo = 2x o risco abaixo da entrada
    assert J.default_levels(-1, 100.0, 105.0, 98.0, 2.0) == (105.0, 90.0)
    # compra: stop na minima
    assert J.default_levels(1, 100.0, 103.0, 96.0, 1.0) == (96.0, 104.0)


def test_signal_already_past_the_stop_is_rejected():
    with pytest.raises(ValueError):
        J.default_levels(-1, 106.0, 105.0, 98.0, 2.0)


def test_sell_stop_and_target_use_the_ask():
    # o bid nunca chega a 105, mas o ask (bid + spread 1) chega: venda estopada
    assert J.evaluate_path(-1, 100.0, 105.0, 90.0, [104.5], [101.0], [1.0])[0] == J.LOSS
    # o bid chega a 89,5: o ask (90,5) ainda nao pegou o alvo de 90
    assert J.evaluate_path(-1, 100.0, 105.0, 90.0, [100.0], [89.5], [1.0])[0] == J.OPEN
    assert J.evaluate_path(-1, 100.0, 105.0, 90.0, [100.0], [88.9], [1.0])[:2] == (J.WIN, 90.0)


def test_stop_comes_first_inside_the_same_candle():
    assert J.evaluate_path(1, 100.0, 95.0, 110.0, [111.0], [94.0], [0.0])[0] == J.LOSS


def test_save_and_load_roundtrip(tmp_path):
    path = str(tmp_path / "diario.csv")
    J.save([entry(), entry(id=2, lado="compra", status=J.WIN, resultado_usd=0.5)], path)
    back = J.load(path)
    assert [e.id for e in back] == [1, 2]
    assert back[1].status == J.WIN and back[1].resultado_usd == 0.5 and back[0].anotado_em_utc == 1000


def test_summary_compares_with_breakeven_and_luck():
    entries = [entry(id=i, status=J.WIN if i < 6 else J.LOSS, resultado_usd=0.2 if i < 6 else -0.1)
               for i in range(10)]
    s = J.summary(entries)["bom"]
    assert s["n"] == 10 and s["wins"] == 6
    assert s["breakeven"] == pytest.approx(1 / 3)
    # 6 acertos em 10 com chance de 1/3 cada: ~7,7% de chance de ser sorte
    assert s["p_sorte"] == pytest.approx(0.0766, abs=1e-3)
