import argparse
import sys
import time
from datetime import datetime
import pandas as pd
import numpy as np
from pathlib import Path
import MetaTrader5 as mt5

sys.path.append(str(Path(__file__).parent.parent))

from mt5bot.engine.indicators import add_all_indicators
from mt5bot.engine.vectorized_signals import generate_vectorized_signals

def main():
    parser = argparse.ArgumentParser(description="Simulador Vetorizado (Hilpisch) - Rápido e Focado em IA")
    parser.add_argument("--months", type=int, default=1, help="Numero de meses para retroceder")
    parser.add_argument("--symbol", type=str, default="HK50", help="Ativo para simular")
    parser.add_argument("--setup", type=str, default="all", help="Setup especifico para analisar (ex: 91, 92, russian) ou 'all'")
    
    args = parser.parse_args()
    
    print("==================================================")
    print("   MOTOR VETORIZADO DE BACKTESTING (HILPISCH)    ")
    print("==================================================")
    print(f"Ativo: {args.symbol} | Meses: {args.months} | Setup Alvo: {args.setup}")
    
    if not mt5.initialize():
        print("Erro: Nao foi possivel inicializar o MetaTrader 5.")
        sys.exit(1)
        
    info = mt5.symbol_info(args.symbol)
    if not info:
        print(f"Erro: Ativo {args.symbol} nao encontrado.")
        mt5.shutdown()
        sys.exit(1)
        
    candles_per_month = 9000
    total_candles = args.months * candles_per_month
    
    if total_candles > 1000000:
        total_candles = 1000000
        
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Baixando ultimos {total_candles} candles (M5)...")
    rates = None
    while total_candles >= 5000:
        rates = mt5.copy_rates_from_pos(args.symbol, mt5.TIMEFRAME_M5, 0, total_candles)
        if rates is not None and len(rates) > 0:
            break
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Corretora nao tem {total_candles} candles. Reduzindo em 10000...")
        total_candles -= 10000
    
    if rates is None or len(rates) == 0:
        print("Erro: Nenhum dado retornado.")
        mt5.shutdown()
        sys.exit(1)
        
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    t0 = time.time()
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Calculando Indicadores (Bollinger, RSI, EMAs)...")
    df = add_all_indicators(df)
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Aplicando Matriz de Setups (Vetorizado)...")
    df = generate_vectorized_signals(df)
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Calculando Retornos de Estrategia...")
    # Retornos continuos logaritmicos do ativo
    df['returns'] = np.log(df['close'] / df['close'].shift(1))
    
    # Agregar todos os sinais caso setup=='all' (Simplificacao: assume operacao simultanea de todos com peso 1)
    if args.setup == 'all':
        signals_cols = [c for c in df.columns if c.startswith('signal_')]
        df['combined_signal'] = df[signals_cols].sum(axis=1)
        # Limita a 1/-1 para nao alavancar multiplos setups ativados ao mesmo tempo
        df['position'] = np.where(df['combined_signal'] > 0, 1, np.where(df['combined_signal'] < 0, -1, 0))
    else:
        col = f'signal_{args.setup}'
        if col in df.columns:
            df['position'] = df[col]
        else:
            print(f"Setup '{args.setup}' invalido ou nao mapeado.")
            sys.exit(1)
            
    # O retorno da estrategia e o sinal do periodo anterior vezes o retorno do periodo atual
    # Se estavamos comprados ontem, ganhamos com a alta de hoje.
    df['strategy_returns'] = df['position'].shift(1) * df['returns']
    
    t1 = time.time()
    
    # Calcular performance
    df.dropna(inplace=True)
    cum_returns = np.exp(df['returns'].cumsum()) - 1
    cum_strategy = np.exp(df['strategy_returns'].cumsum()) - 1
    
    total_trades = (df['position'].diff() != 0).sum()
    
    print("\n" + "="*50)
    print(f"RESULTADOS DA SIMULACAO VETORIZADA ({len(df)} candles)")
    print("="*50)
    print(f"Tempo de Processamento (Indicators + Sinais + Math): {(t1 - t0):.4f} segundos")
    print(f"Total de Transicoes de Posicao: {total_trades}")
    print(f"Retorno do Ativo (Buy & Hold):  {cum_returns.iloc[-1] * 100:.2f}%")
    print(f"Retorno da Estrategia:          {cum_strategy.iloc[-1] * 100:.2f}%")
    
    # Volatilidade Anualizada (aprox 288 candles por dia * 252 dias)
    vol_anual = df['strategy_returns'].std() * np.sqrt(288 * 252) * 100
    print(f"Volatilidade Anualizada:        {vol_anual:.2f}%")
    
    if vol_anual > 0:
        sharpe = (cum_strategy.iloc[-1]*100) / vol_anual
        print(f"Sharpe Ratio (Aprox):           {sharpe:.2f}")
    
    print("="*50)
    mt5.shutdown()

if __name__ == "__main__":
    main()
