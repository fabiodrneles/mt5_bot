# 013 — Diário de decisões, auditoria e relatórios

- **Prioridade:** P1
- **Status:** Draft
- **Código afetado:** novo `mt5bot/core/journal.py`, `mt5bot/execution/quant_manager.py`, `mt5bot/execution/execution_manager.py`, `mt5bot/core/telemetry.py`, `bot.bat`, `interfaces/dashboard.py`
- **Resolve:** G22 · R9

## Contexto

Para entender o robô, estudar o projeto academicamente ou justificar uma decisão, é preciso responder "por que ele entrou aqui?" e "por que **não** entrou ali?". Hoje a resposta está espalhada em texto livre no log rotativo, que se perde com a rotação.

## Requisitos funcionais

- **FR-1** Toda decisão de uma rota a cada candle fechado MUST gerar um registro estruturado (JSON Lines em `<dados>/journal/AAAA-MM.jsonl`): horário UTC, rota, candle, sinal (sim/não), valores dos indicadores usados, resultado de cada trava (risco, spread, margem, kill switch, pausa) e a ação (ordem, recusa com motivo, nada).
- **FR-2** Execuções MUST registrar preço pedido, executado, *slippage*, *ticket*, SL/TP confirmados (008) e, ao fechar, resultado em $ (com comissão e *swap* do MT5) e em R.
- **FR-3** `bot.bat journal [ROTA] [--dias N]` MUST mostrar um resumo legível, sem o usuário abrir o arquivo.
- **FR-4** `bot.bat report [--mes AAAA-MM]` MUST gerar um relatório HTML autocontido (sem CDN) com curva de patrimônio, *drawdown*, resultado por rota e por mês, distribuição em R, motivos de recusa e comparação ao vivo × esperado (011).
- **FR-5** `bot.bat export` MUST exportar trades e diário em CSV para planilha ou estudo.
- **FR-6** O diário MUST ser só anexado (nunca reescrito) e ter retenção configurável (padrão: 24 meses).

## Requisitos não funcionais

- **NFR-1** Gravar o diário custa menos de 1 ms por decisão; o arquivo de um ano de duas rotas fica abaixo de 20 MB.
- **NFR-2** O relatório abre offline e pesa menos de 2 MB.

## Critérios de aceite

- **AC-1** Dado um sinal recusado por *spread*, então o diário tem um registro com `action = "reject"` e `reason = "spread"` com o valor medido e o limite.
- **AC-2** Dado um mês com 3 trades de demonstração, `bot.bat report` gera um HTML cujos totais batem com `telemetry.trade_stats`.
- **AC-3** O CSV exportado tem cabeçalho estável (testado) e abre no Excel em pt-BR (separador `;`, decimal `,` como opção).
- **AC-4** Uma linha corrompida no diário não impede a leitura das outras.

## Fora de escopo

- Banco de dados (SQLite pode vir depois; JSONL basta e é legível).

## Decisões

- —
