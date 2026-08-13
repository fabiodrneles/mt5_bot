import pandas as pd
import numpy as np
from mt5bot.core import config
from mt5bot.engine.indicators import swing_levels, fib_extension_targets


class StrategyScorer:
    """
    Cérebro Matemático: Analisa o DataFrame de preços (com os indicadores já preenchidos)
    e retorna o setup de maior probabilidade para o momento, além de motivos verbosos
    caso nenhum setup seja ativado.
    """

    @staticmethod
    def evaluate_all(df: pd.DataFrame, tick_size: float = 0.01, tick_offset: float = 1) -> tuple[list, str]:
        """
        Avalia o último candle completado (df.iloc[-1]) e verifica se há um gatilho armado.
        Retorna:
        - Lista de setups identificados.
        - String explicativa (motivo da rejeição) caso nenhum setup seja acionado.
        """
        if len(df) < 5:
            return [], "Dados insuficientes (menos de 5 candles)."

        enabled = getattr(config, 'CONFIG_SETUPS', None) or {}
        setups_found = []
        reasons = []
        
        c_last = df.iloc[-1]
        c_prev = df.iloc[-2]
        offset = tick_size * tick_offset

        def _enabled(setup_name: str) -> bool:
            return enabled.get(setup_name, True)
        
        # ----------------------------------------------------
        # SETUP ABERTURA (Fechamento de GAP)
        # ----------------------------------------------------
        if 'time' in df.columns and _enabled("GAP"):
            # Verifica se é o primeiro candle do dia
            is_first_candle = c_last['time'].date() != c_prev['time'].date()
            if is_first_candle:
                gap_percent = abs(c_last['open'] - c_prev['close']) / c_prev['close'] * 100
                if gap_percent > 0.5:
                    if c_last['open'] > c_prev['close'] and c_last['close'] < c_last['open']:
                        # Gap de Alta, candle fechou negativo (vermelho) -> Venda
                        setups_found.append({
                            "setup": "GAP",
                            "action": "sell",
                            "trigger_price": c_last['low'] - offset,
                            "stop_loss": c_last['high'],
                            "score": 50, # Alta prioridade
                            "target": c_prev['close']
                        })
                    elif c_last['open'] < c_prev['close'] and c_last['close'] > c_last['open']:
                        # Gap de Baixa, candle fechou positivo (verde) -> Compra
                        setups_found.append({
                            "setup": "GAP",
                            "action": "buy",
                            "trigger_price": c_last['high'] + offset,
                            "stop_loss": c_last['low'],
                            "score": 50,
                            "target": c_prev['close']
                        })
                    else:
                        reasons.append(f"GAP de Abertura ({gap_percent:.2f}%): Direção do candle não favorece fechamento.")
                else:
                    reasons.append(f"GAP de Abertura minúsculo ({gap_percent:.2f}% < 0.5%). Ignorado.")
        
        # ----------------------------------------------------
        # SETUP 9.1 (Reversão de Tendência Curta da EMA9)
        # ----------------------------------------------------
        if _enabled("9.1"):
            if df['ema9_down'].iloc[-2] and df['ema9_up'].iloc[-1]:
                setups_found.append({
                    "setup": "9.1", "action": "buy",
                    "trigger_price": c_last['high'] + offset,
                    "stop_loss": c_last['low'], "score": 10
                })
            elif df['ema9_up'].iloc[-2] and df['ema9_down'].iloc[-1]:
                setups_found.append({
                    "setup": "9.1", "action": "sell",
                    "trigger_price": c_last['low'] - offset,
                    "stop_loss": c_last['high'], "score": 10
                })
            else:
                reasons.append("9.1 Falhou: EMA9 não virou neste candle.")

        # ----------------------------------------------------
        # SETUP 9.2 (Correção Leve contra a EMA9)
        # ----------------------------------------------------
        if _enabled("9.2"):
            if df['ema9_up'].iloc[-1] and df['ema9_up'].iloc[-2]:
                if c_last['low'] < c_prev['low']:
                    setups_found.append({
                        "setup": "9.2", "action": "buy",
                        "trigger_price": c_last['high'] + offset,
                        "stop_loss": c_last['low'], "score": 15
                    })
                else:
                    reasons.append("9.2 Compra Falhou: EMA9 aponta para cima, mas a minima nao perdeu a minima anterior.")
            elif df['ema9_down'].iloc[-1] and df['ema9_down'].iloc[-2]:
                if c_last['high'] > c_prev['high']:
                    setups_found.append({
                        "setup": "9.2", "action": "sell",
                        "trigger_price": c_last['low'] - offset,
                        "stop_loss": c_last['high'], "score": 15
                    })
                else:
                    reasons.append("9.2 Venda Falhou: EMA9 aponta para baixo, mas a maxima nao superou a maxima anterior.")

        # ----------------------------------------------------
        # SETUP 9.3 (Correção Profunda com 2 fechamentos)
        # ----------------------------------------------------
        if len(df) >= 4 and _enabled("9.3"):
            if df['ema9_up'].iloc[-1]:
                ref_candle = df.iloc[-3]
                c1 = df.iloc[-2]
                c2 = df.iloc[-1]
                if ref_candle['close'] < df['low'].iloc[-4] and c1['close'] < ref_candle['close'] and c2['close'] < ref_candle['close']:
                    setups_found.append({
                        "setup": "9.3", "action": "buy",
                        "trigger_price": c2['high'] + offset,
                        "stop_loss": min(c1['low'], c2['low']), "score": 20
                    })
            elif df['ema9_down'].iloc[-1]:
                ref_candle = df.iloc[-3]
                c1 = df.iloc[-2]
                c2 = df.iloc[-1]
                if ref_candle['close'] > df['high'].iloc[-4] and c1['close'] > ref_candle['close'] and c2['close'] > ref_candle['close']:
                    setups_found.append({
                        "setup": "9.3", "action": "sell",
                        "trigger_price": c2['low'] - offset,
                        "stop_loss": max(c1['high'], c2['high']), "score": 20
                    })

        # ----------------------------------------------------
        # SETUP 9.4 (Falsa Reversão da EMA9)
        # ----------------------------------------------------
        if len(df) >= 4 and _enabled("9.4"):
            if df['ema9_up'].iloc[-3] and df['ema9_down'].iloc[-2] and df['ema9_up'].iloc[-1]:
                if df['low'].iloc[-1] >= df['low'].iloc[-2]:
                    setups_found.append({
                        "setup": "9.4", "action": "buy",
                        "trigger_price": df['high'].iloc[-1] + offset,
                        "stop_loss": df['low'].iloc[-2], "score": 25
                    })
            elif df['ema9_down'].iloc[-3] and df['ema9_up'].iloc[-2] and df['ema9_down'].iloc[-1]:
                if df['high'].iloc[-1] <= df['high'].iloc[-2]:
                    setups_found.append({
                        "setup": "9.4", "action": "sell",
                        "trigger_price": df['low'].iloc[-1] - offset,
                        "stop_loss": df['high'].iloc[-2], "score": 25
                    })

        # ----------------------------------------------------
        # PONTO CONTÍNUO (PC)
        # ----------------------------------------------------
        if _enabled("PC") and df.get('sma21_up') is not None and df['sma21_up'].iloc[-1] and df['sma21_up'].iloc[-2]:
            dist_to_sma = c_last['low'] - df['sma21'].iloc[-1]
            atr = df['atr'].iloc[-1]
            if 0 <= dist_to_sma <= (atr * 0.3):
                setups_found.append({
                    "setup": "PC", "action": "buy",
                    "trigger_price": c_last['high'] + offset,
                    "stop_loss": c_last['low'], "score": 30
                })

        # ----------------------------------------------------
        # FFFD (Fechou Fora, Fechou Dentro)
        # ----------------------------------------------------
        if _enabled("FFFD") and df.get('bollinger_lower') is not None and c_prev['close'] < df['bollinger_lower'].iloc[-2]:
            if c_last['close'] > df['bollinger_lower'].iloc[-1]:
                setups_found.append({
                    "setup": "FFFD", "action": "buy",
                    "trigger_price": c_last['high'] + offset,
                    "stop_loss": min(c_last['low'], c_prev['low']), "score": 35
                })
        
        if _enabled("FFFD") and df.get('bollinger_upper') is not None and c_prev['close'] > df['bollinger_upper'].iloc[-2]:
            if c_last['close'] < df['bollinger_upper'].iloc[-1]:
                setups_found.append({
                    "setup": "FFFD", "action": "sell",
                    "trigger_price": c_last['low'] - offset,
                    "stop_loss": max(c_last['high'], c_prev['high']), "score": 35
                })

        # ----------------------------------------------------
        # SETUP D'INAPOLI (2º Fundo acima + Média Deslocada)
        # ----------------------------------------------------
        if _enabled("DiNapoli") and df.get('ema12_displaced') is not None and len(df) >= 6 and not np.isnan(df['ema12_displaced'].iloc[-1]):
            # Busca o 2º fundo recente (mínima do candle atual x candles anteriores)
            lowest2 = c_prev['low']
            lowest1 = df['low'].iloc[-3]
            # Certificar que houve um fundo antes do fundo 1
            if lowest1 < df['low'].iloc[-4] and lowest2 >= lowest1:
                # 2º fundo deve fechar acima da média deslocada
                if c_prev['close'] > df['ema12_displaced'].iloc[-2]:
                    setups_found.append({
                        "setup": "DiNapoli", "action": "buy",
                        "trigger_price": c_prev['high'] + offset,
                        "stop_loss": c_prev['low'], "score": 28
                    })

        # ----------------------------------------------------
        # SETUP IFR2 (IFR extremo + MME50)
        # ----------------------------------------------------
        if _enabled("IFR2") and df.get('rsi2') is not None and df.get('ema50_up') is not None:
            if not np.isnan(df['rsi2'].iloc[-1]) and df['rsi2'].iloc[-1] <= 5 and df['ema50_up'].iloc[-1] and c_last['close'] > df['ema50'].iloc[-1]:
                # Rompimento da máxima do candle de sinal (que furou a MM13)
                if c_last['close'] > df['sma13'].iloc[-1]:
                    setups_found.append({
                        "setup": "IFR2", "action": "buy",
                        "trigger_price": c_last['high'] + offset,
                        "stop_loss": c_last['low'], "score": 22
                    })

        # ----------------------------------------------------
        # SETUP SAR (Machado — SAR + IFR14 + MM13)
        # ----------------------------------------------------
        if _enabled("SAR") and df.get('sar') is not None and df.get('rsi14') is not None and not np.isnan(df['sar'].iloc[-1]):
            # Compra: SAR sob o preço (alta), IFR14>50 e fechamento acima da MM13
            if df['sar'].iloc[-1] < c_last['low'] and not np.isnan(df['rsi14'].iloc[-1]) and df['rsi14'].iloc[-1] > 50 and c_last['close'] > df['sma13'].iloc[-1]:
                setups_found.append({
                    "setup": "SAR", "action": "buy",
                    "trigger_price": c_last['high'] + offset,
                    "stop_loss": c_last['low'], "score": 26
                })

        # ----------------------------------------------------
        # SETUP ROMPIMENTO FALSO (Alan Farley)
        # ----------------------------------------------------
        if _enabled("RompFalso") and len(df) >= 6:
            # Compra: perda de suporte (mínima anterior), preço volta para dentro
            sup = df['low'].iloc[-4]
            if c_prev['close'] < sup and c_last['close'] > sup and c_last['low'] < sup:
                setups_found.append({
                    "setup": "RompFalso", "action": "buy",
                    "trigger_price": c_last['high'] + offset,
                    "stop_loss": min(c_last['low'], c_prev['low']), "score": 27
                })
            # Venda: falso rompimento de resistência
            res = df['high'].iloc[-4]
            if c_prev['close'] > res and c_last['close'] < res and c_last['high'] > res:
                setups_found.append({
                    "setup": "RompFalso", "action": "sell",
                    "trigger_price": c_last['low'] - offset,
                    "stop_loss": max(c_last['high'], c_prev['high']), "score": 27
                })

        # ----------------------------------------------------
        # FILTRO MACRO (SMA 200) e ORDENAÇÃO
        # ----------------------------------------------------
        valid_setups = []
        for s in setups_found:
            sma200_val = df['sma200'].iloc[-1]
            # GAP Setup is exempt from SMA200 filter because it's an aggressive reversion trade
            if s["setup"] == "GAP":
                valid_setups.append(s)
            elif np.isnan(sma200_val):
                # Dados insuficientes para a media de 200: permissivo (igual MTF/RVOL)
                valid_setups.append(s)
            elif s["action"] == "buy" and c_last['close'] > sma200_val:
                valid_setups.append(s)
            elif s["action"] == "sell" and c_last['close'] < sma200_val:
                valid_setups.append(s)
            else:
                reasons.append(f"{s['setup']} Falhou: Tendência de longo prazo (SMA200) contra a operação.")

        valid_setups = sorted(valid_setups, key=lambda x: x['score'], reverse=True)
        
        # Injeta o contexto de ML em cada setup valido retornado
        if valid_setups:
            swing_h, swing_l = swing_levels(df, lookback=20)
            
            # Formata os indicadores com tratamento para np.nan
            def _safe_float(val):
                try:
                    f = float(val)
                    return f if not np.isnan(f) else None
                except Exception:
                    return None
            
            ml_context = {
                "ohlcv": {
                    "open": _safe_float(c_last.get('open')),
                    "high": _safe_float(c_last.get('high')),
                    "low": _safe_float(c_last.get('low')),
                    "close": _safe_float(c_last.get('close')),
                    "tick_volume": _safe_float(c_last.get('tick_volume')),
                    "real_volume": _safe_float(c_last.get('real_volume'))
                },
                "trend": {
                    "ema9": _safe_float(c_last.get('ema9')),
                    "sma21": _safe_float(c_last.get('sma21')),
                    "sma200": _safe_float(c_last.get('sma200')),
                },
                "momentum": {
                    "rsi9": _safe_float(c_last.get('rsi9')),
                    "rsi14": _safe_float(c_last.get('rsi14')),
                    "sar": _safe_float(c_last.get('sar'))
                },
                "volatility": {
                    "atr": _safe_float(c_last.get('atr')),
                    "bollinger_bandwidth": _safe_float((c_last.get('bollinger_upper', 0) - c_last.get('bollinger_lower', 0)) / c_last.get('bollinger_mid', 1)) if c_last.get('bollinger_mid') else None
                },
                "liquidity": {
                    "vwap_dist": _safe_float(c_last.get('close') - c_last.get('vwap')) if c_last.get('vwap') else None
                },
                "fibonacci": {
                    "swing_high": _safe_float(swing_h),
                    "swing_low": _safe_float(swing_l)
                },
                "time": {}
            }
            
            if 'time' in c_last and pd.notnull(c_last['time']):
                try:
                    dt = pd.to_datetime(c_last['time'])
                    ml_context["time"] = {
                        "hour": dt.hour,
                        "minute": dt.minute,
                        "day_of_week": dt.dayofweek
                    }
                except Exception:
                    pass
            
            for s in valid_setups:
                is_long = s.get('action', '').lower() == 'buy'
                fib1, fib1618 = fib_extension_targets(s.get('trigger_price', c_last['close']), swing_h, swing_l, is_long)
                
                # Clone para evitar mutacao compartilhada caso um setup modifique depois
                s_context = dict(ml_context)
                s_context["fibonacci"] = dict(ml_context["fibonacci"])
                s_context["fibonacci"]["fib_1_0"] = _safe_float(fib1)
                s_context["fibonacci"]["fib_1_618"] = _safe_float(fib1618)
                
                s['ml_context'] = s_context
        
        # Seleciona o motivo mais relevante para informar o usuário caso não haja setups
        # Prioriza rejeição de 9.2 (que indica tendência ocorrendo) ou GAP
        final_reason = "Nenhum setup configurado ou EMA9 está flat."
        if not valid_setups and reasons:
            for r in reasons:
                if "9.2" in r or "GAP" in r or "SMA200" in r:
                    final_reason = r
                    break
            else:
                final_reason = reasons[0]

        return valid_setups, final_reason
