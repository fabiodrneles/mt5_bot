AI Handoff — Como retomar trabalho se esta IA parar de responder

Objetivo

Este arquivo contém passos claros, comandos e um TODO priorizado para que outra IA (ou humano) possa retomar o trabalho no repositório `mt5_bot-main` sem perda de contexto.

Passos iniciais mínimos

1. Abrir o workspace em `c:\Users\Gamer\mt5_bot-main`.
2. Garantir Python 3.10+ instalado. Recomendado usar o mesmo interpretador usado localmente.
3. Instalar dependências de dev:

```powershell
py -3 -m pip install -U pytest coverage
```

4. Rodar os testes:

```powershell
py -3 -m pytest -q
```

5. Se precisar executar testes que manipulam `%APPDATA%`, use `monkeypatch.setenv('APPDATA', '<path>')` nos testes (exemplo em `test_persistence.py`).

Arquivos importantes

- `README.md` — guia de usuário e comandos principais.
- `ARCHITECTURE.md` — documentação técnica completa.
- `ARCHITECTURE_RECENT.md` — mudanças recentes v1.1.0 (resumo técnico).
- `DEVELOPER_GUIDE.md` — guia curto para desenvolvedores/IA.
- `CHANGELOG.md` — changelog v1.1.0.
- `persistence.py`, `tracker.py`, `strategy.py`, `main.py` — código central.
- `test_strategy.py`, `test_shutdown.py`, `test_persistence.py`, `test_main_cli.py` — testes existentes.

Comandos git úteis

```powershell
# Criar branch de trabalho
git checkout -B testes

# Commitar alterações locais
git add -A
git commit -m "mensagem curta" 

go to push (force if you want to replace remote):

git push origin testes --force
```

TODO priorizado (próxima IA/humano)

1. Adicionar testes de persistência e recuperação corrompida (feito: `test_persistence.py`).
2. Adicionar testes do `tracker` (serialização e cálculo PnL).
3. Adicionar teste CLI para `--shutdown-action` e `wait-flat` timeout.
4. Configurar CI (GitHub Actions) para rodar `pytest` e lint (pre-commit).
5. Gerar coverage e mirar >95% (usar `coverage run -m pytest` + `coverage html`).
6. Expandir `README.md` com exemplos por comando e cenários.
7. Publicar release v1.1.0 (tag + criar release no GitHub).

Notas de contexto rápido

- Persistência: arquivos movidos para `%APPDATA%/mt5bot` (Windows) para evitar gravação em site-packages.
- Tests: mocks do MetaTrader5 são fornecidos em `test_strategy.py`/`conftest.py` para isolar a suíte.
- Shutdown: padrão `save-only` para segurança; CLI `--shutdown-action` override disponível.

Se precisar de ajuda adicional, o histórico de ações do Copilot/IA está salvo localmente no workspace (logs/commits e arquivos modificados). Boa continuação.
