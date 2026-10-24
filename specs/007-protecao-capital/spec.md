# 007 — Proteção de capital à prova de falhas

- **Prioridade:** P0
- **Status:** Draft
- **Código afetado:** `mt5bot/risk/risk_calculator.py`, `mt5bot/execution/quant_manager.py`, `mt5bot/execution/execution_manager.py`, `mt5bot/core/config.py`, `mt5bot/core/user_config.py`, `mt5bot/core/telemetry.py`
- **Resolve:** G1, G2, G10, G17 ([ANALYSIS-v3.1](../ANALYSIS-v3.1.md)) · R1, R2, R3

## Contexto

O princípio 1 da constituição ("capital primeiro") vale para o caminho feliz. Nos caminhos de erro, algumas travas deixam a ordem passar. Um robô acima da média trata **toda incerteza como "não opere"** e tem mais de uma camada de limite de perda.

## Estado atual (verificado)

- `quant_manager.py:155-164`: se `calculate_risk_limits()` ou `get_daily_pnl()` lançar exceção, o código só registra um aviso e **segue para a ordem**.
- `risk_calculator.py:52-59`: com probabilidade inválida, devolve `MAX_RISK_PER_TRADE_PERCENT` (1%); com $f^* \le 0$, o *clamp* devolve 0,5%.
- Só existe o limite **diário** (`MAX_DAILY_LOSS_PERCENT = 2.0`). Não há limite semanal, por sequência de perdas nem por *drawdown* desde o pico.
- `PARTIAL_EXIT_PERCENT = 0.50` com lote mínimo 0,01: metade de 0,01 arredonda para baixo do mínimo e a saída parcial nunca acontece, sem aviso.

## Requisitos funcionais

- **FR-1** Toda verificação de risco antes de uma ordem MUST falhar **fechada**: exceção, `None` ou dado faltando = sinal recusado, com estado `🔴 RISCO INDISPONÍVEL` e log `ERROR`.
- **FR-2** (D9) O dimensionamento por Kelly MUST recusar o trade quando $f^* \le 0$ ou quando os parâmetros forem inválidos. O piso de 0,5% passa a valer só para $f^* > 0$.
- **FR-3** (D10) MUST existir, além do diário: perda máxima **semanal** (`max_weekly_loss_pct`, padrão 5), **perdas seguidas** (`max_consecutive_losses`, padrão 4) e **drawdown desde o pico** do patrimônio (`max_drawdown_pct`, padrão 15). Todos configuráveis no `config.toml`, com validação de faixa.
- **FR-4** Atingir um limite semanal, de sequência ou de *drawdown* MUST ligar um **kill switch** persistente (`<dados>/kill_switch.json`) com motivo e horário. Ele bloqueia novas entradas em todas as rotas até o usuário rodar `bot.bat resume`. Posições abertas mantêm SL/TP.
- **FR-5** O estado do kill switch MUST aparecer no painel quant, no Maestro e no dashboard (fonte única: `telemetry`).
- **FR-6** A saída parcial MUST ser desativada automaticamente quando o volume não permitir dividir em dois lotes válidos, com um aviso único no log por posição.
- **FR-7** O pico de patrimônio MUST ser lido do histórico do MT5 (stateless) ou de `<dados>/state.json`, nunca reiniciado só por reabrir o programa.

## Requisitos não funcionais

- **NFR-1** Nenhuma chamada nova ao MT5 por ciclo além de uma consulta ao histórico do dia/semana, com cache de 60 s.
- **NFR-2** As mensagens dizem o limite, o valor atual e como retomar.

## Critérios de aceite

- **AC-1** Dado `tracker.get_daily_pnl` lançando exceção, quando aparece um sinal PULLB, então nenhuma ordem é enviada e o estado é `🔴 RISCO INDISPONÍVEL`.
- **AC-2** Dado `prob_win = 0.30` e `rrr = 1.5` ($f^* < 0$), quando o tamanho é calculado, então o resultado é "recusar" (0 ou `None`), não 0,5%.
- **AC-3** Dado `prob_win = 1.2`, quando o tamanho é calculado, então o trade é recusado.
- **AC-4** Dadas 4 perdas seguidas no histórico, quando aparece um sinal, então o kill switch liga com o motivo "4 perdas seguidas" e a ordem não sai.
- **AC-5** Dado o kill switch ligado, quando o programa reinicia, então ele continua ligado; depois de `bot.bat resume`, as entradas voltam.
- **AC-6** Dado lote 0,01 e mínimo 0,01, quando o alvo da saída parcial é atingido, então nenhuma ordem parcial é enviada e há um único aviso no log.
- **AC-7** Dado `max_weekly_loss_pct = 500` no `config.toml`, então o valor é recusado com mensagem que cita arquivo e chave, e o padrão é usado.

## Fora de escopo

- Risco agregado entre rotas (spec 015).
- Fechar posições abertas ao ligar o kill switch (já existe `DAILY_MAX_LOSS_CLOSE_ENABLED` para o diário).

## Decisões

- D9, D10 — ver [ANALYSIS-v3.1 §6](../ANALYSIS-v3.1.md#6-decisões-em-aberto).

## Referências

[Thorp 2006; MacLean, Thorp & Ziemba 2011] Kelly e frações; [Vince 1990] risco de ruína (guia cap. 6).
