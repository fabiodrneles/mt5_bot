import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from mt5bot.core import config

def run_show_config():
    print("="*50)
    print("            CONFIGURACOES DO MT5BOT            ")
    print("="*50)
    
    # Risco
    risco = getattr(config, 'RISK_PER_TRADE_PERCENT', 1.0)
    risco_max = getattr(config, 'MAX_DAILY_LOSS_PERCENT', 2.0)
    print(f"Risco por Trade: {risco}% | Max Perda Diaria: {risco_max}%")
    
    # Filtro ML
    ml = getattr(config, 'ML_FILTER_ENABLED', False)
    ml_prob = getattr(config, 'ML_MIN_WIN_PROB', 0.40)
    print(f"Filtro XGBoost: {'ON' if ml else 'OFF'} | Probabilidade Minima: {ml_prob*100:.0f}%")
    
    # Setups globais
    setups = getattr(config, 'CONFIG_SETUPS', {})
    ativos = getattr(config, 'ASSET_SETUPS', {})
    print(f"Setups Globais Habilitados: {list(setups.keys())}")
    print(f"Ativos Monitorados: {list(ativos.keys())}")
    
    print("="*50)

if __name__ == "__main__":
    run_show_config()
