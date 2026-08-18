import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from mt5bot.core import config

def run_market_status():
    print("="*60)
    print("                STATUS DO MERCADO                ")
    print("="*60)
    
    try:
        import MetaTrader5 as mt5
        if not mt5.initialize():
            print("Erro: Nao foi possivel conectar ao MT5.")
            return
            
        print(f"{'ATIVO':<10} | {'PRECO':<10} | {'SPREAD':<8} | {'TICK_VAL':<10} | {'MARGEM (0.01)':<15}")
        print("-" * 60)
        
        assets = getattr(config, 'ASSET_SETUPS', {}).keys()
        if not assets:
            # Fallback se não configurado
            assets = ['HK50', 'EURUSD', 'JP225']
            
        for symbol in assets:
            info = mt5.symbol_info(symbol)
            if info:
                price = (info.bid + info.ask) / 2
                spread = info.spread
                tick_value = info.trade_tick_value
                tick_size = info.trade_tick_size
                # Calculo de margem basico
                margin = mt5.order_calc_margin(mt5.ORDER_TYPE_BUY, symbol, 0.01, price)
                if margin is None:
                    margin = 0.0
                
                print(f"{symbol:<10} | {price:<10.5f} | {spread:<8} | {tick_value:<10.5f} | ${margin:<14.2f}")
            else:
                print(f"{symbol:<10} | Indisponivel no MT5")
                
        mt5.shutdown()
        
    except Exception as e:
        print(f"Erro ao ler mercado: {e}")
        
    print("="*60)

if __name__ == "__main__":
    run_market_status()
