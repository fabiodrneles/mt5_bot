# 011 — Monitoramento ao vivo × esperado

- **Prioridade:** P1
- **Status:** Draft
- **Código afetado:** novo `mt5bot/core/live_monitor.py`, `mt5bot/core/telemetry.py`, `mt5bot/execution/quant_manager.py`, `interfaces/dashboard.py`, `tools/quant_runner.py`
- **Resolve:** G9 · R7

## Contexto

Pela hipótese dos mercados adaptativos [Lo 2004], uma vantagem pode sumir. Um robô médio só descobre isso pelo saldo. Um robô acima da média compara **continuamente** o que acontece ao vivo com a distribuição esperada pelo backtest e para a rota quando a diferença deixa de ser explicável por sorte.

## Requisitos funcionais

- **FR-1** Para cada trade fechado de uma rota quant, MUST ser registrado o resultado em R (múltiplos do risco), o *slippage* (spec 008 FR-6) e o resultado que o simulador de referência (spec 010) teria dado nos mesmos candles (**sombra**).
- **FR-2** MUST ser calculado e exibido o **tracking error**: diferença média em R entre o real e a sombra, com o número de trades.
- **FR-3** MUST existir um detector de degradação por **CUSUM** sobre o resultado em R, calibrado com a média e o desvio do OOS da validação (spec 009). Ao cruzar o limiar, a rota entra em `⏸ PAUSADA (degradação)`.
- **FR-4** (D11) Rota pausada não abre posição nova até `bot.bat resume ROTA`. A pausa gera alerta (spec 012).
- **FR-5** O dashboard MUST mostrar por rota: trades ao vivo, expectativa ao vivo × esperada com IC, *tracking error* e estado do CUSUM.
- **FR-6** Com menos de 10 trades ao vivo, os números MUST vir marcados "amostra pequena" (princípio 3).

## Requisitos não funcionais

- **NFR-1** O cálculo é incremental (O(1) por trade).
- **NFR-2** O limiar do CUSUM tem taxa de falso alarme documentada (ARL₀ ≥ 100 trades em dados sem degradação).

## Critérios de aceite

- **AC-1** Dada uma sequência sintética de trades com a mesma distribuição do OOS, então o CUSUM não dispara em 1.000 simulações com frequência acima da ARL₀ documentada.
- **AC-2** Dada uma sequência cuja média cai para −0,5 R, então o CUSUM dispara em até 30 trades em pelo menos 90% das simulações.
- **AC-3** Dada a rota pausada, quando aparece um sinal, então não há ordem e o estado é `⏸ PAUSADA`.
- **AC-4** Dado um trade real com saída 2 *ticks* pior que a sombra, então o *tracking error* reflete a diferença.

## Fora de escopo

- Reotimização automática dos parâmetros (risco de *overfitting* ao vivo).

## Decisões

- D11 — pausar e avisar, com retomada manual.

## Referências

[Page 1954] CUSUM; [Wald 1945] testes sequenciais; [Lo 2004] mercados adaptativos.
