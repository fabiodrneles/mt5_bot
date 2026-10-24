"""Simulador da pesquisa ampla (tools/quant_research/research2.py) — spec 010 AC-1..3."""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "quant_research"))
import research2 as R  # noqa: E402

META = {"X": dict(point=1.0, usd_per_unit=1.0, comm_rt=0.0, swapL=-1.0, swapS=0.0, swap_mode=1, swap3=3,
                  margin=1.0)}


@pytest.fixture(autouse=True)
def _meta(monkeypatch):
    monkeypatch.setattr(R, "META", META)


def frame(o, h, l, c, day0=0):
    n = len(c)
    day = np.arange(day0, day0 + n)
    return dict(t=day * 86400, o=np.array(o, float), h=np.array(h, float), l=np.array(l, float),
                c=np.array(c, float), spr=np.zeros(n), day=day, dow=(day + 3) % 7)


def test_rollovers_wednesday_is_triple_and_weekend_is_free():
    # dia 5 = 1970-01-06 (terca); terca->quinta cruza terca (1) e quarta (3)
    assert R._rollovers(5, 7, swap3=2) == 4
    # sexta -> segunda: so a rolagem de sexta
    assert R._rollovers(8, 11, swap3=2) == 1


def test_stop_before_target_on_same_candle():
    d = frame([100, 100, 100], [100, 120, 100], [100, 80, 100], [100, 100, 100])
    sig = np.array([1, 0, 0])
    tr = R.simulate("X", d, sig, np.full(3, 10.0), np.full(3, 10.0), None, None, 10, False)
    assert tr[0, 2] == pytest.approx(-10.0)


def test_gap_through_stop_exits_at_open():
    d = frame([100, 100, 85], [100, 101, 86], [100, 99, 84], [100, 100, 85], day0=8)  # sab->dom: sem swap
    sig = np.array([1, 0, 0])
    tr = R.simulate("X", d, sig, np.full(3, 10.0), np.full(3, np.nan), None, None, 10, False)
    assert tr[0, 2] == pytest.approx(-15.0)  # saiu na abertura (85), nao no stop (90)


def test_swap_charged_with_triple_rollover():
    # entra terca (dia 5), sai quinta (dia 7) por tempo: 4 rolagens x -1
    d = frame([100] * 4, [100] * 4, [100] * 4, [100] * 4, day0=4)
    sig = np.array([1, 0, 0, 0])
    tr = R.simulate("X", d, sig, np.full(4, 50.0), np.full(4, np.nan), None, None, 3, False)
    assert tr[0, 2] == pytest.approx(-4.0)


def test_strategies_have_no_lookahead():
    """Mudar o futuro nao pode mudar os sinais do passado."""
    rng = np.random.default_rng(1)
    n = 700
    c = 100 + np.cumsum(rng.normal(0, 1, n))
    o = np.r_[c[0], c[:-1]]
    h, l = np.maximum(o, c) + 0.5, np.minimum(o, c) - 0.5
    t = np.arange(n) * 3600 + 1_700_000_000
    day = t // 86400

    def mkd(cc, hh, ll, oo):
        return dict(t=t, o=oo, h=hh, l=ll, c=cc, v=np.full(n, 100.0), spr=np.zeros(n), day=day,
                    dow=(day + 3) % 7, hour=(t % 86400) // 3600,
                    month=t.astype("datetime64[s]").astype("datetime64[M]").astype(np.int64))

    base = R.strategies(mkd(c, h, l, o), "H1")
    c2, h2, l2 = c.copy(), h.copy(), l.copy()
    c2[600:] += 50
    h2[600:] += 50
    l2[600:] += 50
    alt = R.strategies(mkd(c2, h2, l2, o), "H1")
    for a, b in zip(base, alt):
        assert np.array_equal(a[2][:599], b[2][:599]), (a[0], a[1])
