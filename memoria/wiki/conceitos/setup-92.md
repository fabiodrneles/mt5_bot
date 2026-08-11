# Setup 9.2 — Correção rápida

Fonte: `raw/estrategias-operacionais.txt` · Status: em análise (WATCHING_92 no código)

## Regras (COMPRA)
1. **Contexto**: MME9 apontando para cima (tendência de alta ativa).
2. **Correção**: um candle de correção tem sua **mínima abaixo da mínima do candle anterior** (a mínima do candle anterior não é respeitada — o preço "passa" dela).
3. **Entrada**: rompimento da **máxima** do candle de correção.
4. **Stop**: mínima do candle de correção.

## Regras (VENDA) — simétrico
- MME9 apontando para baixo; candle de correção com máxima acima da máxima do anterior.
- Venda no rompimento da mínima do candle de correção. Stop: máxima do candle.

## Ponto-chave
- É um setup de **continuação da tendência** após uma correção rápida.
- A "quebra" da mínima anterior indica que a correção chegou ao fim; o rompimento da máxima confirma a retomada.
- Requer MME9 alinhada — sem isso não é 9.2 válido.

## No código (estado atual)
- `strategy.py`: estado `WATCHING_92` (aguardando condições), `check_setup_92_buy/sell`.
- Gerenciamento: no fluxo atual, após saída lucrativa volta ao 9.1 (mapear em `estado-atual-codigo.md`).

## Observação de trading
- Palex: 9.2/9.3 são ~60% das operações dele — o core da operação.
- Preferir quando a correção é rápida (poucos candles) e rasa.
