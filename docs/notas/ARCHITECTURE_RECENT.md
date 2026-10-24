# Mudanças recentes — v1.1.0

Este arquivo resume as mudanças técnicas introduzidas na versão v1.1.0 do MT5Bot.
Útil para leitura por IAs e desenvolvedores que buscam um changelog técnico curto.

Principais alterações

- Persistência
  - `state.json` e `trades.json` passaram a ser gravados em `%APPDATA%/mt5bot` no Windows ou `~/.mt5bot` em outros sistemas.
  - Racional: evita gravar em `site-packages` e problemas de permissão/corruptos após reinstalações.
  - Implementação: `persistence._get_data_dir()` decide o diretório, com fallback para o diretório do pacote se necessário.

- Serialização JSON segura
  - `persistence.save_states()` e `tracker._save_trades()` agora convertem tipos não-serializáveis (ex: `numpy.int64`, `numpy.ndarray`, `datetime`) para tipos nativos antes de chamar `json.dump`.
  - Isso evita `TypeError: int64 not JSON serializable` e problemas similares.

- Backup de arquivo corrompido
  - Ao detectar JSON inválido em `state.json`, o bot renomeia o arquivo para `state.json.corrupt.<timestamp>` e inicia do zero, emitindo warnings para revisão manual.

- Shutdown seguro e interativo
  - Comportamento padrão: `save-only` (não cancela ordens/posições ao encerrar).
  - Opções: `wait-flat` (aguarda posições/ordens encerrarem até timeout configurado) e `cancel-open` (cancela ordens pendentes antes de encerrar).
  - CLI flag: `--shutdown-action` para definir o comportamento ao iniciar.
  - Console watcher: enquanto o bot roda, é possível digitar `exit`, `exit now`, `exit when flat` no terminal para acionar o shutdown com a ação desejada.

- Estratégia e logs
  - Mensagens de rejeição e logs foram padronizados para serem curtas e profissionais, facilitando análise automatizada.
  - `strategty._place_entry_order()` reseta `partial_exit_done` ao colocar nova ordem (fix para flag persistente).

- Testes
  - `test_strategy.py` foi restaurado e estabilizado; testes usam mock compartilhado do `MetaTrader5` via `conftest.py` para garantir isolamento.
  - Comando de execução: `py -3 -m pytest -q`.

Objetivo

Tornar o repositório robusto para ingestão por IAs, reduzir erros operacionais em ambiente real, e facilitar auditoria e manutenção.

Onde procurar

- Implementação persistência: `persistence.py`
- Serialização segura e backup: `persistence.py` e `tracker.py`
- Shutdown e watcher console: `main.py`
- Testes: `test_strategy.py`, `conftest.py`
- Changelog e guia para desenvolvedores: `CHANGELOG.md`, `DEVELOPER_GUIDE.md`
