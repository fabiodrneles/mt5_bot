import numpy as np
import pandas as pd
from scipy import stats

def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.0) -> float:
    """
    Calcula o Sharpe Ratio anualizado.
    Assume que os retornos são diários ou por trade. O ajuste (252) é para dados diários.
    Se for intradiário, o fator de ajuste deve ser modificado (ex: 252 * 24 para H1).
    """
    if len(returns) < 2:
        return 0.0
    mean_ret = returns.mean()
    std_ret = returns.std()
    
    if std_ret == 0:
        return 0.0
        
    sharpe = (mean_ret - risk_free_rate) / std_ret
    return sharpe * np.sqrt(252)  # Fator fixo simplificado para retorno trade-by-trade

def permutation_test(actual_returns: pd.Series, n_permutations: int = 1000) -> tuple:
    """
    Randomiza (baralha) a ordem temporal dos retornos para ver se a curva de capital 
    foi fruto do acaso (se sim, embaralhar não deveria destruir o PnL consistentemente).
    """
    actual_pnl = actual_returns.sum()
    permuted_pnls = []
    
    for _ in range(n_permutations):
        # Embaralha os retornos
        shuffled = np.random.permutation(actual_returns.values)
        # Calcula PnL do caminho embaralhado
        permuted_pnls.append(np.sum(shuffled))
        
    permuted_pnls = np.array(permuted_pnls)
    
    # Calcula a probabilidade de uma permutação aleatória ser melhor que o retorno real
    p_value = np.sum(permuted_pnls >= actual_pnl) / n_permutations
    
    return actual_pnl, permuted_pnls, p_value

def calculate_p_value_t_test(returns: pd.Series) -> float:
    """
    Testa a hipótese nula de que a média dos retornos é zero ou negativa.
    Se p-value < 0.05, rejeitamos a hipótese nula (Sinal estatisticamente válido).
    """
    if len(returns) < 2 or returns.std() == 0:
        return 1.0
        
    t_stat, p_val = stats.ttest_1samp(returns.values, 0.0, alternative='greater')
    return p_val

def deflated_sharpe_ratio(actual_sharpe: float, n_trials: int, variance_of_sharpes: float = 1.0) -> float:
    """
    Aplica punição no Sharpe com base no número de tentativas (Backtests/Otimizações).
    Abordagem simplificada inspirada em López-Prado.
    """
    # Quanto mais testes você rodou para achar esse Sharpe, maior o desconto.
    euler_mascheroni = 0.5772156649
    expected_max_sr = np.sqrt(2 * np.log(n_trials)) if n_trials > 1 else 0
    
    adjusted_sharpe = actual_sharpe - expected_max_sr
    
    # Probabilidade (CDF da Normal) do SR desinflacionado
    dsr_prob = stats.norm.cdf(adjusted_sharpe)
    return dsr_prob

if __name__ == "__main__":
    print("==================================================")
    print(" MT5Bot - Motor de Validação Estatística (P-Value)")
    print("==================================================")
    
    # Simula o retorno (PnL) de 100 trades do MT5Bot
    np.random.seed(42)
    # Suponha um modelo com ligeira borda positiva (mean = 0.001)
    mock_returns = pd.Series(np.random.normal(loc=0.001, scale=0.01, size=100))
    
    print("1. Calculando Sharpe Ratio...")
    sr = calculate_sharpe_ratio(mock_returns)
    print(f"Sharpe Ratio (Trade-by-trade): {sr:.2f}")
    
    print("\n2. Rodando Teste de Permutação (1000 caminhos aleatórios)...")
    actual, perms, p_val_perm = permutation_test(mock_returns, n_permutations=1000)
    print(f"PnL Real: {actual:.4f}")
    print(f"P-Value (Permutação): {p_val_perm:.4f} " + ("(Aprovado!)" if p_val_perm < 0.05 else "(Reprovado - Ruído)"))
    
    print("\n3. Calculando Significância Estatística (T-Test)...")
    p_val_t = calculate_p_value_t_test(mock_returns)
    print(f"P-Value (T-Test): {p_val_t:.4f} " + ("(Aprovado - Média positiva real!)" if p_val_t < 0.05 else "(Reprovado - Acaso)"))
    
    print("\n4. Calculando Deflated Sharpe Ratio...")
    # Supondo que fizemos 50 backtests para achar o parâmetro
    trials = 50
    dsr_prob = deflated_sharpe_ratio(sr, trials)
    print(f"Número de Otimizações testadas (Trials): {trials}")
    print(f"Probabilidade Deflated Sharpe: {dsr_prob*100:.1f}% " + ("(Aprovado - Resiste à penalização)" if dsr_prob > 0.95 else "(Overfitting provável)"))
