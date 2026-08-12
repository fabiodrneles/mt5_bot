import numpy as np
import pandas as pd
import pytest

from mt5bot.core import config
from mt5bot.engine.scoring import (
    aplicar_scoring,
    build_context,
    calcular_score,
    projetar_alvo,
    validar_risco_retorno,
)


# ---------------------------------------------------------------------------
# validar_risco_retorno
# ---------------------------------------------------------------------------

def test_rrr_aprovado_com_2x_risco():
    # BUY: entrada 100, stop 99 (risco 1), alvo 102 (retorno 2) -> RRR 2.0
    assert validar_risco_retorno(100.0, 99.0, 102.0, "BUY") is True


def test_rrr_reprovado_abaixo_de_1x():
    assert validar_risco_retorno(100.0, 99.0, 100.5, "BUY") is False  # RRR 0.5


def test_rrr_stop_invalido_risco_zero():
    assert validar_risco_retorno(100.0, 100.0, 110.0, "BUY") is False


def test_rrr_respeita_multiplicador_personalizado():
    # RRR 1.5 >= 1.0 -> True; com minimo 2.0 -> False
    assert validar_risco_retorno(100.0, 99.0, 101.5, "BUY", multiplicador_minimo=1.0) is True
    assert validar_risco_retorno(100.0, 99.0, 101.5, "BUY", multiplicador_minimo=2.0) is False


# ---------------------------------------------------------------------------
# calcular_score (formula do livro / aprofundamento)
# ---------------------------------------------------------------------------

def _setup(rrr, congruencia=False, proximidade=1.0, volume=False, esforco_falho=False):
    """Monta setup com entrada 100, risco 1 e alvo que gera o RRR desejado."""
    entrada, stop = 100.0, 99.0
    alvo = entrada + rrr  # retorno = rrr x risco (risco = 1)
    return {
        "trigger_price": entrada,
        "stop_loss": stop,
        "target": alvo,
        "action": "BUY",
    }, {
        "congruencia_macro": congruencia,
        "proximidade_media": float(proximidade),
        "volume_confirma": volume,
        "esforco_falho": esforco_falho,
    }


def test_score_rrr_abaixo_1_zerado():
    setup, ctx = _setup(rrr=0.8)
    assert calcular_score(setup, ctx) == 0.0


def test_score_base_rrr_1x():
    setup, ctx = _setup(rrr=1.0, congruencia=False, proximidade=1.0, volume=False)
    # rrr 1.0 * 30 + 0 + (1-1)*20 + 0 = 30
    assert calcular_score(setup, ctx) == pytest.approx(30.0)


def test_score_soma_pesos_congruencia_volume():
    setup, ctx = _setup(rrr=2.0, congruencia=True, proximidade=0.0, volume=True)
    # 2.0*30 + 25 + (1-0)*20 + 25 = 60+25+20+25 = 130
    assert calcular_score(setup, ctx) == pytest.approx(130.0)


def test_score_esforco_falho_veta():
    setup, ctx = _setup(rrr=2.0, esforco_falho=True)
    assert calcular_score(setup, ctx) == 0.0


def test_score_mtf_contra_veta():
    # MTF desfavoravel (tendencia superior contra) zera o score (spec 5.4/5.5)
    setup, ctx = _setup(rrr=2.0, congruencia=True, volume=True)
    assert calcular_score(setup, ctx) > 0.0
    ctx["mtf_favoravel"] = False
    assert calcular_score(setup, ctx) == 0.0


def test_score_mtf_ausente_permissivo():
    # Contexto sem "mtf_favoravel" nao deve vetar (permissivo por default)
    setup, ctx = _setup(rrr=1.0)
    assert "mtf_favoravel" not in ctx
    assert calcular_score(setup, ctx) == pytest.approx(30.0)


def test_score_rrr_maior_bonifica():
    low, _ = _setup(rrr=1.0)
    high, ctx = _setup(rrr=3.0)
    assert calcular_score(high, ctx) > calcular_score(low, ctx)


# ---------------------------------------------------------------------------
# projetar_alvo (spec 5.6)
# ---------------------------------------------------------------------------

def test_projetar_alvo_buy():
    assert projetar_alvo(100.0, 99.0, "BUY") == 101.0  # entrada + 1x risco


def test_projetar_alvo_sell():
    assert projetar_alvo(99.0, 100.0, "SELL") == 98.0  # entrada - 1x risco


def test_projetar_alvo_multiplicador_2x():
    assert projetar_alvo(100.0, 99.0, "BUY", multiplicador=2.0) == 102.0


# ---------------------------------------------------------------------------
# aplicar_scoring (fluxo completo: RRR gate + ordenacao)
# ---------------------------------------------------------------------------

def _df_com_dados():
    """DataFrame curto com indicadores suficientes para build_context nao quebrar."""
    np.random.seed(0)
    closes = np.linspace(100.0, 110.0, 30) + np.random.normal(0, 0.2, 30)
    df = pd.DataFrame({
        "open": closes,
        "high": closes + 0.5,
        "low": closes - 0.5,
        "close": closes,
        "ema9": closes,
        "sma21": closes - 2.0,
        "ema50": closes - 4.0,
        "atr": np.full(30, 1.0),
    })
    df["ema9"] = df["close"]
    df["tick_volume"] = np.ones(30) * 100
    return df


def test_aplicar_scoring_descarta_rrr_ruim_e_ordena():
    df = _df_com_dados()
    setups = [
        # BUY com alvo proprio muito proximo -> RRR 0.5, deve ser descartado
        {"setup": "X", "action": "BUY", "trigger_price": 100.0, "stop_loss": 99.0,
         "target": 100.5, "score": 50},
        # BUY sem alvo -> alvo default 1x risco, RRR 1.0, entra na lista
        {"setup": "Y", "action": "BUY", "trigger_price": 100.0, "stop_loss": 99.0,
         "score": 10},
    ]
    ranked = aplicar_scoring(setups, df)
    assert len(ranked) == 1
    assert ranked[0]["setup"] == "Y"
    assert ranked[0]["target"] == 101.0  # alvo default projetado


def test_aplicar_scoring_ordena_maior_score_primeiro():
    df = _df_com_dados()
    # o setup A tem RRR 2.0 (score base 60), B tem RRR 1.0 (score base 30)
    setups = [
        {"setup": "B", "action": "BUY", "trigger_price": 100.0, "stop_loss": 99.0,
         "target": 101.0, "score": 99},
        {"setup": "A", "action": "BUY", "trigger_price": 100.0, "stop_loss": 99.0,
         "target": 102.0, "score": 99},
    ]
    ranked = aplicar_scoring(setups, df)
    assert [s["setup"] for s in ranked] == ["A", "B"]
    assert ranked[0]["score"] > ranked[1]["score"]


def test_aplicar_scoring_lista_vazia():
    assert aplicar_scoring([], _df_com_dados()) == []


def test_aplicar_scoring_mtf_veta_um_lado_e_mantem_outro():
    df = _df_com_dados()
    # Ambos com RRR valido (alvo 1x risco -> RRR 1.0); MTF desfavoravel para BUY
    setups = [
        {"setup": "A", "action": "BUY", "trigger_price": 100.0, "stop_loss": 99.0,
         "target": 101.0, "score": 99},
        {"setup": "B", "action": "SELL", "trigger_price": 101.0, "stop_loss": 102.0,
         "target": 100.0, "score": 99},
    ]
    ranked = aplicar_scoring(setups, df, mtf_favoravel={"BUY": False, "SELL": True})
    assert len(ranked) == 1
    assert ranked[0]["setup"] == "B"


def test_aplicar_scoring_mtf_none_permissivo():
    df = _df_com_dados()
    setups = [
        {"setup": "A", "action": "BUY", "trigger_price": 100.0, "stop_loss": 99.0,
         "target": 101.0, "score": 99},
    ]
    # Sem dict MTF: nenhum setup vetado (default permissivo)
    assert len(aplicar_scoring(setups, df)) == 1
    assert len(aplicar_scoring(setups, df, mtf_favoravel=None)) == 1


# ---------------------------------------------------------------------------
# build_context
# ---------------------------------------------------------------------------

def test_context_permissivo_sem_dados():
    ctx = build_context(pd.DataFrame(), {"action": "BUY"})
    assert ctx["congruencia_macro"] is False
    assert ctx["volume_confirma"] is False
    assert ctx["proximidade_media"] == 1.0
    assert ctx["esforco_falho"] is False


def test_context_mtf_default_permissivo():
    # Sem informacao MTF (None) -> permissivo True; com valor explicito respeita
    ctx = build_context(pd.DataFrame(), {"action": "BUY"})
    assert ctx["mtf_favoravel"] is True
    ctx = build_context(pd.DataFrame(), {"action": "BUY"}, mtf_favoravel=False)
    assert ctx["mtf_favoravel"] is False
    ctx = build_context(pd.DataFrame(), {"action": "BUY"}, mtf_favoravel=True)
    assert ctx["mtf_favoravel"] is True