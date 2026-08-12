import sys
import os
import time
import logging
import MetaTrader5 as mt5
from mt5bot.core import config

# A raiz do projeto precisa estar no path para importar config (o script roda a partir de maestro/).
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - SHUTDOWN - %(message)s')

def cancel_pending_orders():
    """Cancela todas as ordens pendentes (Buy Stop / Sell Stop)"""
    orders = mt5.orders_get()
    if orders is None:
        logging.error("Falha ao obter ordens do MT5.")
        return

    count = 0
    for order in orders:
        request = {
            "action": mt5.TRADE_ACTION_REMOVE,
            "order": order.ticket,
        }
        result = mt5.order_send(request)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            count += 1
            logging.info(f"Ordem {order.ticket} ({order.symbol}) cancelada com sucesso.")
        else:
            logging.error(f"Falha ao cancelar ordem {order.ticket}: {result.comment if result else 'N/A'}")
            
    logging.info(f"Total de {count} ordens pendentes canceladas.")

def close_all_positions():
    """Fecha todas as posicoes ativas a mercado."""
    positions = mt5.positions_get()
    if positions is None:
        logging.error("Falha ao obter posicoes do MT5.")
        return

    count = 0
    for pos in positions:
        tick = mt5.symbol_info_tick(pos.symbol)
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": pos.ticket,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
            "price": tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask,
            "deviation": 20,
            "magic": getattr(config, 'MAGIC', 1000),
            "comment": "Panic Close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(request)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            count += 1
            logging.info(f"Posicao {pos.ticket} ({pos.symbol}) fechada a mercado.")
        else:
            logging.error(f"Falha ao fechar posicao {pos.ticket}: {result.comment if result else 'N/A'}")
            
    logging.info(f"Total de {count} posicoes liquidadas.")

def create_no_trade_lock():
    """Cria um arquivo de lock para impedir que os workers abram novas operacoes."""
    try:
        with open(".no_new_trades", "w") as f:
            f.write("locked")
        logging.info("Lock .no_new_trades criado. Workers nao abrirao novos trades.")
    except Exception as e:
        logging.error(f"Falha ao criar lock: {e}")

def wait_flat():
    """Aguarda ate que todas as posicoes abertas sejam liquidadas."""
    create_no_trade_lock()
    logging.info("Aguardando zerar todas as posicoes. Pode demorar...")
    
    while True:
        positions = mt5.positions_get()
        if positions is None or len(positions) == 0:
            logging.info("Todas as posicoes foram zeradas! Pronto para desligar.")
            break
        
        logging.info(f"Ainda existem {len(positions)} posicoes ativas. Checando novamente em 30 segundos...")
        time.sleep(30)

def main():
    if len(sys.argv) < 2:
        print("Uso: python shutdown_manager.py <acao>")
        return

    action = sys.argv[1].lower()
    
    if not mt5.initialize():
        logging.error("Falha ao inicializar conexao com MT5 para shutdown.")
        return

    logging.info(f"Executando acao de shutdown institucional: {action}")

    if action == "cancel-open":
        cancel_pending_orders()
    elif action == "close-all":
        cancel_pending_orders()
        close_all_positions()
    elif action == "wait-flat":
        wait_flat()
    else:
        logging.warning(f"Acao desconhecida: {action}")

    mt5.shutdown()

if __name__ == "__main__":
    main()
