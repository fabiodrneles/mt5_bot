# 005 — Segurança operacional

- **Prioridade:** P1
- **Status:** Done
- **Código afetado:** `.github/workflows/ml_training.yml`, `mt5bot/core/config.py`, `mt5bot/execution/execution_manager.py`, `maestro/`
- **Resolve:** A3, A4

## Estado atual (verificado)

- O `ml_training.yml:21` dispara com `contains(message, 'ML')`, o que inclui "HTML", "XML" e "YAML", e faz `git push` na `main` com `contents: write`.
- O `ASSET_SETUPS["default"]` liga 11 setups clássicos no modo ao vivo. O histórico real deles é de 7 trades e −$33,18.

## Requisitos funcionais

- **FR-1** O treino de ML MUST rodar só por `workflow_dispatch` e publicar os modelos como artefato ou PR, nunca com push direto na `main`.
- **FR-2** (conforme D5) Setups sem validação fora da amostra MUST operar ao vivo só com uma opção explícita (`ALLOW_UNVALIDATED_LIVE = true` no `config.toml`). Por padrão, o `/add` com setup clássico MUST recusar e sugerir o `/study`.
- **FR-3** O Maestro MUST mostrar no cartão do robô se a estratégia é **validada** ou **experimental**.

## Critérios de aceite

- **AC-1** Um commit com "HTML" na mensagem não dispara o workflow de ML.
- **AC-2** Dado o padrão, quando o usuário faz `/add EURUSD H1` (sem rota quant), então o robô não envia ordem, e o log explica como simular ou liberar.
- **AC-3** Com `ALLOW_UNVALIDATED_LIVE = true`, o comportamento atual é mantido.

## Decisões

- D5 — Setups clássicos só em `/study` por padrão; ao vivo apenas com opção explícita.
