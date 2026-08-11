# Memória Permanente — MT5Bot Palex

> Base de conhecimento persistente do projeto MT5Bot + livros de Alexandre Fernandes (Palex).
> Estrutura: `raw/` (fontes imutáveis) + `wiki/` (conhecimento destilado) + `scripts/` (RAG BM25).
> Consultar via: `python memoria/scripts/query_memory.py "sua pergunta"`

## Índice de páginas

### Conceitos — Setups (livro: Estratégias Operacionais)
- `conceitos/setup-91.md` — Inversão da MME9 (Larry Williams)
- `conceitos/setup-92.md` — Correção rápida
- `conceitos/setup-93.md` — Recuo profundo (2 fechamentos)
- `conceitos/setup-94.md` — Falso recuo (1 candle contra)
- `conceitos/ponto-continuo.md` — MM21 como âncora
- `conceitos/fffd.md` — Bollinger Fechou Fora/Fechou Dentro
- `conceitos/joe-dinapolli.md` — 2º fundo acima + média deslocada
- `conceitos/rompimento-falso.md` — Alan Farley
- `conceitos/ifr2.md` — IFR(2) extremos + MME50
- `conceitos/sar-parabolico.md` — SAR + IFR(14) + MM13
- `conceitos/mm21-setups.md` — MM21 retorno/fura-teto/cruzamento, MM200, alinhamento

### Conceitos — Fundamentos
- `conceitos/expectativa-matematica.md` — Pay Off, Expectância, regra de ouro
- `conceitos/plano-de-trade.md` — Sistematização >90% falham
- `conceitos/gestao-de-risco.md` — 1%, breakeven, saída parcial, trailing

### Arquitetura
- `arquitetura/maestro-golang.md` — Supervisor (fora do caminho da ordem)
- `arquitetura/cebro-python.md` — Motor multi-setup, hydration, scoring
- `arquitetura/fases.md` — Fase 1 Infra / Fase 2 Multi-Setup / Fase 3 Maestro
- `arquitetura/estado-atual-codigo.md` — O que já existe no strategy.py/indicators.py/config.py

### Fontes
- `fontes/estrategias-operacionais.md` — Resumo + stats do livro de estratégias
- `fontes/fundamentos.md` — Resumo do livro de fundamentos
- `fontes/aprofundamento.md` — Decisões da conversa (RAG de arquitetura)

## Como atualizar
1. Novas fontes → `memoria/raw/` (imutável, nunca editar).
2. Novo conhecimento → criar/atualizar página em `wiki/`.
3. Reindexar: `python memoria/scripts/build_memory.py`
