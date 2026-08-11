import sys
import json
import logging
import pandas as pd
import MetaTrader5 as mt5

from indicators import add_all_indicators
from setups import PalexScorer

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

        if not candles:
            # Hydration: O Brain puxa as velas da fonte da verdade (MT5)
            if not mt5.initialize():
                sys.stdout.write(json.dumps({"error": "Falha ao inicializar MT5", "symbol": symbol}) + '\n')
                sys.stdout.flush()
                return
            
            # Puxar 200 velas do timeframe H1 (exemplo padrão)
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 200)
            if rates is None or len(rates) == 0:
                sys.stdout.write(json.dumps({"error": "No candles found in MT5", "symbol": symbol}) + '\n')
                sys.stdout.flush()
                return
            
            df = pd.DataFrame(rates)
            # Converter tempo MT5
            df['time'] = pd.to_datetime(df['time'], unit='s')
        else:
            # Converter velas recebidas via stdin (se o Go enviar)
            df = pd.DataFrame(candles)
        
        # Opcional: ordenar pelo tempo caso nao venha ordenado
        if 'time' in df.columns:
            df = df.sort_values(by='time')

        # Adicionar os indicadores matemáticos (EMA9, SMA21, Bollinger, ATR...)
        df = add_all_indicators(df)
        
        # Avaliar gatilhos na matriz do Palex
        valid_setups = PalexScorer.evaluate_all(df)

        # Preparar a resposta (o melhor setup, se houver)
        response = {
            "symbol": symbol,
            "has_signal": False,
            "best_setup": None,
            "all_setups": valid_setups
        }

        if valid_setups:
            response["has_signal"] = True
            response["best_setup"] = valid_setups[0]

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
