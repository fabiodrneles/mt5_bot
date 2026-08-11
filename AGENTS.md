# AGENTS.md — Ponto de Entrada para IA no MT5Bot

> **Leia este arquivo primeiro.** Este é o mapa que permite a qualquer IA (ou humano) entender o projeto inteiro em minutos, incluindo a **memória permanente RAG** que o projeto mantém.

## TL;DR — O que é este projeto

Bot de trading automatizado para **MetaTrader 5** em Python, baseado nos **Setups da família 9.x e do Ponto Contínuo**. Opera H1 com disciplina total, risco de 1% por operação, e uma arquitetura planejada de **maestro Go + cérebro Python**.

**O projeto tem UMA fonte extra de conhecimento: `memoria/`** — uma base de conhecimento permanente (RAG BM25) construída a partir dos livros-fonte da estratégia e das decisões de arquitetura. **Qualquer IA deve consultá-la antes de responder/perguntar sobre o projeto.**

---

## 1. Estrutura do repositório

```
mt5_bot-main/
├── AGENTS.md                # ← VOCÊ ESTÁ AQUI (leia primeiro)
├── memoria/                 # ← MEMÓRIA PERMANENTE + RAG (leia o README interno)
│   ├── README.md            #    explica o RAG, como consultar e atualizar
│   ├── raw/                 #    fontes imutáveis (livros extraídos, spec, aprofundamento)
│   ├── wiki/                #    conhecimento destilado pela IA (13+ páginas)
│   ├── index/               #    índice BM25 gerado (não editar)
│   └── scripts/             #    build_memory.py + query_memory.py
├── main.py                  # Ponto de entrada + loop principal
├── strategy.py              # FSM do bot: SCANNING → SIGNAL_READY → IN_POSITION → WATCHING_92
├── indicators.py            # EMA9/21, ATR, alvo adaptativo, pullback, setups 9.1/9.3
├── config.py                # Parâmetros centralizados
├── executor.py              # Ordens MT5
├── risk_calculator.py       # Lote dinâmico (1% do saldo), risk shield
├── persistence.py           # Estado persistente em %APPDATA%/mt5bot
├── tracker.py               # Histórico + métricas de performance
├── logger.py                # Logs rotativos
├── tui.py / dashboard.py    # Interfaces (terminal/navegador)
├── docs/superpowers/specs/  # Specs de design
└── testes: test_*.py         # Suíte pytest (mock do MT5)
```

---

## 2. Como entender o projeto (ordem recomendada para IA)

1. **`memoria/README.md`** — entenda o sistema de memória/RAG e como consultá-lo. Ele resume o projeto inteiro.
2. **`memoria/wiki/`** — conhecimento destilado: setups 9.1–9.4, Ponto Contínuo, FFFD, DiNapoli, IFR2, SAR, expectativa matemática, plano de trade, gestão de risco, arquitetura (maestro Go + cérebro Python).
3. **`README.md`** — visão do usuário: instalação, comandos, funcionalidades.
4. **`ARCHITECTURE.md`** — documentação técnica completa.
5. **`docs/superpowers/specs/2026-08-11-mt5-multi-setup-maestro-design.md`** — spec do motor multi-setup e do maestro Go (Fase 2/3).
6. **`strategy.py` + `indicators.py` + `config.py`** — o coração do código.
7. **`ROADMAP_IMPROVEMENTS.md`** — fases do projeto e status.
8. **`CHANGELOG.md`** — histórico de versões.

---

## 3. MEMÓRIA PERMANENTE + RAG (`memoria/`) — O QUE VOCÊ PRECISA SABER

Este projeto mantém uma **base de conhecimento permanente** consultável via RAG lexical (BM25). O objetivo: a IA não depende do limite de contexto para lembrar do projeto — ela consulta o RAG.

### Como consultar (sempre que precisar de contexto do projeto)

```powershell
python memoria\scripts\query_memory.py "regras do setup 9.4 falso recuo" -k 3
python memoria\scripts\query_memory.py "expectativa matemática pay off" --kind wiki
python memoria\scripts\query_memory.py "saída parcial breakeven" --text
```

- `-k N`: número de resultados.
- `--kind wiki`: só conhecimento destilado (melhor para respostas rápidas e corretas).
- `--kind raw`: só fontes brutas (livros, spec, aprofundamento).
- `--text`: mostra o bloco inteiro (sem truncar).

### Detalhes técnicos
- **Motor**: BM25 (rank_bm25 equivalente, implementado em stdlib puro — sem dependências).
- **Por que BM25 e não embeddings**: hardware limitado (i3 4ª geração, 4GB RAM). BM25 lexical supera MiniLM embeddings em RAG de baixa RAM e não precisa instalar nada.
- **Índice**: `memoria/index/memoria_index.json` (1.824 chunks, ~25k termos). Reconstrução automática se faltar.
- **Reconstruir manualmente**: `python memoria\scripts\build_memory.py`.

### Quando atualizar a memória
- Sempre que o projeto ganhar **conhecimento novo** (novo setup entendido, decisão de arquitetura, mudança de código relevante): **editar/gerar página em `memoria/wiki/`** e reindexar.
- Nunca editar `memoria/raw/` (fontes imutáveis).
- Detalhes completos em **`memoria/README.md`**.

---

## 4. O BOT EM 60 SEGUNDOS

### Setups implementados
| Setup | Nome | Status |
|---|---|---|
| 9.1 | Inversão da MME9 (Larry Williams) | ✅ implementado |
| 9.2 | Correção rápida | ✅ implementado (`brain/setups.py`) |
| 9.3 | Recuo profundo (2 fechamentos) | ✅ implementado |
| 9.4 | Falso recuo | 🔲 Fase 2 |
| PC | Ponto Contínuo (MM21) | 🔲 Fase 2 |
| FFFD | Bollinger fora/dentro | 🔲 Fase 2 |
| +4 | DiNapoli, Rompimento Falso, IFR2, SAR | 🔲 Fase 2 |

### Proteção de capital (implementado)
- Lote dinâmico: **1% do saldo** por operação (`risk_calculator.py`).
- **Risk Shield**: rejeita operação se o risco do lote mínimo exceder 1.5% do saldo.
- **Daily Max Loss**: trava de 2% de perda diária.
- **Max Spread**: aborta ordem se spread > 50 pontos.
- **Breakeven automático** a 1x ATR.
- **Saída parcial**: 50% no alvo; restante até EMA9 virar.
- **Alvo adaptativo** (mediana de 20 candles) + **ATR dinâmico** (alarga stop em alta volatilidade).
- **Shutdown seguro**: `save-only` (padrão), `wait-flat`, `cancel-open`.

### FSM (fluxo de estados)
```
SCANNING ──→ SIGNAL_READY ──→ IN_POSITION ──→ WATCHING_92
   ↑              │                │                │
   │         (cancelado)      (prejuizo)    (timeout/contra)
   └──────────────┘────────────────┘────────────────┘
                                   │
                                   └──(lucro)──→ WATCHING_92 ──→ SIGNAL_READY
```

### Arquitetura alvo (Fases)
- **Fase 1 (infra, concluída)**: log rotativo, UTC, stateless/hydration, .env, heartbeat.
- **Fase 2 (em andamento)**: motor multi-setup — `CONFIG_SETUPS`, `SetupSignal`, `scoring.py` (RRR≥1, ordenar, executar 1º), novos setups, filtros MM200/MM50/IFR9/VWAP, Fibonacci.
- **Fase 3 (planejada)**: maestro **Go** (`orchestrator/`) — supervisor fora do caminho da ordem; Python é o único que fala com MT5 (lib nativa).

---

## 5. COMANDOS

```powershell
python main.py                 # Rodar o bot
python -m pytest -q            # Testes (25+)
python memoria\scripts\query_memory.py "pergunta"   # Consultar memória RAG
python memoria\scripts\build_memory.py              # Reindexar memória
```

---

## 6. CONVENÇÕES DO PROJETO

- **Nunca** editar `memoria/raw/` — fontes imutáveis.
- **Usar** o RAG antes de afirmar conhecimento sobre o projeto (perguntas de regras, arquitetura, decisões).
- **Logar** com o módulo `logging`, nunca `print()` em produção.
- **Testes** obrigatórios para mudanças de lógica (`test_*.py`, mock do MT5 via `conftest.py`).
- **Documentar** conhecimento novo no `memoria/wiki/` e reindexar.
- Respeitar o hardware alvo: **i3 4ª geração, 4GB RAM** — nada de dependências pesadas sem necessidade.

---

*Se você é uma IA recém-chegada: leia `memoria/README.md` em seguida para entender o RAG, depois `memoria/wiki/index.md`. Isso substitui anos de contexto com minutos de leitura.*
