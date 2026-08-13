import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Tenta importar o MT5. Se não estiver rodando no Windows com MT5 instalado, fará mock genérico para testes.
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    print("Aviso: MetaTrader5 não encontrado. Modo de simulação (Mock) será ativado se necessário.")

def get_historical_data(symbol: str, timeframe: int, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """Busca dados no MT5 para o Backtest."""
    if not MT5_AVAILABLE:
        print("Modo Mock: Gerando dados aleatórios para demonstração do WFO.")
        return _generate_mock_data(start_date, end_date)

    if not mt5.initialize():
        print("Erro: mt5.initialize() falhou")
        return pd.DataFrame()
    
    rates = mt5.copy_rates_range(symbol, timeframe, start_date, end_date)
    if rates is None or len(rates) == 0:
        print(f"Aviso: Sem dados para {symbol}")
        return pd.DataFrame()
    
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    return df

def _generate_mock_data(start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """Gera dataframe dummy para testes de CI/CD onde o MT5 não existe."""
    periods = int((end_date - start_date).total_seconds() / 3600)
    idx = pd.date_range(start=start_date, periods=periods, freq='h')
    df = pd.DataFrame({
        'open': np.random.randn(periods).cumsum() + 100,
        'high': 0.0, 'low': 0.0, 'close': 0.0, 'volume': 100
    }, index=idx)
    df['close'] = df['open'] + np.random.randn(periods)
    df['high'] = df[['open', 'close']].max(axis=1) + abs(np.random.randn(periods))
    df['low'] = df[['open', 'close']].min(axis=1) - abs(np.random.randn(periods))
    return df

def walk_forward_optimization(df: pd.DataFrame, num_windows: int, is_ratio: float = 0.7):
    """
    Divide o DataFrame histórico em 'num_windows'. 
    Para cada janela, divide o tempo em In-Sample (IS) e Out-Of-Sample (OOS).
    """
    total_len = len(df)
    window_size = total_len // num_windows
    
    results = []
    
    for i in range(num_windows):
        start_idx = i * window_size
        end_idx = start_idx + window_size if i < num_windows - 1 else total_len
        
        window_df = df.iloc[start_idx:end_idx]
        
        is_len = int(len(window_df) * is_ratio)
        is_df = window_df.iloc[:is_len]
        oos_df = window_df.iloc[is_len:]
        
        if is_df.empty or oos_df.empty:
            continue
            
        # Otimização In-Sample (busca melhor MME9 e MME21)
        best_param = optimize_in_sample(is_df)
        
        # Teste Cego Out-Of-Sample
        oos_pnl, oos_drawdown = test_out_of_sample(oos_df, best_param)
        
        results.append({
            'Window': i + 1,
            'IS_Start': is_df.index[0].strftime('%Y-%m-%d'),
            'IS_End': is_df.index[-1].strftime('%Y-%m-%d'),
            'OOS_Start': oos_df.index[0].strftime('%Y-%m-%d'),
            'OOS_End': oos_df.index[-1].strftime('%Y-%m-%d'),
            'Best_EMA': best_param,
            'OOS_PnL': round(oos_pnl, 4),
            'OOS_Drawdown': round(oos_drawdown, 4)
        })
        
    return pd.DataFrame(results)

def optimize_in_sample(df: pd.DataFrame) -> int:
    """Busca o período ideal para a EMA no In-Sample."""
    best_period = 9
    best_return = -9999.0
    
    for period in range(5, 22, 2):  # Testando períodos ímpares de 5 a 21
        ret, _ = backtest_logic(df, period)
        if ret > best_return:
            best_return = ret
            best_period = period
            
    return best_period

def test_out_of_sample(df: pd.DataFrame, param: int) -> tuple:
    """Retorna PnL e Drawdown do período OOS."""
    return backtest_logic(df, param)

def backtest_logic(df: pd.DataFrame, ema_period: int) -> tuple:
    """
    Simulação isolada de setups direcionais básicos.
    Em ambiente produtivo, importaria os triggers do strategy.py
    """
    df = df.copy()
    df['ema'] = df['close'].ewm(span=ema_period, adjust=False).mean()
    
    # Sinal basico: preço fechou acima da média
    df['signal'] = np.where(df['close'] > df['ema'], 1, -1)
    
    # Retorno diário da estratégia (com delay de 1 vela para evitar look-ahead)
    df['return'] = df['close'].pct_change() * df['signal'].shift(1)
    
    # Penalização por Slippage / Custos nas viradas de mão
    trades = df['signal'].diff().fillna(0).abs() > 0
    slippage_penalty = 0.0001 # 1 pip de slippage/spread médio percentual
    df.loc[trades, 'return'] -= slippage_penalty
    
    df['return'] = df['return'].fillna(0)
    
    # Calcula Curva de Capital (Base 1)
    df['equity_curve'] = (1 + df['return']).cumprod()
    
    total_return = df['equity_curve'].iloc[-1] - 1.0 if not df.empty else 0.0
    
    # Max Drawdown
    df['peak'] = df['equity_curve'].cummax()
    df['drawdown'] = (df['equity_curve'] - df['peak']) / df['peak']
    max_dd = df['drawdown'].min()
    
    return total_return, max_dd

if __name__ == "__main__":
    print("==================================================")
    print(" MT5Bot - Walk-Forward Optimization (WFO) Engine  ")
    print("==================================================")
    
    # Parâmetros Padrões
    symbol = "EURUSD"
    # Utilizar API do MT5 caso instalada
    timeframe = mt5.TIMEFRAME_H1 if MT5_AVAILABLE else 16385 
    end = datetime.now()
    start = end - timedelta(days=180) # 6 meses de histórico
    
    print(f"Ativo: {symbol} | Período: {start.strftime('%Y-%m-%d')} a {end.strftime('%Y-%m-%d')}")
    
    df = get_historical_data(symbol, timeframe, start, end)
    
    if not df.empty:
        print(f"Foram carregadas {len(df)} velas (candles).")
        wfo_results = walk_forward_optimization(df, num_windows=5, is_ratio=0.7)
        
        print("\n=== Matriz de Walk-Forward Optimization ===")
        print(wfo_results.to_string(index=False))
        
        # Análise de Robustez
        oos_positive = (wfo_results['OOS_PnL'] > 0).sum()
        total_windows = len(wfo_results)
        win_rate_windows = (oos_positive / total_windows) * 100
        
        print("\n=== Diagnóstico Quantitativo ===")
        print(f"Janelas OOS Lucrativas: {oos_positive} de {total_windows} ({win_rate_windows:.1f}%)")
        if win_rate_windows > 50:
            print("Status: APROVADO. O modelo demonstra robustez adaptativa fora da amostra.")
        else:
            print("Status: FALHOU. Indício de Overfitting. O modelo não sobrevive a dados desconhecidos.")
    else:
        print("Falha ao obter dados.")
