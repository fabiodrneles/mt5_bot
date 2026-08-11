# Gestão de Risco — Regras de Ouro

Fonte: `raw/fundamentos.txt` + `risk_calculator.py` · Status: implementado no código

## Regras fundamentais
1. **Risco máximo por operação: 1% do capital** (padrão Palex). Nunca 2%+ em uma única operação.
2. **Breakeven**: mover o stop para o preço de entrada quando a operação atinge um lucro inicial (protege o capital).
3. **Saída parcial**: realizar parte do lucro (ex: 50% no 1º alvo) e deixar o resto correr — reduz o risco e garante ganho.
4. **Trailing stop**: acompanhar o preço quando o movimento confirma — captura tendências.
5. **Alvo vs stop**: relação mínima de **1:1** (RRR ≥ 1); o bot exige `MIN_RISK_REWARD` no scoring (Fase 2).

## No código (estado atual)
- `risk_calculator.py`: cálculo de risco por trade (1% do capital).
- `config.py`:
  - `PARTIAL_EXIT`: saída parcial de 50% com ganho de 1.00 (1x risco).
  - `FLAT_TICKS`: retorno ao flat após 5 ticks de pullback.
  - `ADAPTIVE_TARGET`: alvo adaptativo com lookback de 20.
  - `ATR_PERIOD=14`, `ATR_MULTIPLIER=50` — stop dinâmico por ATR.
- `executor.py`: execução das ordens (tamanho, stop, alvo).

## Regra de ouro (Palex)
> **"Proteja o capital primeiro. O lucro é consequência."**

## Observação
- Saída parcial + breakeven = proteção; trailing = captura de tendência; a combinação é o gerenciamento profissional.
- `MIN_RISK_REWARD` garante que só operações com RRR ≥ 1 entram (evita operações ruins mesmo com sinal válido).
