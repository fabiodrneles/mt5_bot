# Setup 9.1 — Inversão da MME9 (Larry Williams)

Fonte: `raw/estrategias-operacionais.txt` · Status: já implementado no código (`strategy.py`, `indicators.py`)

## Regras (COMPRA)
1. **Condição**: a MME9 (exponencial de período 9) precisa "virar" para cima — um candle fecha acima do valor anterior da MME9 (cruzamento do preço sobre a MME9).
2. **Sinal**: o candle que fez a MME9 virar para cima é o "candle de virada".
3. **Entrada**: compra na máxima do candle de virada + 1 tick.
4. **Stop**: 1 tick abaixo da mínima do candle de virada.
5. **Cancelamento**: se a MME9 voltar a virar para baixo antes do acionamento, o setup é cancelado. NÃO há limite de candles para o acionamento.

## Regras (VENDA) — simétrico
- MME9 vira para baixo (candle fecha abaixo do valor anterior da MME9).
- Venda na mínima do candle de virada − 1 tick. Stop: 1 tick acima da máxima.

## Ponto-chave (dito pelo Palex)
- Setup de **reversão**, mas a entrada só é confirmada com o **rompimento** da máxima/mínima do candle de virada.
- Não antecipar: esperar o preço romper o candle de virada.
- Aplicável em **qualquer time frame** (o Palex usa gráficos diários; o bot opera H1 com multi-TF).

## No código (estado atual)
- `indicators.py`: `get_ema9`, `slopes`, `virou` (detecção de virada da MME9).
- `strategy.py`: `check_setup_91_buy/sell` — entrada por rompimento da máxima/mínima do candle de virada.
- `SymbolState.setup_type = "9.1"`.

## Observação de trading
- Palex: 9.1 é o setup que ele menos usa hoje (~10% das operações), mas é o mais "puro".
- Não usar contra a tendência maior (filtrar por MM200/MM50 — ver `fases.md`).
