# Redesign da Interface TUI do Maestro (v2.4)

Data: 2026-08-14
Status: Aprovado pelo usuário (mockup fornecido)
Escopo: 100% estético — nenhuma mudança na lógica de trading, FSM, worker ou Python brain.

## Objetivo

Modernizar a interface Bubble Tea do orquestrador Go (`maestro/main.go`), mantendo a
identidade da marca, com layout em grid, painel de performance modo-consciente, badges
de status e paleta Tokyo Night + âmbar.

## Layout (mockup aprovado)

```
┌─ MAESTRO v2.4 ───────────────────────────── [ MODE: SIMULATOR ] ── [ MT5: CONNECTED ] ─┐
│ ATIVOS EM EXECUÇÃO      │ EVENT LOG (Live Stream)                                 │
│ ──────────────────────  │ 12:05:07 [EURNOK] Entrada registrada: SELL @ 10.92258   │
│ EURUSD  │ M5  │ [SCAN]  │ 12:05:08 [EURNOK] PnL: -79.52 USD (loss)                │
│ HK50    │ M5  │ [WAIT]  │ 12:05:09 [AUDCAD] Setups detectados, mas vetados (RRR)  │
│ US500   │ M5  │ [SETUP] │ 12:05:09 [US500] 9.2 Venda Falhou: EMA9 aponta para baixo│
│ US100   │ M5  │ [SCAN]  │ 12:05:09 [EURNOK] Aguardando: 9.2 Venda Falhou          │
│ USDJPY  │ M5  │ [SCAN]  │                                                         │
│ AUDUSD  │ M5  │ [WAIT]  │ ─────────────────────────────────────────────────────── │
│ GBPUSD  │ M5  │ [SCAN]  │ PERFORMANCE RESUMO (Sessão Atual)                       │
│ AUDCAD  │ M5  │ [SETUP] │ PnL Total: -$158.40  |  Win Rate: 42%  |  Trades: 12    │
└─────────────────────────┴─────────────────────────────────────────────────────────┘
```

## Design Tokens (paleta Tokyo Night + âmbar)

| Token | Cor | Uso |
|---|---|---|
| `bg` | `#1A1B26` | Fundo geral |
| `border` | `#414868` | Bordas dos painéis (RoundedBorder) |
| `text` | `#C0CAF5` | Texto principal |
| `amber` | `#E0AF68` | Título MAESTRO, badges de espera |
| `green` | `#9ECE6A` | Sucesso, lucro, badges SCAN/SETUP/POS |
| `red` | `#F7768E` | Erro, prejuízo |
| `blue` | `#7AA2F7` | Badges de sistema (MODE/MT5), ciano |

## Componentes

### 1. Top bar (header)
- Título **MAESTRO v2.4** à esquerda, âmbar bold.
- Badges à direita: `[ MODE: SIMULATOR ]` e `[ MT5: CONNECTED ]`.
- Implementado como linha de texto acima dos painéis (lipgloss não embute texto na borda;
  a borda superior fica `─...─` e o título é a primeira linha do View).
- `[ MODE: X ]` azul ciano; `[ MT5: ON/OFF ]` verde quando ON, vermelho quando OFF.

### 2. Painel esquerdo — ATIVOS EM EXECUÇÃO (~33% largura)
- Cabeçalho: `ATIVOS EM EXECUÇÃO` + linha separadora.
- Colunas: `ATIVO | TF | STATUS`.
- Linha por worker ativo: `EURUSD  │ M5  │ [SCAN]`.
- Badge de status derivado do `state_text` do Python (ver mapa abaixo).
- Uptime ou cor do ativo mantidos como destaque.

### 3. Painel direito superior — EVENT LOG (Live Stream)
- Viewport de logs (comportamento atual, cap 1000 linhas).
- Timestamps em cinza, `[ATIVO]` colorido pela cor do worker (já existente).
- Título centralizado `EVENT LOG (Live Stream)`.

### 4. Painel direito inferior — PERFORMANCE RESUMO (Sessão Atual)
- Título `PERFORMANCE RESUMO (Sessão Atual)`.
- Linha única: `PnL Total: -$158.40  |  Win Rate: 42%  |  Trades: 12`.
- **Modo-consciente**:
  - Se qualquer worker tem `IsStudyMode == true` → painel lê `virtual_trades.json`
    (paper/simulador) e o badge de modo mostra `SIMULATOR`.
  - Senão → lê `trades.json` (real) e badge mostra `LIVE`.
- PnL com cor condicional (verde positivo, vermelho negativo).
- Win Rate = wins / (wins + losses) entre trades fechados.
- Trades = total de trades fechados (result != "open").

## Fonte de dados (leitura no Go)

Novo arquivo `maestro/metrics.go` (padrão stdlib, sem dependências novas):

- `readTradesFile(path string) []Trade` — parse de `trades.json`/`virtual_trades.json`.
- Struct `Trade { Result string; PnLMoney float64 }`.
- `computeSummary(trades []Trade) Summary { PnL float64; WinRate float64; Trades int }`.
- Caminhos: `%APPDATA%/mt5bot/trades.json` e `%APPDATA%/mt5bot/virtual_trades.json`
  (mesma convenção de `lang.go` e do `persistence.py`).
- Leitura a cada tick (1s) no `updateStatus()` — barata, arquivos pequenos.

## Mapa de badges de status (state_text → badge)

| state_text (Python) | Badge | Cor |
|---|---|---|
| `SCANNING` / `STUDY_SCANNING` / `WAIT_DATA` | `[SCAN]` | azul |
| `PENDING` / `EXTERNAL_POS` / `WAIT` | `[WAIT]` | âmbar |
| `IN_POSITION` / `PAPER_TRADE` | `[POS]` | verde |
| `ERRO:` (via StatusText) | `[ERRO]` | vermelho |

## Modo (badge de modo)

- `study` presente → `SIMULATOR` (mesmo que haja mistura; a leitura de performance usa
  o arquivo virtual).
- Nenhum worker de estudo → `LIVE`.

## MT5 (badge de conectividade — inferência)

- `ON` (verde): ≥1 worker ativo e sem erro reportado.
- `OFF` (vermelho): nenhum worker ativo ou algum reportou erro (`StatusText` contém "ERRO").
- Documentado no código como inferência (o maestro não fala com MT5 diretamente).

## Decisões de design profissional (revisão frontend-design)

Incorporadas ao spec; nenhuma altera a lógica de trading.

### 1. Hierarquia de severidade nos logs
- `worker.go`: a cor do símbolo passa a aplicar **apenas no tag `[ATIVO]`**, não na linha inteira.
- Mensagem do log em texto neutro (`text`), com **erros em vermelho** (`red`).
- Regra: erros são o elemento mais "alto" na hierarquia visual; cor-por-símbolo nunca compete com severidade.

### 2. Paleta de símbolos disciplinada (assinatura)
- Rotação de cores substituída por paleta curada de 6 tons dimmed (Tokyo Night):
  `#7AA2F7, #9ECE6A, #E0AF68, #F7768E, #BB9AF7, #7DCFFF`.
- Atribuição determinística por ordem de criação do worker (`symbolColors[i % 6]`).
- Cor usada **só** no tag `[ATIVO]`; nunca na linha inteira do log.

### 3. Terminologia do modo consistente
- Subtítulo do EVENT LOG dinâmico: `EVENT LOG (Live)` ou `EVENT LOG (Simulador)`,
  seguindo o mesmo critério do painel de performance (`IsStudyMode`).

### 4. Badges sem emoji, alinhados à direita
- `state_text` do Python vem com emoji (`🔵 SCANNING` etc.) — emojis renderizam mal em
  terminal Windows. Mapear para badges limpos com largura fixa:
  `[SCAN]` (azul), `[WAIT]` (âmbar), `[POS]` (verde), `[ERRO]` (vermelho).
- Badges alinhados à direita na coluna STATUS (largura fixa, coluna sempre reta).

### 5. Tipografia de dados
- Números alinhados à direita; labels de largura fixa (`PnL Total:  `, `Win Rate:    `).
- Win Rate com 1 casa decimal (`42.0%`).
- PnL sempre com sinal (`-$158.40` / `+$22.66`), cor condicional (verde positivo, vermelho negativo).

### 6. Design tokens centralizados (novo `maestro/style.go`)
- Todos os hex nomeados em um único arquivo (`style.go`): `Amber, Green, Red, Blue,
  Purple, Cyan, Border, Text, Dim, Bg`.
- `main.go`, `worker.go` e `metrics.go` derivam cores dos tokens, nunca repetem hex.

### Opcional (se aprovado)
- Versão dinâmica: ler `pyproject.toml` para exibir a versão real em vez de `v2.4` fixo.

## Limitações / decisões

- Lipgloss não embute texto na borda: título e badges ficam na linha superior, não na borda
  propriamente dita (visual equivalente ao mockup).
- Logs com PnL colorido (verde/vermelho dentro do fluxo de log) fica fora do escopo inicial
  (item mais caro); apenas timestamp cinza + `[ATIVO]` colorido + erros em vermelho.

## Arquivos alterados

- `maestro/style.go` — NOVO: design tokens centralizados (todas as cores nomeadas) + paleta de símbolos.
- `maestro/metrics.go` — NOVO: leitura de trades e cálculo de summary.
- `maestro/badges.go` — NOVO: mapeamento `state_text` → badge e detecção de modo/MT5 (testável isoladamente).
- `maestro/main.go` — header, grid (left + right-top + right-bottom), badges, painel de performance, terminologia de modo dinâmica.
- `maestro/worker.go` — cor aplicada apenas no tag `[ATIVO]`; mensagem neutra; erros em vermelho; paleta de símbolos curada; correção de `go vet` (`log.Printf` → `log.Print`).
- `maestro/metrics_test.go`, `maestro/badges_test.go`, `maestro/style_test.go` — NOVOS: testes unitários.

## Critérios de aceite

1. TUI abre com layout de 4 regiões + top bar.
2. Badge MODE reflete `/study` (SIMULATOR) vs `/add` (LIVE).
3. Painel performance lê o JSON correto pelo modo e mostra PnL/WR/Trades com cores.
4. Badges de status por ativo corretos (sem emoji, alinhados à direita).
5. Logs: tag `[ATIVO]` colorido, mensagem neutra, erros em vermelho.
6. Todos os hex derivados de `style.go` (nenhum hex solto em main.go/worker.go).
7. `go build` sem erros; testes do maestro passam.
8. Sem mudança em arquivos Python nem lógica de trading.