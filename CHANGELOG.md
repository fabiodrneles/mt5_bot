# Changelog

## v1.1.0 — 2026-08-10

Principais mudanças:

- Moveu persistencia (`state.json`, `trades.json`) para `%APPDATA%/mt5bot` (Windows) ou `~/.mt5bot` (outros). Evita gravação em site-packages e problemas de permissões/corruptos.
- Implementou conversao segura para JSON em `persistence.save_states()` e `tracker._save_trades()` (converte `numpy` types, `datetime` para strings ISO, arrays para listas).
- Backup automático de arquivos de estado corrompidos: renomeia para `state.json.corrupt.<timestamp>` e inicia do zero (gera warning log).
- Shutdown interativo e seguro:
  - Default: `save-only` (nao cancela ordens/posicoes)
  - `wait-flat`: aguarda posicoes e ordens encerrarem antes de sair (com timeout configuravel)
  - `cancel-open`: cancela ordens pendentes antes de encerrar (uso explicito)
  - CLI flag: `--shutdown-action` e comandos no console (`exit`, `exit now`, `exit when flat`).
- Mensagens de log e rejeicao de sinais foram tornadas mais curtas e profissionais para auditoria automatizada.
- Testes: restauração e estabilização de `test_strategy.py`, adicionada estrategia de mock compartilhado via `conftest.py`. Suíte rodando com `pytest`.
- Bump de versão para `1.1.0` e atualização do tagline para inglês no banner.

Detalhes de implementação e notas de desenvolvedor estão em `DEVELOPER_GUIDE.md`.
