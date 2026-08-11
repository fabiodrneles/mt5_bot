# IFR2 — IFR(2) extremos + MME50

Fonte: `raw/estrategias-operacionais.txt` (IFR2, p.72) · Status: planejado para Fase 2

## Regras (COMPRA)
1. **IFR(2)** atinge **≤ 5** (extremo de sobrevenda no IFR de período 2).
2. **MME50** apontando **para cima** (tendência maior a favor).
3. **Preços** do candle **acima** da MME50.
4. **Entrada**: rompimento da **máxima do candle** que fez o IFR(2) furar a **MM13/MM28** (médias de referência do Palex).
5. **Stop**: mínima do candle de sinal.
6. **Alvo**: **50% a 2%** do movimento diário (pequena captura).

## Regras (VENDA) — simétrico
- IFR(2) ≥ 95; MME50 para baixo; preços abaixo da MME50; venda no rompimento da mínima do candle que furou a MM13/MM28; stop na máxima; alvo 2%.

## Ponto-chave
- IFR(2) é **extremamente sensível** — detecta exaustão rápida, mas gera muitos sinais (filtro obrigatório: MME50 + posição vs MM13/28).
- O IFR(2) nunca fica no meio: ou comprado ou vendido demais.
- Alvo curto: **50% da amplitude diária** ou 2% — o Palex usa isso como "pegada" rápida.
- Usa médias **MM13 e MM28** como referência (diferente da MME9 dos setups 9.x).

## No código (planejado)
- `indicators.py`: IFR período 2 (RSI 2), MME50, MM13, MM28.
- `strategy.py`: `check_ifr2_buy/sell` na Fase 2.

## Observação de trading
- "Quanto menor o período do IFR, mais extremo é o valor" — 5 e 95 são níveis fortes.
- Só opera a favor da MME50 — nunca contra.
