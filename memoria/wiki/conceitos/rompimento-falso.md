# Rompimento Falso (Alan Farley)

Fonte: `raw/estrategias-operacionais.txt` (Rompimento Falso, p.81) · Status: planejado para Fase 2

## Regras (COMPRA)
1. **Perda de suporte**: o preço rompe (para baixo) um nível de suporte importante.
2. **Marca**: marca-se a **máxima do candle que rompeu** (o candle que violou o suporte).
3. **Entrada**: compra **1 centavo (1 tick) acima** da máxima do candle de rompimento.
4. **Stop**: abaixo da **menor mínima** do movimento de rompimento.
5. **Time frame**: melhor desempenho em gráficos **diário e semanal**.

## Regras (VENDA) — simétrico
- Rompimento falso de resistência (para cima); marca a mínima do candle que rompeu; venda 1 tick abaixo; stop acima da maior máxima.

## Ponto-chave
- Captura a **armadilha**: o rompimento que falha volta com força.
- É a "trap" clássica de traders — o mercado quebra um nível, atrai stops/ordens, e reverte.
- Diferente do FFFD: baseia-se em **níveis estruturais** (suporte/resistência), não em bandas de volatilidade.

## No código (planejado)
- `indicators.py`: detecção de rompimento de swing de suporte/resistência (swing highs/lows).
- `strategy.py`: `check_rompimento_falso_buy/sell` na Fase 2.

## Observação de trading
- Palex combina com a estrutura de **slingshots** e o conceito de "falso" no 9.4.
- Importante usar em TF maior (diário/semanal) — o bot opera H1 com multi-TF de contexto.
