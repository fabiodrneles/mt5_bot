# 010 — Simulador único de referência

- **Prioridade:** P1
- **Status:** Draft
- **Código afetado:** `tools/quant_research/research.py`, novo `mt5bot/sim/` (núcleo), `tools/backtest.py`, `tools/backtest_wfo.py`, `tools/vectorized_backtester.py`, `mt5bot/mentorship/simulator.py`
- **Resolve:** G7, G8 · R6

## Contexto

O guia (cap. 12 §12.5) reconhece quatro simuladores com regras de custo diferentes. Isso permite que uma estratégia pareça boa num e ruim no outro. A solução é um **núcleo único** e testado, com os outros virando adaptadores finos.

## Estado atual (verificado)

- `research.py:simulate` é a referência (spread por candle, comissão, *swap*, SL antes de TP no mesmo candle).
- `research.py:90 swap_usd` multiplica o *swap* por noites de calendário; a rolagem tripla (quarta-feira na maioria dos índices) é ignorada.
- `tools/backtest.py`, `backtest_wfo.py` e `vectorized_backtester.py` têm custos próprios ou nenhum.

## Requisitos funcionais

- **FR-1** MUST existir `mt5bot/sim/engine.py` com uma função `simulate(candles, signals, costs, rules) -> trades`, sem MT5 e sem estado global, extraída de `research.py`.
- **FR-2** Os custos MUST vir de um objeto `CostModel` com *spread* por candle, comissão por lado, *swap* com **dia de rolagem tripla do símbolo** (`swap_rollover3days` do MT5, salvo nos metadados) e *slippage* configurável.
- **FR-3** `research.py`, `backtest.py`, `backtest_wfo.py` e `mentorship/simulator.py` MUST usar o núcleo. `vectorized_backtester.py` MAY ser removido se não tiver uso.
- **FR-4** MUST existir um teste de **paridade** que roda o núcleo e o caminho de produção (`quant_setups.evaluate` + `quant_manager`) vela a vela sobre o mesmo histórico e exige 0 divergências de sinal (generaliza o cap. 8 §8.8 para toda rota).
- **FR-5** Regras ambíguas MUST ser explícitas e testadas: SL antes de TP no mesmo candle, *gap* além do SL executa no preço de abertura, entrada no candle seguinte.

## Critérios de aceite

- **AC-1** Dado um trade comprado aberto de terça a quinta num símbolo com rolagem tripla na quarta, então o *swap* cobrado é de 4 noites, não 2.
- **AC-2** Dado um candle que toca SL e TP, então o trade sai no SL.
- **AC-3** Dado um *gap* de abertura abaixo do SL de uma compra, então a saída é no preço de abertura, não no SL.
- **AC-4** Os resultados das rotas atuais no núcleo novo diferem no máximo 1% (só pelo *swap* corrigido) dos publicados no guia; a diferença é documentada.
- **AC-5** O teste de paridade passa para PULLB e RSI2MR.

## Fora de escopo

- Simulação tick a tick.

## Decisões

- —
