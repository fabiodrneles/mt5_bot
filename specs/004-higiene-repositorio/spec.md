# 004 — Higiene do repositório

- **Prioridade:** P0
- **Status:** Done
- **Código afetado:** raiz do repositório, `maestro/`, `run.bat`, `.gitignore`
- **Resolve:** A1, A2, M2, M3

## Estado atual (verificado)

- `run.bat` (`go run main.go worker.go`) → `undefined: ColorAmber`.
- Arquivos versionados que não deveriam estar no git:
  - binários: `maestro/maestro.exe` (6,6 MB), `maestro.exe.bak`, `bin/maestro.exe`, `maestro_supervisor_check.exe`;
  - logs e saídas: `logs/*.log`, `blame.txt`, `build_check.txt`, `dist/*1.0.0*`;
  - rascunhos e dados: `temp/test.go`, `testes/`, `dataset_live_experience.csv`;
  - documentos soltos na raiz (`FINISH.md`, `AI_CONTINUE.md`…);
  - código legado: `mt5bot/legacy_*.py`, `tools/sim_fin*.py`, `refactor_imports.py`, `test_rvol_wins.py`.

## Requisitos funcionais

- **FR-1** O `run.bat` MUST compilar e rodar o Maestro (`go run .`).
- **FR-2** Binários, logs, saídas de build e dumps MUST sair do git (conforme D8) e entrar no `.gitignore`.
- **FR-3** Código legado sem uso MUST ser removido; o que for útil MUST ir para `tools/` com teste ou documentação.
- **FR-4** Documentos soltos na raiz MUST ir para `docs/` (ou ser removidos, se obsoletos), com os links atualizados no README e no `AGENTS.md`.
- **FR-5** Quem clona MUST conseguir gerar o `maestro.exe` com um comando documentado (`go build` ou `bot.bat build`).

## Critérios de aceite

- **AC-1** `git ls-files '*.exe' '*.bak' '*.log'` não retorna nada.
- **AC-2** Num clone limpo, o `run.bat` abre o Maestro.
- **AC-3** A raiz contém só os arquivos de entrada (README, AGENTS, CHANGELOG, configurações de build e scripts `.bat`).

## Fora de escopo

- Reescrever o histórico do git para remover os binários antigos (custoso e destrutivo para quem já clonou).

## Decisões

- D8 — Binários saem do git e são publicados só nas Releases (quem clona compila com `go build`).
