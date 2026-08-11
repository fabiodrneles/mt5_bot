import pandas as pd
import numpy as np

class PalexScorer:
    """
    Cérebro Matemático: Analisa o DataFrame de preços (com os indicadores já preenchidos)
    e retorna o setup de maior probabilidade para o momento, além de motivos verbosos
    caso nenhum setup seja ativado.
    """

    @staticmethod
    def evaluate_all(df: pd.DataFrame) -> tuple[list, str]:
        """
        Avalia o último candle completado (df.iloc[-1]) e verifica se há um gatilho armado.
        Retorna:
        - Lista de setups identificados.
        - String explicativa (motivo da rejeição) caso nenhum setup seja acionado.
        """
        if len(df) < 5:
            return [], "Dados insuficientes (menos de 5 candles)."

        setups_found = []
        reasons = []
        
        c_last = df.iloc[-1]
        c_prev = df.iloc[-2]
        c_prev2 = df.iloc[-3]
        
        # ----------------------------------------------------
        # SETUP ABERTURA (Fechamento de GAP)
        # ----------------------------------------------------
        if 'time' in df.columns:
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
                            "trigger_price": c_last['low'] - 0.01,
                            "stop_loss": c_last['high'],
                            "score": 50, # Alta prioridade
                            "target": c_prev['close']
                        })
                    elif c_last['open'] < c_prev['close'] and c_last['close'] > c_last['open']:
                        # Gap de Baixa, candle fechou positivo (verde) -> Compra
                        setups_found.append({
                            "setup": "GAP",
                            "action": "buy",
                            "trigger_price": c_last['high'] + 0.01,
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
        if df['ema9_down'].iloc[-2] and df['ema9_up'].iloc[-1]:
            setups_found.append({
                "setup": "9.1", "action": "buy",
                "trigger_price": c_last['high'] + 0.01,
                "stop_loss": c_last['low'], "score": 10
            })
        elif df['ema9_up'].iloc[-2] and df['ema9_down'].iloc[-1]:
            setups_found.append({
                "setup": "9.1", "action": "sell",
                "trigger_price": c_last['low'] - 0.01,
                "stop_loss": c_last['high'], "score": 10
            })
        else:
            reasons.append("9.1 Falhou: EMA9 não virou neste candle.")

        # ----------------------------------------------------
        # SETUP 9.2 (Correção Leve contra a EMA9)
        # ----------------------------------------------------
        if df['ema9_up'].iloc[-1] and df['ema9_up'].iloc[-2]:
            if c_last['close'] < c_prev['low']:
                setups_found.append({
                    "setup": "9.2", "action": "buy",
                    "trigger_price": c_last['high'] + 0.01,
                    "stop_loss": c_last['low'], "score": 15
                })
            else:
                reasons.append("9.2 Compra Falhou: EMA9 aponta para cima, mas fechamento não perdeu mínima anterior.")
        elif df['ema9_down'].iloc[-1] and df['ema9_down'].iloc[-2]:
            if c_last['close'] > c_prev['high']:
                setups_found.append({
                    "setup": "9.2", "action": "sell",
                    "trigger_price": c_last['low'] - 0.01,
                    "stop_loss": c_last['high'], "score": 15
                })
            else:
                reasons.append("9.2 Venda Falhou: EMA9 aponta para baixo, mas fechamento não superou máxima anterior.")

        # ----------------------------------------------------
        # SETUP 9.3 (Correção Profunda com 2 fechamentos)
        # ----------------------------------------------------
        if len(df) >= 4:
            if df['ema9_up'].iloc[-1]:
                ref_candle = df.iloc[-3]
                c1 = df.iloc[-2]
                c2 = df.iloc[-1]
                if ref_candle['close'] < df['low'].iloc[-4] and c1['close'] < ref_candle['close'] and c2['close'] < ref_candle['close']:
                    setups_found.append({
                        "setup": "9.3", "action": "buy",
                        "trigger_price": c2['high'] + 0.01,
                        "stop_loss": min(c1['low'], c2['low']), "score": 20
                    })
            elif df['ema9_down'].iloc[-1]:
                ref_candle = df.iloc[-3]
                c1 = df.iloc[-2]
                c2 = df.iloc[-1]
                if ref_candle['close'] > df['high'].iloc[-4] and c1['close'] > ref_candle['close'] and c2['close'] > ref_candle['close']:
                    setups_found.append({
                        "setup": "9.3", "action": "sell",
                        "trigger_price": c2['low'] - 0.01,
                        "stop_loss": max(c1['high'], c2['high']), "score": 20
                    })

        # ----------------------------------------------------
        # SETUP 9.4 (Falsa Reversão da EMA9)
        # ----------------------------------------------------
        if len(df) >= 4:
            if df['ema9_up'].iloc[-3] and df['ema9_down'].iloc[-2] and df['ema9_up'].iloc[-1]:
                if df['low'].iloc[-1] >= df['low'].iloc[-2]:
                    setups_found.append({
                        "setup": "9.4", "action": "buy",
                        "trigger_price": df['high'].iloc[-1] + 0.01,
                        "stop_loss": df['low'].iloc[-2], "score": 25
                    })
            elif df['ema9_down'].iloc[-3] and df['ema9_up'].iloc[-2] and df['ema9_down'].iloc[-1]:
                if df['high'].iloc[-1] <= df['high'].iloc[-2]:
                    setups_found.append({
                        "setup": "9.4", "action": "sell",
                        "trigger_price": df['low'].iloc[-1] - 0.01,
                        "stop_loss": df['high'].iloc[-2], "score": 25
                    })

        # ----------------------------------------------------
        # PONTO CONTÍNUO (PC)
        # ----------------------------------------------------
        if df.get('sma21_up') is not None and df['sma21_up'].iloc[-1] and df['sma21_up'].iloc[-2]:
            dist_to_sma = c_last['low'] - df['sma21'].iloc[-1]
            atr = df['atr'].iloc[-1]
            if 0 <= dist_to_sma <= (atr * 0.3):
                setups_found.append({
                    "setup": "PC", "action": "buy",
                    "trigger_price": c_last['high'] + 0.01,
                    "stop_loss": c_last['low'], "score": 30
                })

        # ----------------------------------------------------
        # FFFD (Fechou Fora, Fechou Dentro)
        # ----------------------------------------------------
        if df.get('bollinger_lower') is not None and c_prev['close'] < df['bollinger_lower'].iloc[-2]:
            if c_last['close'] > df['bollinger_lower'].iloc[-1]:
                setups_found.append({
                    "setup": "FFFD", "action": "buy",
                    "trigger_price": c_last['high'] + 0.01,
                    "stop_loss": min(c_last['low'], c_prev['low']), "score": 35
                })
        
        if df.get('bollinger_upper') is not None and c_prev['close'] > df['bollinger_upper'].iloc[-2]:
            if c_last['close'] < df['bollinger_upper'].iloc[-1]:
                setups_found.append({
                    "setup": "FFFD", "action": "sell",
                    "trigger_price": c_last['low'] - 0.01,
                    "stop_loss": max(c_last['high'], c_prev['high']), "score": 35
                })

        # ----------------------------------------------------
        # FILTRO MACRO (SMA 200) e ORDENAÇÃO
        # ----------------------------------------------------
        valid_setups = []
        for s in setups_found:
            # GAP Setup is exempt from SMA200 filter because it's an aggressive reversion trade
            if s["setup"] == "GAP":
                valid_setups.append(s)
            elif s["action"] == "buy" and c_last['close'] > df['sma200'].iloc[-1]:
                valid_setups.append(s)
            elif s["action"] == "sell" and c_last['close'] < df['sma200'].iloc[-1]:
                valid_setups.append(s)
            else:
                reasons.append(f"{s['setup']} Falhou: Tendência de longo prazo (SMA200) contra a operação.")

        valid_setups = sorted(valid_setups, key=lambda x: x['score'], reverse=True)
        
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
