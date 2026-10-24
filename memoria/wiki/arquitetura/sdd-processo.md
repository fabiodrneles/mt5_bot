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

## Fases 4–7 (especificadas em 2026-10-24, após a v3.1.0)
`specs/ANALYSIS-v3.1.md` compara o projeto com um padrão "acima da média" (R1–R14) e lista as lacunas G1–G22 verificadas no código. As críticas: a trava diária do Modo Quant libera a entrada se der erro (`quant_manager.py:163`), o Kelly arrisca 0,5% com f* ≤ 0, não há reconexão ao MT5 e ninguém confere o SL depois da ordem.
- Fase 4 `v3.2.0` (capital blindado): specs 007 (travas que falham fechadas, Kelly, limites semanal/sequência/drawdown, kill switch) e 008 (reconexão, retcodes, SL confirmado, spread no Quant).
- Fase 5 `v3.3.0` (evidência): 009 (walk-forward, DSR, PBO, bootstrap, Monte Carlo, veredito), 010 (simulador único, rolagem tripla do swap, paridade) e 011 (sombra, tracking error, CUSUM com pausa da rota).
- Fase 6 `v3.4.0` (operação): 012 (notificações), 013 (diário JSONL e relatórios), 014 (keyring, lock com hashes, pip-audit, SBOM, assinatura) e 018 (mutação, propriedade, mypy, orçamento de desempenho).
- Fase 7 `v4.0.0` (produto): 015 (risco de carteira), 016 (ML sem vazamento) e 017 (configuração no dashboard, aviso de versão, i18n).
Decisões em aberto: D9–D16 (ANALYSIS-v3.1 §6). Tarefas T18–T44 no `specs/ROADMAP.md`.
