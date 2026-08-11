import pandas as pd
import numpy as np

class PalexScorer:
    """
    Cérebro Matemático: Analisa o DataFrame de preços (com os indicadores já preenchidos)
    e retorna o setup de maior probabilidade para o momento.
    """

    @staticmethod
    def evaluate_all(df: pd.DataFrame) -> list:
        """
        Avalia o último candle completado (df.iloc[-1]) e verifica se há um gatilho armado.
        Retorna uma lista de setups identificados (ex: [{"setup": "9.1", "action": "buy", "trigger": 10.5, "stop": 10.0}])
        """
        if len(df) < 5:
            return []

        # Vamos analisar os últimos candles.
        # df.iloc[-1] é o candle mais recente fechado.
        
        setups_found = []
        
        # ----------------------------------------------------
        # SETUP 9.1 (Reversão de Tendência Curta da EMA9)
        # ----------------------------------------------------
        # COMPRA 9.1: EMA9 vinha caindo e agora virou para cima
        if df['ema9_down'].iloc[-2] and df['ema9_up'].iloc[-1]:
            setups_found.append({
                "setup": "9.1",
                "action": "buy",
                "trigger_price": df['high'].iloc[-1] + 0.01,  # 1 centavo acima da máxima
                "stop_loss": df['low'].iloc[-1],
                "score": 10
            })
            
        # VENDA 9.1: EMA9 vinha subindo e agora virou para baixo
        if df['ema9_up'].iloc[-2] and df['ema9_down'].iloc[-1]:
            setups_found.append({
                "setup": "9.1",
                "action": "sell",
                "trigger_price": df['low'].iloc[-1] - 0.01,
                "stop_loss": df['high'].iloc[-1],
                "score": 10
            })
            
        # ----------------------------------------------------
        # SETUP 9.2 (Correção Leve contra a EMA9)
        # ----------------------------------------------------
        # COMPRA 9.2: EMA9 apontando para cima, mas o candle atual FECHOU abaixo da MÍNIMA do candle anterior.
        if df['ema9_up'].iloc[-1] and df['ema9_up'].iloc[-2]:
            if df['close'].iloc[-1] < df['low'].iloc[-2]:
                setups_found.append({
                    "setup": "9.2",
                    "action": "buy",
                    "trigger_price": df['high'].iloc[-1] + 0.01,
                    "stop_loss": df['low'].iloc[-1],
                    "score": 15
                })
        
        # VENDA 9.2: EMA9 apontando para baixo, mas o candle atual FECHOU acima da MÁXIMA do candle anterior.
        if df['ema9_down'].iloc[-1] and df['ema9_down'].iloc[-2]:
            if df['close'].iloc[-1] > df['high'].iloc[-2]:
                setups_found.append({
                    "setup": "9.2",
                    "action": "sell",
                    "trigger_price": df['low'].iloc[-1] - 0.01,
                    "stop_loss": df['high'].iloc[-1],
                    "score": 15
                })

        # ----------------------------------------------------
        # SETUP 9.3 (Correção Profunda com 2 fechamentos)
        # ----------------------------------------------------
        # COMPRA 9.3: EMA9 subindo. Procuramos 1 fechamento abaixo da mínima (referência), seguido por pelo menos +1 fechamento abaixo da referência.
        if df['ema9_up'].iloc[-1] and len(df) >= 4:
            # Lógica simplificada: se os dois últimos fecharam abaixo do terceiro (referência)
            ref_candle = df.iloc[-3]
            c1 = df.iloc[-2]
            c2 = df.iloc[-1]
            if ref_candle['close'] < df['low'].iloc[-4]: # Candle referência fechou abaixo da mínima anterior
                if c1['close'] < ref_candle['close'] and c2['close'] < ref_candle['close']:
                    setups_found.append({
                        "setup": "9.3",
                        "action": "buy",
                        "trigger_price": c2['high'] + 0.01,
                        "stop_loss": min(c1['low'], c2['low']),
                        "score": 20
                    })

        # VENDA 9.3: EMA9 descendo. Referência fecha acima da máxima. Os dois seguintes fecham acima da referência.
        if df['ema9_down'].iloc[-1] and len(df) >= 4:
            ref_candle = df.iloc[-3]
            c1 = df.iloc[-2]
            c2 = df.iloc[-1]
            if ref_candle['close'] > df['high'].iloc[-4]:
                if c1['close'] > ref_candle['close'] and c2['close'] > ref_candle['close']:
                    setups_found.append({
                        "setup": "9.3",
                        "action": "sell",
                        "trigger_price": c2['low'] - 0.01,
                        "stop_loss": max(c1['high'], c2['high']),
                        "score": 20
                    })

        # ----------------------------------------------------
        # SETUP 9.4 (Falsa Reversão da EMA9)
        # ----------------------------------------------------
        # COMPRA 9.4: EMA9 vinha subindo, candle T-2 virou pra baixo. Candle T-1 virou pra cima logo em seguida (e não perdeu a mínima).
        if len(df) >= 4:
            if df['ema9_up'].iloc[-3] and df['ema9_down'].iloc[-2] and df['ema9_up'].iloc[-1]:
                # Mínima do candle que virou pra baixo (T-2) não foi perdida pelo candle (T-1)
                if df['low'].iloc[-1] >= df['low'].iloc[-2]:
                    setups_found.append({
                        "setup": "9.4",
                        "action": "buy",
                        "trigger_price": df['high'].iloc[-1] + 0.01,
                        "stop_loss": df['low'].iloc[-2],
                        "score": 25
                    })

        # VENDA 9.4: EMA9 vinha descendo, virou pra cima (T-2), virou pra baixo (T-1) sem romper a máxima.
        if len(df) >= 4:
            if df['ema9_down'].iloc[-3] and df['ema9_up'].iloc[-2] and df['ema9_down'].iloc[-1]:
                if df['high'].iloc[-1] <= df['high'].iloc[-2]:
                    setups_found.append({
                        "setup": "9.4",
                        "action": "sell",
                        "trigger_price": df['low'].iloc[-1] - 0.01,
                        "stop_loss": df['high'].iloc[-2],
                        "score": 25
                    })

        # ----------------------------------------------------
        # PONTO CONTÍNUO (PC)
        # ----------------------------------------------------
        # COMPRA: Retração até tocar/chegar muito perto da SMA21 em tendência de alta
        if df['sma21_up'].iloc[-1] and df['sma21_up'].iloc[-2]:
            dist_to_sma = df['low'].iloc[-1] - df['sma21'].iloc[-1]
            atr = df['atr'].iloc[-1]
            # Se a mínima encostar ou chegar perto (até 1/3 do ATR) da SMA21
            if 0 <= dist_to_sma <= (atr * 0.3):
                setups_found.append({
                    "setup": "PC",
                    "action": "buy",
                    "trigger_price": df['high'].iloc[-1] + 0.01,
                    "stop_loss": df['low'].iloc[-1],
                    "score": 30
                })

        # ----------------------------------------------------
        # FFFD (Fechou Fora, Fechou Dentro)
        # ----------------------------------------------------
        # COMPRA: Fechou abaixo da banda inferior (T-2), fechou dentro (acima da inferior) em (T-1)
        if df['close'].iloc[-2] < df['bollinger_lower'].iloc[-2]:
            if df['close'].iloc[-1] > df['bollinger_lower'].iloc[-1]:
                setups_found.append({
                    "setup": "FFFD",
                    "action": "buy",
                    "trigger_price": df['high'].iloc[-1] + 0.01,
                    "stop_loss": min(df['low'].iloc[-1], df['low'].iloc[-2]),
                    "score": 35  # Extreme reversion
                })
        
        # VENDA: Fechou acima da banda superior (T-2), fechou dentro em (T-1)
        if df['close'].iloc[-2] > df['bollinger_upper'].iloc[-2]:
            if df['close'].iloc[-1] < df['bollinger_upper'].iloc[-1]:
                setups_found.append({
                    "setup": "FFFD",
                    "action": "sell",
                    "trigger_price": df['low'].iloc[-1] - 0.01,
                    "stop_loss": max(df['high'].iloc[-1], df['high'].iloc[-2]),
                    "score": 35
                })

        # ----------------------------------------------------
        # FILTRO MACRO (SMA 200) e ORDENAÇÃO
        # ----------------------------------------------------
        # Remover setups de compra abaixo da MM200 e vendas acima da MM200
        valid_setups = []
        for s in setups_found:
            if s["action"] == "buy" and df['close'].iloc[-1] > df['sma200'].iloc[-1]:
                valid_setups.append(s)
            elif s["action"] == "sell" and df['close'].iloc[-1] < df['sma200'].iloc[-1]:
                valid_setups.append(s)

        # Ordenar por Score (Golden Setups no topo)
        valid_setups = sorted(valid_setups, key=lambda x: x['score'], reverse=True)
        return valid_setups
