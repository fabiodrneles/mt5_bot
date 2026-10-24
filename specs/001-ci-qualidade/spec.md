# 001 — CI e qualidade

- **Prioridade:** P0
- **Status:** Approved
- **Código afetado:** `.github/workflows/ci.yml`, `pyproject.toml`, `test_rvol_wins.py`, `testes/`, novo `tools/ci.ps1`
- **Resolve:** C1, A7, M1, M4

## Contexto

O CI é a única garantia de que uma mudança não quebrou o robô que opera dinheiro real. Hoje ele falha antes de rodar qualquer teste.

## Estado atual (verificado)

- Run `40057784737`: `test_rvol_wins.py:15` chama `exit()` durante a coleta → `INTERNALERROR`, "no tests ran".
- Venv limpo com `pytest numpy pandas` (o que o CI instala): `ModuleNotFoundError: No module named 'pytz'` em 5 arquivos.
- CI só em `ubuntu-latest`; o produto é Windows.
- Não há lint; `ruff` encontra 53 problemas.

## Requisitos funcionais

- **FR-1** O CI MUST instalar o projeto pelas próprias dependências declaradas (`pip install -e ".[dev]"`).
- **FR-2** O pytest MUST coletar só `tests/` (`testpaths`); scripts soltos MUST sair da raiz ou virar teste real.
- **FR-3** O CI MUST rodar em matriz `windows-latest` + `ubuntu-latest`, com Python 3.10 e 3.13.
- **FR-4** O CI MUST rodar `ruff check` com regras de erro (F, E9) e falhar em achados.
- **FR-5** O CI MUST rodar `go vet`, `go test -race` e `go build` do Maestro para Windows.
- **FR-6** MUST existir um alvo local equivalente ao CI (`tools/ci.ps1`).
- **FR-7** SHOULD medir cobertura do pacote `mt5bot` com um piso que não pode cair.
- **FR-8** O repositório SHOULD ter `CONTRIBUTING.md`, templates de issue e PR e `CODEOWNERS`.

## Requisitos não funcionais

- **NFR-1** O CI completo SHOULD terminar em menos de 10 minutos.

## Critérios de aceite

- **AC-1** Dado um push na `main`, quando o CI roda, então todos os jobs ficam verdes em Windows e Ubuntu.
- **AC-2** Dado um import quebrado num módulo do `mt5bot`, quando o CI roda, então ele falha (teste de importação de todos os módulos).
- **AC-3** Dado um nome indefinido num `.py`, quando o CI roda, então o job de lint falha.
- **AC-4** `tools/ci.ps1` executa os mesmos passos e retorna código ≠ 0 em falha.

## Fora de escopo

- Testes contra um MT5 real no CI (exigiria conta e terminal; o MT5 continua simulado).

## Decisões

- D4 — Merges delegados ao agente em rodadas, sempre com CI verde e na ordem do épico (2026-10-24).
