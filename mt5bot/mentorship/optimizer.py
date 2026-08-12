import json
import os
import pandas as pd
from datetime import datetime

from mt5bot.core import logger

_ENRICHED_FILE = os.path.join(os.path.expanduser(os.getenv('APPDATA') or os.path.join('~')), 'mt5bot', 'virtual_rejections_enriched.json')
_CALIBRATIONS_FILE = os.path.join(os.path.expanduser(os.getenv('APPDATA') or os.path.join('~')), 'mt5bot', 'calibrations.json')

def get_session(time_iso):
    """Retorna a sessão de mercado baseado no horário UTC."""
    dt = datetime.fromisoformat(time_iso)
    hour = dt.hour
    if 0 <= hour < 8:
        return "Asian"
    elif 8 <= hour < 13:
        return "London"
    else:
        return "NY"

def run_optimization():
    if not os.path.exists(_ENRICHED_FILE):
        logger.error(f"Arquivo não encontrado: {_ENRICHED_FILE}. Rode o simulator.py primeiro.")
        return

    with open(_ENRICHED_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Filtrar apenas os que já têm resultado
    df = pd.DataFrame([d for d in data if "result" in d and d["result"] in ["win", "loss", "breakeven"]])
    
    if df.empty:
        logger.info("Nenhum dado simulado disponível para otimização.")
        return

    df['session'] = df['time'].apply(get_session)
    
    calibrations = {}
    
    # Agrupar por symbol, setup e motivo da rejeição
    grouped = df.groupby(['symbol', 'session', 'reason'])
    
    for name, group in grouped:
        symbol, session, reason = name
        
        wins = group[group['result'] == 'win']
        losses = group[group['result'] == 'loss']
        
        win_rate = len(wins) / len(group) if len(group) > 0 else 0
        
        avg_win = wins['pnl_pips'].mean() if not wins.empty else 0
        avg_loss = abs(losses['pnl_pips'].mean()) if not losses.empty else 0
        
        # Expectativa Matemática: (Win Rate * Avg Win) - (Loss Rate * Avg Loss)
        loss_rate = 1 - win_rate
        expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)
        
        logger.info(f"Otimizando {symbol} | Sessão: {session} | Filtro: {reason}")
        logger.info(f"  Amostras: {len(group)} | Win Rate: {win_rate:.2%} | Expectancy: {expectancy:.4f} pips")
        
        # Se a expectativa matemática for significativamente positiva, sugerimos um override
        if expectancy > 0 and len(group) >= 3: # Minimo de 3 amostras pra ter significancia básica
            if symbol not in calibrations:
                calibrations[symbol] = {}
            if session not in calibrations[symbol]:
                calibrations[symbol][session] = {}
                
            if "RVOL" in reason:
                # O filtro RVOL atual é muito rígido.
                # Recomendamos um RVOL menor (ex: 1.05 ou 1.0) para essa sessão.
                calibrations[symbol][session]["RVOL"] = 1.05
                logger.info(f"  -> [OVERRIDE GERADO] RVOL flexibilizado para 1.05 em {symbol} ({session})")
            elif "Scoring" in reason or "Macro" in reason:
                # Se for barrado por outro filtro, flexibiliza
                calibrations[symbol][session]["MACRO_OVERRIDE"] = True
                logger.info(f"  -> [OVERRIDE GERADO] MACRO_OVERRIDE ativado em {symbol} ({session})")

    if calibrations:
        with open(_CALIBRATIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(calibrations, f, indent=2, ensure_ascii=False)
        logger.info(f"Calibrações salvas em {_CALIBRATIONS_FILE}")
    else:
        logger.info("Nenhuma calibração lucrativa encontrada para os dados atuais.")

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
    run_optimization()
