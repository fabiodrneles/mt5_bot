# Joe DiNapoli — 2º fundo acima + média deslocada

Fonte: `raw/estrategias-operacionais.txt` (Joe DiNapolli) · Status: planejado para Fase 2

## Regras (COMPRA)
1. **2º fundo**: o preço forma um fundo (mínima), corrige, e forma um **segundo fundo**.
2. **Critério**: o 2º fundo precisa ficar **acima** do 1º fundo — OU a mínima do 2º fundo pode violar o 1º fundo, desde que o **fechamento** do candle do 2º fundo fique acima da mínima do 1º fundo.
3. **Média deslocada**: o **fechamento** do candle do 2º fundo deve ficar **acima da média deslocada** (média móvel deslocada para trás).
4. **Marca**: marca-se a **máxima do candle do 2º fundo** (o candle de sinal).
5. **Entrada**: compra **1 centavo (1 tick) acima** da máxima marcada.
6. **Stop**: abaixo da **mínima do candle de sinal** (2º fundo).

## Regras (VENDA) — simétrico
- 2º topo abaixo do 1º; fechamento abaixo da média deslocada; venda 1 tick abaixo da mínima marcada; stop acima da máxima do sinal.

## Ponto-chave
- O método de Joe DiNapoli (Displaced Moving Average) usa **média deslocada** (não a MME9).
- O "fechamento acima" é critério rígido — fechar abaixo invalida.
- É um setup de **reversão estrutural** com confirmação por média.

## No código (planejado)
- `indicators.py`: média deslocada (shift para trás); detecção de 2º fundo/topo.
- `strategy.py`: `check_dinapolli_buy/sell` na Fase 2.

## Observação de trading
- Requer leitura estrutural de **fundos/topos** — mais subjetivo que os setups MME9; validar em multi-TF.
