# Processo SDD e qualidade (v2.13.0)

O projeto segue **Spec Driven Development** desde 2026-10-24. A fonte da verdade são `specs/`, com análise, constituição, specs por área e roadmap.

## Fluxo
1. Toda mudança de comportamento tem spec, com FR, NFR e AC (Dado/Quando/Então).
2. Cada fase vira um épico no GitHub, e cada tarefa vira uma sub-issue (ticket).
3. Uma branch por ticket (`<tipo>/<nº>-<descrição>`) e um PR por ticket, começando com `Closes #N · Épico #M · Spec NNN`.
4. Antes do push, roda-se `bot.bat ci` (ruff, pytest, wheel e Maestro). O merge só acontece com o CI verde.
5. O PR de fechamento da fase atualiza o status das specs, o ROADMAP e o CHANGELOG. Quem cria a tag é o dono.

## Gates de qualidade (CI)
- Python em Windows e Ubuntu, nas versões 3.10 e 3.13. O MT5 é simulado no `tests/conftest.py`, e a pasta de dados fica isolada via `MT5BOT_DATA_DIR`.
- `tests/test_imports.py` importa todos os módulos.
- O wheel é instalado num venv limpo, e todos os módulos são importados (`tools/check_wheel.py`).
- `ruff` (E9 + F) e `go vet`, `go test -race` e o build do Maestro para Windows.

## Decisões do dono (D1–D8, 2026-10-24)
- macOS/Linux via Wine (experimental).
- Instalador Windows em Inno Setup, sem assinatura de código.
- Merges delegados ao agente, sempre com CI verde.
- Setups clássicos só em `/study` por padrão.
- Versões seguem em SemVer 2.x.
- Licença MIT; o projeto **não será vendido**, o objetivo é portfólio.
- Binários só nas Releases.

## Fase 1 (v2.13.0)
Entregue com os PRs #9 a #16. A lista completa está no `CHANGELOG.md`. As próximas fases (instalador, release e segurança operacional) estão em `specs/ROADMAP.md`.

## Fase 2 (v2.14.0)
Entregue com os PRs #29 a #34:
- instalador Windows (Inno Setup, Python embutido, `xgboost-cpu`), com cerca de 48 MB;
- smoke test do instalado no CI;
- release automática por tag, com `SHA256SUMS`;
- setups não validados fora do modo ao vivo por padrão;
- treino de ML só sob demanda;
- guia de contribuição.

Para publicar uma versão, o dono cria a tag `vX.Y.Z` igual à versão do `pyproject.toml`; o workflow `Release` faz o resto.
