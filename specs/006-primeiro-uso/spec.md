# 006 — Primeiro uso

- **Prioridade:** P2
- **Status:** Approved
- **Código afetado:** novo `tools/setup_wizard.py`, instalador, README
- **Resolve:** M5

## Contexto

Antes de ligar o robô, o usuário precisa entender se a conta é demo ou real, quanto pode perder por trade e o que esperar.

## Requisitos funcionais

- **FR-1** Na primeira execução, MUST abrir um assistente que testa a conexão com o MT5 e mostra a conta (REAL/DEMO), o saldo, as rotas que cabem no saldo e o risco por trade de cada uma.
- **FR-2** Em conta REAL, o assistente MUST pedir confirmação explícita antes de liberar o modo ao vivo, e MUST recomendar começar em DEMO.
- **FR-3** O assistente SHOULD verificar o botão Algo Trading e os ativos na Observação do Mercado, explicando como corrigir.
- **FR-4** O resultado MUST ficar salvo no `config.toml` (spec 003).

## Critérios de aceite

- **AC-1** Sem o MT5 aberto, o assistente explica o problema e não trava.
- **AC-2** Em conta REAL e sem confirmação, nenhum robô ao vivo inicia.

## Decisões

- —
