MT5Bot — Developer Guide (resumo automatizado)

Objetivo

Este arquivo resume todas as mudancas recentes e explica como o codigo organiza a logica, design decisions e onde procurar
informacao para que uma IA (ou um mantenedor humano) entenda rapidamente o projeto.

Principais pontos (v1.1.0)

- Persistencia
  - Local de armazenamento: `%APPDATA%/mt5bot` (Windows) ou `~/.mt5bot` em outros OS.
  - Funcoes: `persistence.save_states()`, `persistence.load_states()`, `persistence.apply_loaded_states()`.
  - Serializacao: convertendo `numpy` types em primitivos Python; datetimes em ISO strings.
  - Backup: se o arquivo JSON estiver corrompido, o bot faz backup e inicia do zero.

- Tracker
  - Arquivo de historico `trades.json` guarda entradas/saidas.
  - Conversao de tipos antes de `json.dump`
  - Calcula `pnl_money` quando MT5 fornece `trade_tick_value` e `trade_tick_size`.

- Shutdown
  - Flag CLI `--shutdown-action` (save-only|wait-flat|cancel-open)
  - Watcher de console permite `exit`, `exit now`, `exit when flat` enquanto o bot roda.
  - Default seguro: `save-only` (nao cancela ordens automaticamente).

- Tests
  - Testes unitarios em `test_strategy.py` (usa mock do MT5 via `conftest.py`).
  - Rodar: `py -3 -m pytest -q`.

Arquivos chave

- `main.py` — entrada, loop principal, reconexao e shutdown.
- `strategy.py` — maquina de estados: SCANNING, SIGNAL_READY, IN_POSITION, WATCHING_92.
- `indicators.py` — EMA, ATR, adaptive target, checks de pullback/flat.
- `executor.py` — wrapper de chamadas MT5 (place/cancel/close orders).
- `persistence.py` — salvar/carregar estado com conversao para JSON segura.
- `tracker.py` — registrar trades e calcular metricas.
- `tui.py` / `dashboard.py` — interfaces de usuario (terminal/web).

Como contribuir rapidamente

1. Rodar testes: `py -3 -m pytest -q`.
2. Fazer pequenas alteracoes localmente e rodar testes especificos: `py -3 -m pytest test_strategy.py::test_nome_da_funcao -q`.
3. Quando pronto, commitar e push para branch `testes` (forcado se necessario):

```bash
git checkout -B testes
git add -A
git commit -m "docs: atualizar guia do desenvolvedor"
git push origin testes --force
```

Notas finais

Se quiser, eu posso:
- Gerar documentação em formato OpenAPI/JSON-LD para ingestion por outras IAs.
- Gerar um resumo microformal (YAML) listando todos os endpoints, funções publicas e formatos de dados.
- Fazer um `DEVELOPER_GUIDE.html` com links e cross-references.

Diga qual formato prefere e eu gero automaticamente.
