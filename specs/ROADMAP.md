# Roadmap e tarefas

Cada tarefa referencia a spec e os critérios de aceite que ela fecha. Ordem sugerida = ordem da lista.

## Fase 0 — Decisões (antes de codar)

- [x] Responder D1–D8 em [ANALYSIS.md §7](ANALYSIS.md#7-decisões-em-aberto) e mover as specs para `Approved`.

## Fase 1 — Funcionar de verdade (P0) → `v2.13.0` ✅

Entregue em 2026-10-24 (épico #2; PRs #9, #10, #11, #12, #14, #15, #16).

- [x] **T1** CI verde: dependências do projeto, `testpaths`, matriz Windows/Ubuntu × Python 3.10/3.13, `go test -race` — 001 FR-1..3, FR-5, AC-1/2
- [x] **T2** Gate de lint (ruff) e correção dos 53 achados — 001 FR-4, AC-3
- [x] **T3** Alvo local `tools/ci.ps1` — 001 FR-6, AC-4
- [x] **T4** Empacotamento Python: descoberta de pacotes e teste de importação do wheel — 002 FR-1, AC-1
- [x] **T5** `run.bat` funcional, e binários e lixo fora do git — 004 FR-1..5, AC-1..3
- [x] **T6** Pasta de dados do usuário e `config.toml` — 003 FR-1..4, AC-1..3

## Fase 2 — Confiável (P1) → `v2.14.0`

- [ ] **T7** O Maestro usa o Python da instalação — 002 FR-4, AC-4
- [ ] **T8** Instalador Windows (Inno Setup, Python embutido, atalhos, desinstalador) — 002 FR-2, FR-3, FR-7, AC-2
- [ ] **T9** Workflow de release por tag, com smoke e checksums — 002 FR-5, AC-3
- [ ] **T10** Workflow de ML seguro — 005 FR-1, AC-1
- [ ] **T11** Setups não validados fora do modo ao vivo por padrão — 005 FR-2..3, AC-2/3
- [ ] **T12** Guia prático: `CONTRIBUTING.md`, templates, `CODEOWNERS` e `[Unreleased]` no CHANGELOG — 001 FR-8

## Fase 3 — Profissional (P2) → `v3.0.0`

- [ ] **T13** Pacotes Linux e macOS via Wine (experimental) — 002 FR-6
- [ ] **T14** Assistente de primeiro uso — 006 FR-1..4, AC-1/2
- [ ] **T15** `bot.bat config --edit` — 003 FR-5
- [ ] **T16** Cobertura medida com piso — 001 FR-7
