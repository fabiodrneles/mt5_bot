import sys
import os
import json
import logging
import pandas as pd
import MetaTrader5 as mt5

# A raiz do projeto precisa estar no path para importar config/executor/tracker e o package brain.*
# Isso permite rodar este script de qualquer cwd (ex.: `python ../brain/main.py` a partir de maestro/).
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from mt5bot.engine.indicators import add_all_indicators
from mt5bot.engine.strategy import StrategyScorer

# Configuracao de log para escrever no stderr (para não sujar o stdout que é usado para IPC)
logging.basicConfig(level=logging.INFO, stream=sys.stderr, format='%(asctime)s - %(levelname)s - %(message)s')

def process_payload(payload_str: str):
    """
    Processa um payload JSON recebido do Maestro (Golang).
    Espera-se: {"symbol": "WIN", "candles": [{"time":123, "open":10, "high":12, "low":9, "close":11}, ...]}
    """
    try:
        data = json.loads(payload_str)
        if 'ping' in data:
            # Heartbeat check
            sys.stdout.write(json.dumps({"pong": True}) + '\n')
            sys.stdout.flush()
            return

        symbol = data.get("symbol")
        candles = data.get("candles", [])
        timeframe_str = data.get("timeframe", "H1").upper()

        if not candles:
            # Hydration: O Brain puxa as velas da fonte da verdade (MT5)
            if not mt5.initialize():
                sys.stdout.write(json.dumps({"error": "Falha ao inicializar MT5", "symbol": symbol}) + '\n')
                sys.stdout.flush()
                return
            
            tf_map = {
                "M1": mt5.TIMEFRAME_M1,
                "M5": mt5.TIMEFRAME_M5,
                "M15": mt5.TIMEFRAME_M15,
                "M30": mt5.TIMEFRAME_M30,
                "H1": mt5.TIMEFRAME_H1,
                "H4": mt5.TIMEFRAME_H4,
                "D1": mt5.TIMEFRAME_D1,
            }
            tf = tf_map.get(timeframe_str, mt5.TIMEFRAME_H1)
            
            # Puxar 200 velas do timeframe configurado
            rates = mt5.copy_rates_from_pos(symbol, tf, 0, 200)
            if rates is None or len(rates) == 0:
                sys.stdout.write(json.dumps({"error": "No candles found in MT5", "symbol": symbol}) + '\n')
                sys.stdout.flush()
                return
            
            df = pd.DataFrame(rates)
            # Converter tempo MT5 (epoch em segundos) para datetime
            df['time'] = pd.to_datetime(df['time'], unit='s')
        else:
            # Converter velas recebidas via stdin (se o Go enviar)
            df = pd.DataFrame(candles)
            if 'time' in df.columns:
                df['time'] = pd.to_datetime(df['time'], unit='s')
        
        # Opcional: ordenar pelo tempo caso nao venha ordenado
        if 'time' in df.columns:
            df = df.sort_values(by='time')

        # Adicionar os indicadores matemáticos (EMA9, SMA21, Bollinger, ATR...)
        df = add_all_indicators(df)
        
        # Invocar a maquina de estados stateless para o ciclo atual
        from mt5bot.execution import execution_manager
        
        action = data.get("action", "scan")
        is_study_mode = (action == "study")
        
        state = execution_manager.manage_cycle(symbol, df, timeframe_name=timeframe_str, is_study_mode=is_study_mode)

        # Retornar que o processamento do tick foi concluído com sucesso
        response = {
            "symbol": symbol,
            "status": "processed",
            "state_text": state
        }

        sys.stdout.write(json.dumps(response) + '\n')
        sys.stdout.flush()

    except json.JSONDecodeError:
        logging.error("Recebido JSON invalido")
        sys.stdout.write(json.dumps({"error": "Invalid JSON"}) + '\n')
        sys.stdout.flush()
    except Exception as e:
        logging.error(f"Erro ao processar dados: {e}")
        sys.stdout.write(json.dumps({"error": str(e)}) + '\n')
        sys.stdout.flush()

def main():
    """
    Loop principal. Aguarda dados no stdin e envia resultados no stdout.
    """
    logging.info("Python Brain Worker iniciado. Aguardando instrucoes via stdin...")
    
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break # EOF (Go fechou o pipe)
            
            line = line.strip()
            if line:
                process_payload(line)
        except KeyboardInterrupt:
            logging.info("Processo interrompido.")
            break
        except Exception as e:
            logging.error(f"Erro critico: {e}")
            break

if __name__ == "__main__":
    main()
