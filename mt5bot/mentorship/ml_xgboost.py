import os
import logging
import numpy as np
from mt5bot.core import config

logger = logging.getLogger("MLSupervisor")

class MLSupervisor:
    """
    Supervisor Inteligente de Risco.
    Carrega o modelo XGBoost treinado em Python e realiza a inferência em tempo real
    para prever a probabilidade de um trade dar lucro (Classe 1).
    Se a probabilidade for menor que o limiar (ML_MIN_WIN_PROB), o trade é vetado.
    """
    _models = {} # dict mapping symbol to model
    _loaded_symbols = set()
    _base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    @classmethod
    def load_model(cls, symbol: str):
        if symbol in cls._loaded_symbols:
            return
            
        if not getattr(config, 'ML_FILTER_ENABLED', False):
            return

        try:
            import xgboost as xgb
        except ImportError:
            logger.error("[ML Supervisor] Biblioteca xgboost nao encontrada. Execute: pip install xgboost")
            return

        model_filename = f"mt5bot_xgboost_{symbol}_v1.json"
        model_path = os.path.join(cls._base_dir, model_filename)

        if not os.path.exists(model_path):
            # Se não houver modelo treinado para este ativo, registramos como carregado (None) para não ficar tentando toda hora.
            logger.warning(f"[ML Supervisor] Sem cérebro de IA para {symbol} ({model_filename}). O filtro ML ignorará esse ativo.")
            cls._loaded_symbols.add(symbol)
            return

        try:
            # Carrega o modelo especialista deste ativo
            model = xgb.Booster()
            model.load_model(model_path)
            cls._models[symbol] = model
            cls._loaded_symbols.add(symbol)
            logger.info(f"[ML Supervisor] Cérebro de IA ativado para {symbol}: {model_filename}")
        except Exception as e:
            logger.error(f"[ML Supervisor] Erro ao carregar o modelo XGBoost para {symbol}: {e}")

    @classmethod
    def predict_trade(cls, symbol: str, setup_name: str, ml_context: dict) -> tuple[bool, float, str]:
        """
        Retorna (aprovado, prob_vitoria, razao)
        """
        if not getattr(config, 'ML_FILTER_ENABLED', False):
            return True, 1.0, "ML Desativado"

        cls.load_model(symbol)

        model = cls._models.get(symbol)
        if model is None:
            # Modelo não treinado para este ativo
            return True, 1.0, f"Modelo ML não encontrado para {symbol}"

        try:
            import xgboost as xgb
            import pandas as pd
        except ImportError:
            return True, 1.0, "xgboost nao instalado"

        # Modelos de ML são treinados primariamente com base nos parâmetros do mercado, 
        # permitindo que filtrem falsos sinais para os setups configurados (Russian BB, Judas, PC).
        if setup_name.lower() not in ["russian", "russian_bb", "russian bb", "judas", "pc"]:
            return True, 1.0, f"Setup {setup_name} nao avaliado pela IA"

        try:
            
            # Mapeamento do Feature Vector (X) exatamente na mesma ordem do treinamento
            # O array original do generate_ml_dataset era:
            # ['body_size', 'upper_wick', 'lower_wick', 'adx', 'z_score', 'atr', 'rsi14', 
            #  'bollinger_bandwidth', 'dist_ema9', 'dist_sma21', 'dist_sma200', 'dist_vwap', 
            #  'hour', 'day_of_week']
            
            def _safe_float(val):
                if val is None or np.isnan(val):
                    return 0.0
                return float(val)

            features = [
                _safe_float(ml_context.get('microstructure', {}).get('body_size')),
                _safe_float(ml_context.get('microstructure', {}).get('upper_wick')),
                _safe_float(ml_context.get('microstructure', {}).get('lower_wick')),
                _safe_float(ml_context.get('trend', {}).get('adx')),
                _safe_float(ml_context.get('regime', {}).get('z_score')),
                _safe_float(ml_context.get('volatility', {}).get('atr')),
                _safe_float(ml_context.get('momentum', {}).get('rsi14')),
                _safe_float(ml_context.get('volatility', {}).get('bollinger_bandwidth')),
                _safe_float(ml_context.get('relative_distances', {}).get('dist_ema9')),
                _safe_float(ml_context.get('relative_distances', {}).get('dist_sma21')),
                _safe_float(ml_context.get('relative_distances', {}).get('dist_sma200')),
                _safe_float(ml_context.get('relative_distances', {}).get('dist_vwap')),
                _safe_float(ml_context.get('time', {}).get('hour')),
                _safe_float(ml_context.get('time', {}).get('day_of_week')),
            ]

            # O modelo espera uma matriz bidimensional (1 amostra, N features)
            dmatrix = xgb.DMatrix(np.array([features]), feature_names=[
                'body_size', 'upper_wick', 'lower_wick', 'adx', 'z_score', 'atr', 'rsi14', 
                'bollinger_bandwidth', 'dist_ema9', 'dist_sma21', 'dist_sma200', 'dist_vwap', 
                'hour', 'day_of_week'
            ])
            
            # Predict retorna array de previsoes, pegamos a primeira
            # O xgb.Booster predict retorna a probabilidade da classe positiva (Classe 1)
            prob_win = float(model.predict(dmatrix)[0])
            
            min_prob = getattr(config, 'ML_MIN_WIN_PROB', 0.40)
            
            if prob_win < min_prob:
                reason = f"Probabilidade de vitoria ({prob_win:.2f}) abaixo do minimo ({min_prob:.2f})"
                return False, prob_win, reason
            else:
                return True, prob_win, "Aprovado pela IA"
                
        except Exception as e:
            logger.error(f"[ML Supervisor] Erro durante inferencia: {e}")
            # Em caso de erro, nao trave o bot
            return True, 1.0, f"Erro na inferencia: {e}"
