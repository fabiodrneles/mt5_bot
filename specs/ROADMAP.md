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

## Fase 2 — Confiável (P1) → `v2.14.0` ✅

Entregue em 2026-10-24 (épico #22; PRs #29, #30, #31, #32, #33, #34).

- [x] **T7** O Maestro usa o Python da instalação — 002 FR-4, AC-4
- [x] **T8** Instalador Windows (Inno Setup, Python embutido, atalhos, desinstalador) — 002 FR-2, FR-3, FR-7, AC-2
- [x] **T9** Workflow de release por tag, com smoke e checksums — 002 FR-5, AC-3
- [x] **T10** Workflow de ML seguro — 005 FR-1, AC-1
- [x] **T11** Setups não validados fora do modo ao vivo por padrão — 005 FR-2..3, AC-2/3
- [x] **T12** Guia prático: `CONTRIBUTING.md`, templates, `CODEOWNERS` e `[Unreleased]` no CHANGELOG — 001 FR-8

## Fase 3 — Profissional (P2) → `v3.0.0` ✅

Entregue em 2026-10-24 (épico #36; PRs #42–#46). Extra: manual técnico (T17, #45). Fechamento em `v3.1.0`: pacote Wine verificado no CI (#47, PR #49) e guia técnico completo com figuras e listagens (PR #50).

- [x] **T13** Pacotes Linux e macOS via Wine (experimental) — 002 FR-6
- [x] **T14** Assistente de primeiro uso — 006 FR-1..4, AC-1/2
- [x] **T15** `bot.bat config --edit` — 003 FR-5
- [x] **T16** Cobertura medida com piso — 001 FR-7

## Entre fases — Pesquisa ampla, diário de sinais e rotas em estudo → `v3.2.0` ✅

Entregue em 2026-10-24 (PRs #52–#56): specs 007–018, pesquisa ampla de padrões (guia cap. 14), diário de sinais, modo estudo das rotas quant (US100 D1 e USDJPY H1), setups 9.2/9.3/PC conferidos com o livro e rascunho do artigo. Por isso as Fases 4–6 andaram uma versão.

## Fase 4 — Capital blindado (P0) → `v3.3.0`

Base: [ANALYSIS-v3.1](ANALYSIS-v3.1.md). Antes de codar: decidir D9 e D10.

- [ ] **T18** Travas de risco falham fechadas no Modo Quant — 007 FR-1, AC-1
- [ ] **T19** Kelly recusa $f^* \le 0$ e parâmetros inválidos — 007 FR-2, AC-2/3
- [ ] **T20** Limites semanal, de perdas seguidas e de *drawdown* + kill switch e `bot.bat resume` — 007 FR-3..5, FR-7, AC-4/5/7
- [ ] **T21** Saída parcial desativada quando o lote não divide — 007 FR-6, AC-6
- [ ] **T22** Reconexão automática ao MT5 com espera exponencial — 008 FR-1/2, AC-1
- [ ] **T23** Novas tentativas por *retcode*, idempotência e *slippage* registrado — 008 FR-3, FR-6, FR-7, AC-2/3/6
- [ ] **T24** SL confirmado na corretora após cada abertura — 008 FR-4, AC-4
- [ ] **T25** Filtro de *spread* no Modo Quant — 008 FR-5, AC-5

## Fase 5 — Evidência robusta (P1) → `v3.4.0`

- [ ] **T26** Núcleo `mt5bot/sim` extraído de `research.py`, com `CostModel` e rolagem tripla — 010 FR-1/2/5, AC-1..3
- [ ] **T27** Ferramentas de backtest migradas para o núcleo e teste de paridade — 010 FR-3/4, AC-4/5
- [ ] **T28** `validate.py`: *walk-forward*, DSR, PBO, *bootstrap*, Monte Carlo e veredito — 009 FR-1/2/4, AC-1..3
- [ ] **T29** Revalidação publicada das rotas atuais — 009 FR-3, AC-4
- [ ] **T30** Sombra, *tracking error* e CUSUM com pausa da rota — 011 FR-1..6, AC-1..4

## Fase 6 — Operação supervisionada (P1) → `v3.5.0`

Antes de codar: decidir D12 e D16.

- [ ] **T31** `notify.py` com fila, limite de taxa, eventos e resumo diário — 012 FR-1..4, FR-6/7, AC-1..5
- [ ] **T32** Diário JSONL e `bot.bat journal` / `export` — 013 FR-1..3, FR-5/6, AC-1/3/4
- [ ] **T33** `bot.bat report` em HTML — 013 FR-4, AC-2
- [ ] **T34** Segredos no cofre do Windows (`keyring`) — 014 FR-1/2, AC-1
- [ ] **T35** Lock com hashes, `pip-audit`, `govulncheck`, Dependabot, *actions* por SHA — 014 FR-3..5, FR-7, AC-2/3
- [ ] **T36** SBOM, atestado de proveniência, `SECURITY.md` e assinatura (D16) — 014 FR-6, FR-8/9, AC-4
- [ ] **T37** Cobertura 75/90, testes de propriedade e `mypy` no núcleo — 018 FR-1/2/4, AC-2/4
- [ ] **T38** Mutação semanal, *fuzz* Go, orçamento de desempenho e ponta a ponta — 018 FR-3, FR-5..7, AC-1/3

## Fase 7 — Produto completo (P2) → `v4.0.0`

Antes de codar: decidir D11, D13, D14 e D15.

- [ ] **T39** Risco de carteira agregado com correlação — 015 FR-1..3, AC-1..3
- [ ] **T40** *Pipeline* de novas rotas e volatilidade-alvo opcional — 015 FR-4/5, AC-4
- [ ] **T41** ML com validação purgada, calibração, *model card* e falha visível — 016 FR-1..6, AC-1..4
- [ ] **T42** Configuração editável no dashboard com *token* e confirmação de risco — 017 FR-1..3, AC-1..3
- [ ] **T43** Aviso de nova versão, página de relatórios e modo demonstração — 017 FR-4/5/7, AC-4
- [ ] **T44** Interface completa em pt/en/es — 017 FR-6, AC-5
