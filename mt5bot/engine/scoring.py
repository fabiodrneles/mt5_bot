"""Motor de decisao multi-criterio (spec 5.5 + aprofundamento Palex).

Ordena os candidatos por score e aplica o gate de Risco-Retorno (RRR).
Formula do livro:

    score = rrr * 30.0
          + 25.0  se congruencia macro
          + (1.0 - proximidade_media) * 20.0
          + 25.0  se volume confirma
          + 0.0   se RRR < 1.0 (trava, inviavel)

Notas de semantica:
- `proximidade_media` e a distancia relativa do preco a media de referencia,
  normalizada [0,1]: 0 = colado na media (melhor), 1 = muito afastado.
  Segue a formula e o comentario do livro ("perto da media = melhor scorê"),
  nao o comentario inline ambiguo do raw/aprofundamento.md.
- `aplicar_scoring` projeta um alvo default de 1x risco quando o setup nao define
  alvo proprio (spec 5.6: "alvo = entrada ± N x risco").
"""

import numpy as np
import pandas as pd

from mt5bot.core import config
from mt5bot.engine.indicators import calculate_rvol


def _peso(nome: str, default: float) -> float:
    pesos = getattr(config, "SCORE_WEIGHTS", None) or {}
    return float(pesos.get(nome, default))


def validar_risco_retorno(entrada: float, stop: float, alvo: float,
                          direcao: str, multiplicador_minimo: float = None) -> bool:
    """RRR = |alvo - entrada| / |entrada - stop| deve ser >= minimo.

    Retorna False para risco geometricamente invalido (<= 0).
    """
    risco = abs(entrada - stop)
    if risco <= 0:
        return False
    minimo = multiplicador_minimo if multiplicador_minimo is not None \
        else getattr(config, "MIN_RISK_REWARD", 1.0)
    rrr = abs(alvo - entrada) / risco
    return rrr >= minimo


def calcular_score(dados_sinal: dict, contexto: dict) -> float:
    """Calcula o score de um sinal conforme pesos do livro.

    - dados_sinal: dict com "trigger_price" (entrada), "stop_loss" e "target".
    - contexto: dict com "congruencia_macro" (bool), "proximidade_media"
      (0..1, 0=colado), "volume_confirma" (bool), "esforco_falho" (bool, veto).
    """
    entrada = dados_sinal.get("trigger_price")
    stop = dados_sinal.get("stop_loss")
    alvo = dados_sinal.get("target")
    if entrada is None or stop is None or alvo is None:
        return 0.0

    risco = abs(entrada - stop)
    if risco <= 0:
        return 0.0
    rrr = abs(alvo - entrada) / risco
    
    # Exceção para o Setup Russo (Reversão à média com alvos dinâmicos BB)
    if dados_sinal.get("setup") == "russian_bb":
        return 100.0  # Prioridade máxima, ignora filtros macro de tendência

    elif dados_sinal.get("setup") == "judas":
        return 90.0  # Setup probabilistico de horario tem maxima prioridade

    if rrr < getattr(config, "MIN_RISK_REWARD", 1.0):
        return 0.0  # trava de corte: nao paga o risco minimo

    if contexto.get("esforco_falho"):
        return 0.0  # barra de esforco sem resultado -> veta o setup

    # --- Filtros macro Fase 2.5 (veto) ---
    if not contexto.get("mm50_favoravel", True):
        return 0.0  # tendencia intermediaria (MM50) contra a operacao
    if not contexto.get("vwap_favoravel", True):
        return 0.0  # preco esticado demais da VWAP (reversao a media)
    if not contexto.get("mtf_favoravel", True):
        return 0.0  # tendencia no timeframe superior (MTF) contra a operacao

    score = rrr * _peso("rrr", 30.0)
    if contexto.get("congruencia_macro"):
        score += _peso("congruencia_macro", 25.0)

    proximidade = min(max(float(contexto.get("proximidade_media", 1.0)), 0.0), 1.0)
    score += (1.0 - proximidade) * _peso("proximidade_media", 20.0)

    if contexto.get("volume_confirma"):
        score += _peso("volume", 25.0)
    if contexto.get("ifr9_favoravel"):
        score += _peso("ifr9", 10.0)  # IFR9 saindo da zona de exaustao confirma
    if contexto.get("vwap_toque"):
        score += _peso("vwap", 10.0)  # toque na VWAP da score maximo

    return float(score)


def projetar_alvo(entrada: float, stop: float, direcao: str,
                  multiplicador: float = 1.0) -> float:
    """Alvo default geometrico: entrada +- (risco x multiplicador)."""
    risco = abs(entrada - stop)
    delta = risco * multiplicador
    return entrada + delta if direcao.upper() == "BUY" else entrada - delta


def build_context(df: pd.DataFrame, setup: dict, rvol_ratio: float = None,
                  mtf_favoravel: bool = None) -> dict:
    """Monta o contexto multi-criterio a partir do DataFrame local (sem MT5).

    Permissivo na ausencia de dados: congruencia/volume = False,
    proximidade = 1.0 (sem bonus), nunca derruba o setup por falta de coluna.

    `mtf_favoravel`: resultado pre-computado do filtro MTF (spec 5.4). Como
    exigiria chamada ao MT5 (dados do timeframe superior), o scoring nao busca
    esse dado — quem chama (`execution_manager`) o calcula uma vez por side e
    o injeta. `None` (= dados nao disponiveis) e permissivo (True).
    """
    direcao = str(setup.get("action", "BUY")).upper()

    # --- Congruencia macro local (alinhamento de medias) ---
    congruencia = False
    try:
        if all(c in df.columns for c in ("ema9", "sma21", "ema50")):
            close = float(df["close"].iloc[-1])
            ema9 = float(df["ema9"].iloc[-1])
            sma21 = float(df["sma21"].iloc[-1])
            ema50 = float(df["ema50"].iloc[-1])
            if not any(np.isnan(x) for x in (ema9, sma21, ema50)):
                if direcao == "BUY":
                    congruencia = bool(close > ema9 > sma21 > ema50)
                else:
                    congruencia = bool(close < ema9 < sma21 < ema50)
    except Exception:
        congruencia = False

    # --- Proximidade da media de referencia (SMA21), normalizada por ATR ---
    proximidade = 1.0
    try:
        if "sma21" in df.columns and "atr" in df.columns:
            close = float(df["close"].iloc[-1])
            sma21 = float(df["sma21"].iloc[-1])
            atr = float(df["atr"].iloc[-1])
            if not np.isnan(sma21) and not np.isnan(atr) and atr > 0:
                proximidade = min(abs(close - sma21) / atr, 1.0)
    except Exception:
        proximidade = 1.0

    # --- Confirmacao de volume (RVOL) ---
    volume_confirma = False
    try:
        if rvol_ratio is None:
            rvol_ratio, _, _ = calculate_rvol(df)
        volume_confirma = bool(rvol_ratio >= getattr(config, "RVOL_THRESHOLD", 1.15))
    except Exception:
        volume_confirma = False

    # --- Filtros macro Fase 2.5 (delegam aos check_* de brain.indicators) ---
    from mt5bot.engine.indicators import check_ifr9_filter, check_mm50_filter, check_vwap_filter

    mm50_favoravel = check_mm50_filter(df, direcao)
    vwap_favoravel = check_vwap_filter(df, direcao)
    ifr9_favoravel = check_ifr9_filter(df, direcao)

    # Toque na VWAP (score maximo): preco colado na VWAP (dentro de 0.5 ATR)
    vwap_toque = False
    try:
        if df is not None and len(df) and 'vwap' in df.columns and 'atr' in df.columns:
            close = float(df["close"].iloc[-1])
            vwap = float(df["vwap"].iloc[-1])
            atr = float(df["atr"].iloc[-1])
            if not np.isnan(vwap) and not np.isnan(atr) and atr > 0:
                vwap_toque = bool(abs(close - vwap) / atr <= 0.5)
    except Exception:
        vwap_toque = False

    return {
        "congruencia_macro": congruencia,
        "proximidade_media": float(proximidade),
        "volume_confirma": volume_confirma,
        "esforco_falho": False,
        "mm50_favoravel": mm50_favoravel,
        "vwap_favoravel": vwap_favoravel,
        "vwap_toque": vwap_toque,
        "ifr9_favoravel": ifr9_favoravel,
        "mtf_favoravel": True if mtf_favoravel is None else bool(mtf_favoravel),
    }


def aplicar_scoring(setups: list, df: pd.DataFrame,
                    mtf_favoravel: dict = None) -> list:
    """Aplica gate RRR + scoring aos candidatos, retorna ordenados (maior score 1o).

    Setups sem "target" proprio recebem alvo default de 1x risco via
    `projetar_alvo` (spec 5.6). Setups vetados (score 0) sao descartados.

    `mtf_favoravel`: dict opcional {"BUY": bool, "SELL": bool} com o resultado
    do filtro MTF (spec 5.4) pre-computado por quem detém acesso ao MT5.
    `None` significa dados nao disponiveis -> permissivo (nenhum setup vetado).
    """
    if not setups:
        return []
    if df is None or len(df) == 0:
        df = pd.DataFrame()

    try:
        rvol_ratio, _, _ = calculate_rvol(df)
    except Exception:
        rvol_ratio = None

    ranked = []
    for setup in setups:
        entrada = float(setup.get("trigger_price", 0.0))
        stop = float(setup.get("stop_loss", 0.0))
        direcao = str(setup.get("action", "BUY")).upper()
        alvo = setup.get("target")
        if alvo is None:
            alvo = projetar_alvo(entrada, stop, direcao)

        mtf_ok = None
        if isinstance(mtf_favoravel, dict):
            mtf_ok = mtf_favoravel.get(direcao)
        contexto = build_context(df, setup, rvol_ratio=rvol_ratio,
                                 mtf_favoravel=mtf_ok)
        dados_validacao = dict(setup)
        dados_validacao["target"] = alvo

        if not validar_risco_retorno(entrada, stop, alvo, direcao):
            continue

        score = calcular_score(dados_validacao, contexto)
        if score > 0:
            item = dict(setup)
            item["target"] = alvo
            item["score"] = score
            ranked.append(item)

    ranked.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    return ranked