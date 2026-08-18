import sys
from pathlib import Path
import time

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from mt5bot.core import config

def close_position(pos):
    import MetaTrader5 as mt5
    
    symbol = pos.symbol
    lot = pos.volume
    order_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
    price = mt5.symbol_info_tick(symbol).bid if order_type == mt5.ORDER_TYPE_SELL else mt5.symbol_info_tick(symbol).ask
    
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": order_type,
        "position": pos.ticket,
        "price": price,
        "deviation": 50,
        "magic": getattr(config, 'MAGIC_NUMBER', 999),
        "comment": "PANIC_CLOSE",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    result = mt5.order_send(request)
    return result

def run_panic():
    print("="*60)
    print("                 !!! BOTAO DO PANICO !!!                 ")
    print("="*60)
    print("Iniciando desligamento de emergencia...")
    
    try:
        import MetaTrader5 as mt5
        if not mt5.initialize():
            print("Erro critico: Nao foi possivel conectar ao MT5 para fechar ordens!")
            return
            
        magic = getattr(config, 'MAGIC_NUMBER', 999)
        positions = mt5.positions_get()
        
        if positions is None or len(positions) == 0:
            print("Nenhuma posicao aberta encontrada no MT5.")
        else:
            bot_positions = [p for p in positions if p.magic == magic]
            if len(bot_positions) == 0:
                print("Nenhuma posicao pertencente a este robo foi encontrada.")
            else:
                print(f"Encontradas {len(bot_positions)} posicoes abertas do robo. Fechando a mercado...")
                
                for pos in bot_positions:
                    print(f"Fechando Ticket {pos.ticket} ({pos.symbol} lot {pos.volume})...")
                    res = close_position(pos)
                    if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                        print(" -> FECHADA COM SUCESSO")
                    else:
                        print(f" -> FALHA (codigo: {res.retcode if res else 'Unknown'})")
                        
        print("\nDesligamento de emergencia concluido!")
        print("NOTA: Certifique-se de parar o processo main.py no seu terminal.")
        mt5.shutdown()
        
    except Exception as e:
        print(f"Erro no botao de panico: {e}")
        
    print("="*60)

if __name__ == "__main__":
    run_panic()
