import json
import os
from datetime import datetime, timezone

from mt5bot.core import logger

_CALIBRATIONS_FILE = os.path.join(os.path.expanduser(os.getenv('APPDATA') or os.path.join('~')), 'mt5bot', 'calibrations.json')

class AdaptiveSupervisor:
    """
    Supervisor Adaptativo que intercepta vetos de filtros estáticos e, 
    consultando a base de aprendizado contínuo (calibrations.json),
    decide se deve emitir um OVERRIDE baseado no contexto atual (Regime/Sessão).
    """
    _calibrations = {}
    _loaded = False

    @classmethod
    def load_calibrations(cls):
        if os.path.exists(_CALIBRATIONS_FILE):
            try:
                with open(_CALIBRATIONS_FILE, 'r', encoding='utf-8') as f:
                    cls._calibrations = json.load(f)
                cls._loaded = True
                logger.info("[Mentorship] Adaptive Supervisor carregou a base de calibrações de sucesso.")
            except Exception as e:
                logger.error(f"[Mentorship] Erro ao carregar calibrações: {e}")
        else:
            cls._calibrations = {}
            cls._loaded = True

    @staticmethod
    def _get_current_session():
        hour = datetime.now(timezone.utc).hour
        if 0 <= hour < 8:
            return "Asian"
        elif 8 <= hour < 13:
            return "London"
        else:
            return "NY"

    @classmethod
    def check_override(cls, symbol, reason, current_rvol=None) -> bool:
        """
        Retorna True se o trade, apesar de vetado pelos filtros, 
        deve ser autorizado por ter expectativa matemática positiva neste contexto.
        """
        if not cls._loaded:
            cls.load_calibrations()
            
        if not cls._calibrations:
            return False

        if symbol not in cls._calibrations:
            return False
            
        session = cls._get_current_session()
        if session not in cls._calibrations[symbol]:
            return False
            
        session_rules = cls._calibrations[symbol][session]

        # Tratamento específico para o filtro de RVOL
        if "RVOL" in reason:
            override_threshold = session_rules.get("RVOL")
            if override_threshold is not None:
                if current_rvol is not None and current_rvol >= override_threshold:
                    logger.warning(f"🤖 [MENTORSHIP OVERRIDE] Filtro RVOL flexibilizado para {override_threshold} "
                                   f"(Contexto: {symbol} Sessão {session}). Trade Autorizado!")
                    return True
                
        # Tratamento genérico para outros filtros
        if "Scoring" in reason or "Macro" in reason:
            if session_rules.get("MACRO_OVERRIDE"):
                logger.warning(f"🤖 [MENTORSHIP OVERRIDE] Filtro {reason} ignorado "
                               f"(Contexto: {symbol} Sessão {session}). Trade Autorizado!")
                return True

        return False
