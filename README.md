# MT5Bot Maestro

<p align="center">
  <img src="https://upload.wikimedia.org/wikipedia/commons/c/c2/MetaTrader_5_logo.png" width="100" alt="MetaTrader 5">
  <br>
  <em>Robô de trading automatizado para MetaTrader 5 — arquitetura híbrida Go + Python.</em>
</p>

> [!IMPORTANT]
> **Filosofia de Proteção ao Capital**
> O robô não busca ganhos desmedidos na sorte. O objetivo central é **proteger o patrimônio, perder cada vez menos**, e só autorizar ordens quando o risco for estritamente controlado e proporcional ao saldo da sua conta.

---

## Índice

- [Destaques](#destaques)
- [Pré-requisitos](#pré-requisitos)
- [Instalação e execução](#instalação-e-execução)
- [CLI interativa (Maestro)](#cli-interativa-maestro)
- [Condução de posição](#condução-de-posição)
- [Modo assistência (posições externas)](#modo-assistência-posições-externas)
- [Setups embutidos](#setups-embutidos)
- [Motor de decisão](#motor-de-decisão)
- [Arquitetura](#arquitetura)
- [Testes, CI e qualidade](#testes-ci-e-qualidade)
- [Compatibilidade e hardware alvo](#compatibilidade-e-hardware-alvo)
- [Open source e IA](#open-source-e-ia)
- [Licença](#licença)

---

## Destaques

- **Arquitetura híbrida**: orquestrador em **Golang** (CLI não bloqueante, multi-worker) + cérebro em **Python** (cálculos com pandas/numpy, comunicação nativa com o MT5).
- **Posição sizer dinâmico**: lote calculado pelo saldo da conta — o stop-loss financeiro **nunca passa de 1% do capital** por operação.
- **Recuperação institucional (stateless)**: posições ficam protegidas por **hard stop-loss na corretora**. Se o PC cair ou reiniciar, o bot mapeia os trades abertos e reassume exatamente de onde parou — sem reprocessar decisões perdidas do estado local.
- **CLI estilo terminal (Split-Screen)**: Maestro TUI com arquitetura visual avançada (Bubbletea + Lipgloss), layout dividido para acompanhamento real-time, controle de múltiplos robôs isolados e namespaces com `color-coding`.
- **Machine Learning Context V2 (Elite Quant)**: Diferente de robôs amadores que usam datasets públicos cheios de ruído, o nosso "Cérebro Python" captura a **assinatura genética do mercado em tempo real** (ADX, Z-Score, distâncias para EMA9/SMA200, microestrutura do candle). O dataset é gerado *cirurgicamente* apenas quando o setup arma, registrando o contexto exato antes de prever resultados reais (Forward Tracking). É a base perfeita e livre de ilusões de backtest para treinar nossa futura Inteligência Artificial em XGBoost/LightGBM.
- **Roteamento Multi-Ativos Inteligente**: O bot adapta as regras operacionais, lotes obrigatórios e setups autorizados de acordo com o ativo negociado (ex: estratégia isolada de Reversão à Média no HK50 rodando lado a lado com Seguidores de Tendência no Forex).
- **12 setups** da família 9.x, Ponto Contínuo, FFFD, DiNapoli, Russian BB (HK50) e mais — cada um com scoring e filtros macro.

---

## Pré-requisitos

| Item | Versão mínima | Observação |
|------|---------------|------------|
| Sistema | Windows 10/11 | MetaTrader 5 só existe para Windows |
| Python | 3.10+ | com pip |
| Go | 1.20+ | compilador necessário para o Maestro |
| MetaTrader 5 | — | instalado e logado (demo ou real) |

> [!NOTE]
> O CI (GitHub Actions) roda os testes em Linux **sem** o MetaTrader 5 — a suíte mocka a API do MT5. Instalação em desenvolvimento é **Windows**.

---

## Instalação e execução

```bash
git clone https://github.com/fabiodrneles/mt5_bot.git
cd mt5_bot

# Dependências Python (MetaTrader5 + pandas + numpy)
pip install .

# Inicie o Maestro (terminal interativo) — ou via run.bat no Explorer
python main.py
```

O terminal do Maestro abre com a identidade visual laranja. Digite `/help` para começar.

---

## CLI interativa (Maestro)

Prompt: `mt5bot ❯`

| Comando | O que faz |
|---------|-----------|
| `/help` | Lista os comandos disponíveis |
| `/add <ativo> [timeframe]` | Adiciona e inicia uma thread Python dedicada ao ativo. Ex.: `/add WIN M5` |
| `/study <ativo> [timeframe]` | Inicia o ativo em modo simulação (apenas envia logs, sem abrir ordens reais) |
| `/stop <ativo>` | Para a operação em um ativo (ou `/remove` — mesmo efeito) |
| `/list` | Lista os ativos operando |
| `/report` | Relatório de performance no terminal (ganhos vs perdas) |
| `/dashboard` | Abre o painel visual no navegador (servidor local) |
| `/fix` | Repara/reinicia forçosamente um robô que entrou em "Crash Loop" |
| `/idioma <pt\|en\|es>` | Troca o idioma da interface em tempo real |

### Saída segura (`/quit`)

Escolha o modo de desligamento conforme suas posições no mercado:

| Modo | Comportamento |
|------|---------------|
| `/quit` (padrão) | Mantém posições protegidas pelo stop-loss na corretora; o bot local encerra |
| `/quit cancel-open` | Cancela ordens pendentes (não ativa na sua ausência) e encerra |
| `/quit wait-flat` | Para de buscar oportunidades e só desliga quando as posições fecham sozinhas no alvo |
| `/quit close-all` | **Botão de pânico** — liquida todas as posições a mercado e encerra |

---

## Condução de posição

O bot não larga a posição após a entrada — conduz barra a barra:

- **Saída parcial**: lucro de 1× ATR fecha 50% do volume (`PARTIAL_EXIT_ENABLED = True`).
- **Breakeven**: com 1× ATR a favor, o stop sobe/desce para o preço de entrada (`ENABLE_BREAKEVEN`).
- **Trailing stop dinâmico**: após o breakeven, o stop cola no mercado:
  - `TRAILING_MODE = "candle"` (padrão): BUY segue a mínima do penúltimo candle, SELL a máxima.
  - `"ema9"` / `"mm21"`: cola o stop na EMA9 ou SMA21.
  - Se o preço perder a média de referência, o restante é liquidado a mercado.
- **Saída final**: EMA9 virando contra a posição aperta o stop para a extremidade do candle.

Toda a lógica de condução vive em `brain/trailing.py` (pura e testável) orquestrada pelo `execution_manager`.

---

## Modo assistência (posições externas)

Se você abrir uma posição **manualmente** no MT5, o Maestro detecta e **adota** a posição automaticamente (ciclo de 5 s):

- Registra como setup `MANUAL` no relatório de performance.
- Guia o stop (breakeven a 1× ATR + trailing EMA9) e o alvo (saída parcial de 50%).
- **Reconciliação automática**: se você fechar na mão ou o stop fechar, o bot detecta e mantém o relatório 100% sincronizado.

> [!NOTE]
> A assistência é aplicada por ativo monitorado. Adicione o ativo com `/add <ativo> <timeframe>` para ele adotar posições manuais. Desligue com `MANAGE_EXTERNAL_POSITIONS = False` em `config.py`.

## Ferramentas Úteis

Você pode rodar simulações pesadas (backtest) na sua própria máquina sem alterar o robô ou depender da corretora, usando o simulador interno:

```powershell
# Rodar 12 meses de simulação financeira do HK50 (M5)
python tools\backtest.py --months 12

# Você pode personalizar o capital, lote e ativo:
python tools\backtest.py --months 6 --balance 100.0 --lot 0.50 --symbol HK50
```

---

## Setups embutidos

Motor de varredura com 11 setups, todos configuráveis em `CONFIG_SETUPS` no `config.py`:

| Setup | Estratégia |
|-------|-----------|
| GAP | Gaps de fuga na abertura (ex.: HK50), direção institucional nos primeiros candles |
| 9.1 | Agressão primária + virada da MME9 — inícios de tendência |
| 9.2 | Pullback curto contra a EMA9, retomada da continuação |
| 9.3 | Recuo mais profundo na média, continuação com EMA9 a favor |
| 9.4 | Falso recuo — dentro da família 9.x |
| Ponto Contínuo (PC) | Toque na MM21 — entradas cirúrgicas a favor da tendência |
| FFFD | Bandas de Bollinger: exaustão e reversão de retorno à média |
| DiNapoli | Estratégia DiNapoli |
| IFR2 | IFR 2 períodos com MME50 |
| SAR | Parabolic SAR com IFR14 |
| RompFalso | Rompimento falso (reversão) |

**Filtros protetores** — toda ordem passa antes de ser enviada:

- **SMA200** (tendência de longo prazo): em `brain/setups.py`, aborta contra a macro. GAP é isento por ser reversão agressiva.
- **MM50** (`check_mm50_filter`): compra só acima da MM50, venda só abaixo.
- **IFR9** (`check_ifr9_filter`): confirma saída de zona de exaustão.
- **MTF** (`check_mtf_trend`): time frame superior precisa concordar com a direção (EMA9 > EMA21 no TF maior).
- **Spread**: aborta entradas com spread abusivo (`MAX_SPREAD_POINTS`).
- **Limite de perda diária** (`MAX_DAILY_LOSS_PERCENT`): trava novas entradas quando o dia está no prejuízo máximo.

---

## Motor de decisão

Quando vários setups disparam no mesmo ativo, `brain/scoring.py` pontua cada um (`calcular_score`), aplica o gate de **RRR mínimo** (`MIN_RISK_REWARD`) e executa **apenas o 1º colocado**:

- **Vetos (anulam o setup)**: preço contra a **MM50**, preço esticado além de `VWAP_MAX_DEVIATION_ATR`, e filtro **MTF** (time frame superior nega a direção). O 2º colocado assume.
- **Bônus (elevam a nota)**: IFR9 saindo de exaustão e toque milimétrico na VWAP (≤ 0.5 ATR).

**Alvo top-down Fibonacci**: setups sem alvo próprio recebem extensão 1.0×/1.618× da amplitude do swing (`swing_levels` + `fib_extension_targets`).

---

## Arquitetura

```
mt5_bot/
├── maestro/                 # Orquestrador (Golang)
│   ├── main.go              # CLI interativa + gerenciador de workers
│   ├── worker.go            # crash-loop protection (3 falhas / janela)
│   ├── cli.go               # parseCommand (testável)
│   └── main_test.go         # testes table-driven da CLI
├── brain/                   # Cérebro (Python)
│   ├── main.py              # loop por ativo, hidrata candles
│   ├── setups.py            # StrategyScorer — 11 setups + SMA200
│   ├── indicators.py        # EMA/ATR/VWAP + filtros (MM50, IFR9, MTF, RVOL)
│   ├── scoring.py           # motor de decisão multicritério
│   ├── execution_manager.py # validação de risco, condução, reconciliação
│   └── trailing.py          # trailing dinâmico (modos candle/ema9/mm21)
├── config.py                # configuração central
├── executor.py              # ordens/posições MT5
│   ├── shutdown_manager.py  # modos de saída do /quit
├── risk_calculator.py       # lote dinâmico (1%) + limites por sessão
├── tracker.py               # histórico + performance
├── dashboard.py             # painel web local (HTML, sem dependências)
└── main.py                  # entrypoint global (roteia para o Maestro Go)
```

**Fluxo**: Maestro Go (interface TUI Bubbletea, color-coding) gerencia processos isolados por ativo → `brain/main.py` (Worker) hidrata candles, extrai ML Context V2 e chama `StrategyScorer.evaluate_all` → `scoring.py` ranqueia → `execution_manager.py` valida risco/horário/filtros → `executor.py` envia a ordem ao MT5.

---

## Testes, CI e qualidade

```bash
# Suíte Python completa (mocka o MetaTrader5 — roda sem terminal)
python -m pytest -q

# Testes Go do Maestro
cd maestro && go test ./...
```

### Ferramentas Analíticas (Backtest)
Para testar a eficiência dos filtros de proteção (RVOL, Risco/Retorno, etc.), você pode rodar a ferramenta de simulação `test_filters.py`. Ela avalia os trades que o bot **rejeitou**, puxa o histórico de preços real pós-sinal e calcula se o trade daria Gain ou Loss caso o filtro estivesse desligado:
- Dê um clique duplo no arquivo `testar_filtros.bat` na pasta principal.
- Ou rode pelo terminal: `python tools\test_filters.py`

**Simulador de Backtest Local (Campeonato Matemático)**
Para simular as estratégias e testar novos parâmetros (como a Janela Institucional do HK50) contra milhares de candles do MetaTrader sem arriscar capital:
- Rode: `python tools\backtest.py --months 24`

- CI (`.github/workflows/ci.yml`) roda ambos no GitHub Actions: `pytest` em Python 3.12 e `go vet` + `go test` em Go 1.25.
- Estado persistente da aplicação em `%APPDATA%/mt5bot`.

---

## Compatibilidade e hardware alvo

- **MetaTrader 5** obrigatório apenas em produção (Windows). A lógica de estratégia, scoring e condução é 100% testável sem MT5.
- Hardware alvo conservador (**i3 4ª geração, 4 GB RAM**): dependências Python mínimas; o motor de memória RAG usa BM25 (stdlib puro), sem embeddings.

---

## Open source e IA

> [!TIP]
> **Para IAs e desenvolvedores que estudam o projeto:** o repositório mantém uma **memória permanente RAG** (`memoria/`) com os livros-fonte, arquitetura e decisões técnicas. Antes de programar qualquer coisa, leia o arquivo [`AGENTS.md`](AGENTS.md).

---

## Licença

MIT — use, estude, modifique e lucre. Feito com ☕ e disciplina.