# Design: MT5Bot — Motor Multi-Setup (Palex) + Maestro Golang

*Data:* 2026-08-11
*Status:* Proposto (pending user review)
*Autor:* Usuario + opencode
*Branch:* feat/palex-multi-setup-engine

---

## 1. Objetivo

Evoluir o MT5Bot de um bot de setup único (9.1) para um **motor multi-estratégia** baseado no livro de Alexandre Fernandes (Palex), com **arquitetura de dois pilares**:

- **Golang = Maestro (casca/orquestrador):** gerencia o ciclo de vida dos processos Python, supervisão de saúde (heartbeat via Standard I/O), reinício automático em crash, spawn on-demand de ativos e encerramento gracioso. **Não calcula indicadores, não envia ordens e não toca na API do MT5.** Fica fora do caminho da ordem — zero latência adicionada.
- **Python = Cérebro (worker):** toda a matemática (indicadores, setups, scoring, gestão de risco) e a comunicação direta com a API nativa do MetaTrader 5.

Execução em hardware restrito (i3 4ª geração, 4 GB RAM, Windows) com lote 0.01, buscando 1x–2x o risco por operação e trava de 1.0% de perda diária.

---

## 2. Princípios arquiteturais (do `aprofundamento.md`)

| Princípio | Regra |
|---|---|
| **Maestro fora do caminho** | Go supervisiona; Python lê, calcula e envia a ordem. Sem IPC no loop crítico de execução. |
| **Stateless + Data Hydration** | Worker não guarda estado local. Ao acordar, baixa os últimos 100 candles via `mt5.copy_rates_from_pos()` e reconstrói o contexto. MT5/corretora = fonte absoluta da verdade. |
| **Fonte da verdade = MT5** | `mt5.positions_get()` / `orders_get()` na inicialização. `state.json` vira apenas log de auditoria secundário, não fonte de estado. |
| **UTC em tudo** | Timestamps processados em UTC (Unix timestamp absoluto). Fuso local só para exibição de logs. Go usa `time.RFC3339Nano` em UTC. |
| **Logs com rotação** | `RotatingFileHandler` — 5 MB por arquivo, 3 backups (teto ~20 MB). |
| **Credenciais seguras** | `.env` + `python-dotenv`, `.env` no `.gitignore`. `mt5.initialize()` sem credenciais na sessão local (pega carona no terminal aberto). |
| **Resiliência de processos** | Heartbeat JSON a cada 1 s via stdout; watchdog no Go reinicia após 3 s sem sinal; Crash Loop Protection (3 falhas em <2 min desliga o worker); Graceful Shutdown via `os/signal`. |

---

## 3. Arquitetura alvo

```
┌─────────────────────────────────────────────────────────────┐
│                    MAESTRO (Golang, maestro.exe)              │
│  - Supervisiona workers (os/exec + bufio.Scanner)            │
│  - Heartbeat watchdog (3s timeout) + auto-restart            │
│  - Crash Loop Protection (backoff)                           │
│  - Graceful shutdown (os/signal)                             │
│  - CLI: add/stop <ativo> → spawn on-demand                   │
│  - Logs RFC3339Nano UTC em maestro.log                       │
└─────────────────────────────────────────────────────────────┘
        │ spawn / stdout JSON heartbeat {"status":"alive",...}
        ▼
┌─────────────────────────────────────────────────────────────┐
│              CÉREBRO (Python, worker.py)                     │
│  - Hydration: 100 candles ao iniciar (mt5.copy_rates_from_pos)│
│  - Indicators: EMA9, EMA21, MM21, MM50, MM200, IFR(9),       │
│    Bollinger(20,2), VWAP, ATR(14), RVOL, Fibonacci           │
│  - Setups: 9.1 | 9.2 | 9.3 | 9.4 | Ponto Contínuo | FFFD     │
│  - Motor de decisão: RRR gate + scoring multicritério        │
│  - Gestão de risco: 1% lote, daily max loss, breakeven,       │
│    trailing stop, saída parcial                              │
│  - Comunicação direta com a API MetaTrader5                  │
└─────────────────────────────────────────────────────────────┘
```

**Decisão de faseamento** (aprovada pelo usuário: Infra → Multi-Setup):

- **Fase 1 — Infra Python**: logs rotativos, UTC, stateless/hydration, `.env`, heartbeat emitido, métricas de expectância.
- **Fase 2 — Motor Multi-Setup**: unificar 9.1/9.2/9.3 no padrão plugin; adicionar 9.4, Ponto Contínuo, FFFD; filtros macro (MM200, MM50/72, IFR9, VWAP, afastamento, janelas de horário); motor de scoring + RRR; alvos Fibonacci e trailing.
- **Fase 3 — Maestro Golang**: orquestrador, watchdog, spawn on-demand, crash loop protection, graceful shutdown, build otimizado.

---

## 4. Fase 1 — Infraestrutura Python

### 4.1 Logging com rotação (`logger.py`)

Substituir/adaptar o logger atual por `RotatingFileHandler`:

```python
import logging
from logging.handlers import RotatingFileHandler

LOG_FILE = "mt5bot.log"
MAX_LOG_BYTES = 5 * 1024 * 1024   # 5 MB
LOG_BACKUP_COUNT = 3

def setup_logger(name="MT5Bot"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(LOG_FILE, maxBytes=MAX_LOG_BYTES,
                                  backupCount=LOG_BACKUP_COUNT, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)
    return logger
```

- Manter o console (TUI) como handler adicional apenas quando interativo.
- Substituir `print()` remanescentes por `logger.*`.

### 4.2 Timestamps em UTC

- Conversão de candles: `df['time'] = pd.to_datetime(df['time'], unit='s', utc=True)`.
- Logs: converter para fuso local apenas na exibição final.
- Registrar timestamp do candle em UTC no `tracker`.

### 4.3 Stateless + Data Hydration

- `worker.py` (novo entrypoint, ver Fase 2) inicia com: `mt5.copy_rates_from_pos(symbol, tf, 0, 100)` → recalcula EMA9/MM9 → deduz estado dos setups.
- `persistence.py`: manter apenas como gravação de auditoria; **não** mais como fonte de restauração de estado. `_validate_state_against_mt5`/`_check_orphaned_mt5_state` continuam (fonte da verdade = MT5).
- Config: `HYDRATION_CANDLES = 100` (300 se MM200 for usada no gráfico operacional).

### 4.4 Credenciais via `.env`

- Criar `.env` (não versionado) com `MT5_LOGIN`, `MT5_PASSWORD`, `MT5_SERVER`.
- `config.py` lê via `python-dotenv` (`load_dotenv()`).
- Garantir `.env` no `.gitignore`.
- `mt5.initialize()` permanece sem credenciais na sessão local; `mt5.login()` apenas se o usuário configurar credenciais.

### 4.5 Heartbeat (worker → maestro)

- `worker.py` imprime a cada 1 s: `{"status": "alive", "symbol": "HK50", "timestamp": "2026-08-11T03:18:46Z"}`.
- Config: `HEARTBEAT_INTERVAL_SECONDS = 1`, `HEARTBEAT_TIMEOUT_SECONDS = 3`.
- Modo TUI atual: emissão de heartbeat condicionada ao flag `--worker` (quando sob o maestro).

### 4.6 Métricas de Expectância

Novo módulo `metrics.py` (baseado no livro fundamentos p.317):

```python
def payoff(avg_win, avg_loss):
    return avg_win / avg_loss if avg_loss else 0.0

def expectancy(win_rate, avg_win, avg_loss):
    # Expectativa = (%acerto × GanhoMédio) − (%erro × PerdaMédia)
    return (win_rate * avg_win) - ((1 - win_rate) * avg_loss)

def expectancy_from_payoff(win_rate, po):
    # E = ((1 + PayOff) × %acerto) − 1
    return ((1 + po) * win_rate) - 1.0
```

- `tracker` alimenta `metrics` com o histórico de trades reais.
- Painel/TUI exibe `Expectativa`, `Pay Off`, `Win Rate`, `Drawdown máx`, `Sharpe` (quando aplicável).
- **Regra**: nunca operar sistema com expectativa negativa (registrar aviso no log).

### 4.7 Testes Fase 1

- `test_logger.py`: rotação cria arquivo de backup ao exceder tamanho (simular com `maxBytes` pequeno).
- `test_metrics.py`: `payoff`, `expectancy`, `expectancy_from_payoff` com valores conhecidos (ex: 60% acerto, ganho 2.0, perda 1.0 → E = 0.8).
- `test_config.py`: `.env` carregado com mocks (ausência → defaults seguros).

---

## 5. Fase 2 — Motor Multi-Setup

### 5.1 Padrão de plugins (feature flags)

`config.py` (default de fábrica = todos ativos):

```python
CONFIG_SETUPS = {
    "setup_9_1": True,     # já existe
    "setup_9_2": True,     # já existe
    "setup_9_3": True,     # já existe
    "setup_9_4": False,    # novo
    "ponto_continuo": True,   # novo
    "fffd_bollinger": False,  # novo
}
```

- Estrutura de sinal uniforme por setup:

```python
class SetupSignal:
    setup: str          # "9.1" | "9.2" | "9.3" | "9.4" | "PC" | "FFFD"
    side: TradeSide     # BUY | SELL
    entry: float        # preço de entrada (trigger)
    sl: float           # stop-loss técnico do setup
    target_1: float     # alvo parcial (ex: 100% amplitude / 1x risco)
    target_2: float     # alvo final (ex: 161.8% fib)
    ref_candle: tuple   # candle de referência (para condução/amplitude)
    score: float        # preenchido pelo motor de decisão
```

- `strategy.py`: cada setup vira um detector isolado que retorna `SetupSignal | None`; a máquina de estados consome o sinal eleito (não mais `_handle_scanning` hardcoded por setup).
- `SymbolState.setup_type` passa a aceitar os novos nomes.

### 5.2 Setups já existentes (consolidar)

- **9.1** — mantido: virada EMA9 → rompimento da máxima/mínima do candle de virada; anulação se EMA9 reverter antes do acionamento (sem limite de candles).
- **9.2** — revisar contra o livro: contexto EMA9 ascendente + candle fecha com mínima abaixo da mínima anterior (correção rápida); entrada no rompimento da máxima do candle de correção; stop na mínima do mesmo. O atual `WATCHING_92` (só após saída lucrativa) passa a ser uma das fontes do 9.2.
- **9.3** — manter lógica atual (recuo de ≥2 fechamentos abaixo do candle referência sem virar EMA9; entrada no rompimento da máxima).

### 5.3 Setups novos

#### 5.3.1 Setup 9.4 (Falso Recuo)

- Contexto: MME9 inclinada a favor.
- Gatilho: EMA9 vira contra por **exatamente um** candle (mínima estrutural não rompida); no candle seguinte retoma a direção original.
- Entrada: rompimento da máxima do candle que retomou a direção.
- Stop: abaixo da mínima do movimento de correção.
- Validação: se a mínima for rompida, desconfigura 9.4 (pode virar 9.1 de venda).

`indicators.py`:

```python
def check_setup_94_buy(all_rates, ema9_values):
    # EMA9 vira para baixo por 1 candle (slope_prev>0, slope_cur<0) e no
    # seguinte vira para cima (slope_cur>0), mínima da correção não rompida.
    ...
def check_setup_94_sell(all_rates, ema9_values):
    ...
```

#### 5.3.2 Ponto Contínuo (PC — MM21)

- Filtro: MM21 estritamente ascendente/descendente.
- Gatilho: preço recua e toca/aproxima a MM21; marca a máxima do candle de toque.
- Entrada: rompimento de 1 tick acima da máxima do candle de toque (para compra).
- Dinâmica de espera: se o preço cair mais sem romper, rebaixa o ponto para a máxima do novo candle de toque (enquanto MM21 mantiver direção).
- Stop: mínima do candle que tocou a média.

`indicators.py`:

```python
def get_mm21(rates):
    closes = close_prices(rates)
    return [sum(closes[i-20:i+1]) / 21 for i in range(20, len(closes))] if len(closes) >= 21 else None

def check_touch_mm21(candle, mm21_value, is_long):
    if is_long:
        return candle[3] <= mm21_value and candle[2] >= mm21_value  # toque/atravessou
    return candle[2] >= mm21_value and candle[3] <= mm21_value
```

#### 5.3.3 FFFD (Fechamento Fora / Fechamento Dentro — Bollinger 20,2)

- Contexto: volatilidade extrema; Bollinger (20, 2 desvios).
- Gatilho de compra: candle anterior fecha **fora** da banda inferior (sobrevenda/exaustão) + candle atual fecha de volta **dentro** da banda.
- Entrada: rompimento da máxima do candle que fechou dentro.
- Stop: mínima extrema do movimento que rompeu a banda.
- Alvo: linha central (SMA20) ou 2x risco.

`indicators.py`:

```python
def bollinger(rates, period=20, num_std=2.0):
    # Retorna (upper, middle, lower) por candle (com warmup de `period`)
    ...
def check_fffd_buy(all_rates):
    # candle[-2].close < lower[-2] e candle[-1].close dentro do canal
    ...
def check_fffd_sell(all_rates):
    ...
```

### 5.4 Filtros macro e indicadores de confirmação

| Filtro | Regra | Prioridade |
|---|---|---|
| **MM200** | Compras só com preço > MM200; vendas só com preço < MM200. Score 0 em sinais contra a MM200. | alta |
| **Alinhamento de médias** | Quanto mais médias alinhadas (Preço > EMA9 > MM21 > MM50), maior o score. | alta |
| **IFR(9)** | Filtro de exaustão: em 9.2/9.3 de compra, IFR(9) saindo da zona de sobrevenda adiciona score. | média |
| **MTF (existe)** | EMA9/21 no timeframe superior confirma direção. | mantido |
| **RVOL (existe)** | Volume da vela > 1.15× média de 20. | mantido |
| **VWAP** | Intraday (HK50): compra esticada e muito abaixo da VWAP é vetada; toque na VWAP dá score máximo. | média (Fase 2.5) |
| **Afastamento da MM21** | Preço esticado da média → score 0 (risco de reversão à média). | média |
| **Janelas de horário** | Bloquear abertura de novas posições em janelas críticas (1ª meia hora pós-notícias macro; fim do pregão). | baixa |
| **Barra de Ignição** | Candle de gatilho com corpo longo + volume alto → score máximo. | baixa |
| **Barra de Esforço sem resultado** | Candle grande + fechamento medíocre (pavio de rejeição) → **veta** o setup. | baixa |

### 5.5 Motor de decisão (scoring + RRR)

Novo `scoring.py`, unificando as funções descritas no `aprofundamento.md`:

```python
def validar_risco_retorno(entrada, stop, alvo, direcao, multiplicador_minimo=1.0) -> bool:
    risco = abs(entrada - stop)
    if risco <= 0:
        return False
    rrr = abs(alvo - entrada) / risco
    return rrr >= multiplicador_minimo

def calcular_score(sinal: SetupSignal, contexto) -> float:
    # - rrr * 30.0 (bonificação por múltiplo maior de risco)
    # + congruência macro (MTF + alinhamento de médias) * 25.0
    # + proximidade da média (stop curto/barato) * 20.0
    # + confirmação de volume (RVOL) * 25.0
    # + barra de ignição bônus / esforço falho → 0 (veto)
    # Trava: se rrr < 1.0 → score = 0 (inviável)
    ...
```

Fluxo por candle fechado:
1. Roda todos os setups habilitados → lista de `SetupSignal`.
2. Aplica filtros macro; zera score dos vetados.
3. Aplica `validar_risco_retorno` (mín 1x); zera os inválidos.
4. `sorted(candidatos, key=lambda x: x["score"], reverse=True)`.
5. Executa apenas o primeiro (1 posição por símbolo).

### 5.6 Alvos geométricos e Fibonacci

- **Alvo simples** (9.2/9.3/FFFD): projeção da amplitude do candle de gatilho a partir da entrada (1x = parcial, 2x = final).
- **Alvo por extensão de Fibonacci** (9.1/PC):
  - Mapear último Swing Low → Swing High da perna anterior (amplitude = topo − fundo).
  - Alvo 1 (parcial 50%): `entrada + amplitude`.
  - Alvo 2 (final): `entrada + (amplitude × 1.618)`.
  - Validar RRR no Alvo 1 (≥1x risco).

`indicators.py`:

```python
def swing_levels(rates, lookback=20):
    # Retorna (swing_high, swing_low) dos últimos `lookback` candles
    ...
def fib_extension_targets(entry, swing_high, swing_low, is_long):
    amp = swing_high - swing_low
    if is_long:
        return (entry + amp, entry + amp * 1.618)
    return (entry - amp, entry - amp * 1.618)
```

### 5.7 Condução e saída (gestão de posição)

- **Saída parcial (existe)**: 50% no Alvo 1.
- **Zero Loss automático**: ao executar a parcial, mover SL para o preço de entrada (breakeven). Já existe `ENABLE_BREAKEVEN`/`BREAKEVEN_ATR_RATIO` — revisar para atrelar ao momento da parcial.
- **Trailing Stop dinâmico** (novo, `trailing.py`):
  - BUY: ajustar SL para a mínima do penúltimo candle (ou colar abaixo da EMA9/MM21), atualizado barra a barra após o breakeven.
  - SELL: simétrico (máxima do penúltimo candle).
  - Se o preço perder a média de referência, liquidar o restante a mercado.
- **Saída final (existe)**: EMA9 virar contra → fechar restante.

### 5.8 Configuração adicionada

```python
# --- Fase 2: Setups novos ---
SETUP_94_MAX_RECUO_CANDLES = 1
PC_MAX_WAIT_CANDLES = 5
FFFD_PERIOD = 20
FFFD_STD = 2.0

# --- Filtros macro ---
MM200_ENABLED = True
MM200_PERIOD = 200
MM50_ENABLED = True
MM50_PERIOD = 50
IFR9_ENABLED = True
VWAP_ENABLED = True

# --- Motor de decisão ---
MIN_RISK_REWARD = 1.0          # mínimo 1x o risco
SCORE_WEIGHTS = {
    "rrr": 30.0, "congruencia_macro": 25.0,
    "proximidade_media": 20.0, "volume": 25.0,
}

# --- Trailing ---
TRAILING_ENABLED = True
TRAILING_MODE = "candle"        # "candle" | "ema9" | "mm21"
```

### 5.9 Testes Fase 2

- `test_setups.py`: tabela-driven para cada detector (9.1–9.4, PC, FFFD) com séries OHLCV sintéticas conhecidas (compra/venda, anulação, timeout).
- `test_scoring.py`: `validar_risco_retorno`, `calcular_score` (RRR <1 → 0; veto por MM200; ignição bônus).
- `test_fib.py`: `fib_extension_targets` com valores exatos.
- `test_trailing.py`: SL segue mínima do penúltimo candle; perda da média → liquida.

---

## 6. Fase 3 — Maestro Golang

### 6.1 Estrutura

```
orchestrator/
  go.mod
  main.go           # entrada, sinais OS, CLI
  worker.go         # struct WorkerProcess, spawn, kill
  heartbeat.go      # watchdog, timeout, reinício
  cli.go            # add/stop/list ativos
```

### 6.2 Compilação otimizada (Windows, i3 4GB)

```bash
env GOOS=windows GOARCH=amd64 go build -ldflags="-s -w -H=windowsgui" -o maestro.exe main.go
```

- `-s -w`: remove símbolos/debug.
- `-H=windowsgui`: roda em background, sem janela de terminal.

### 6.3 Ciclo de vida

```go
type WorkerProcess struct {
    Symbol    string
    Cmd       *exec.Cmd
    StartTime time.Time
    Status    string
    Restarts  int
    LastFail  time.Time
}
```

- `startWorker(symbol)`: `exec.Command("python", "worker.py", "--symbol", symbol)`, conecta stdout/stderr.
- `stopWorker(symbol)`: encerramento gracioso (escreve `{"cmd":"shutdown"}` no stdin do worker ou `proc.Kill()` após timeout de 5 s).
- CLI assíncrona (bufio.Scanner no terminal principal): `add EURUSD`, `stop HK50`, `list`.

### 6.4 Heartbeat watchdog

```go
func watchHeartbeat(w *WorkerProcess, timeout time.Duration) {
    scanner := bufio.NewScanner(w.Cmd.Stdout)
    for scanner.Scan() {
        line := scanner.Text()
        var hb struct{ Status, Symbol, Timestamp string }
        if json.Unmarshal([]byte(line), &hb) == nil && hb.Status == "alive" {
            w.LastBeat = time.Now()
            continue
        }
        // linhas não-JSON (logs Python) apenas passam para o log central
        log.Printf("%s - %s\n", time.Now().UTC().Format(time.RFC3339Nano), line)
    }
}
```

- Goroutine por worker; `time.Since(w.LastBeat) > 3s` → SIGKILL + restart.
- **Crash Loop Protection**: 3 falhas em <2 min → desliga o worker, loga `[MAESTRO] CRASH LOOP: worker desligado para proteger a banca`, mantém desligado até comando manual.

### 6.5 Logs do maestro

- Formato: `timestamp RFC3339Nano UTC - INFO - [Maestro] <evento>`.
- Arquivo `maestro.log` (centralização de auditoria), cruzável com `mt5bot.log`.

### 6.6 Testes Fase 3

- `main_test.go`: table-driven tests para parsing de CLI (`add`, `stop`, `list`), decisão de restart (timeout), crash loop protection (limite de 3).
- Não depende do MT5 — workers mockados via `testworker.py` que imprime heartbeat e sai.

---

## 7. Ordem de execução e dependências

```
Fase 1 (Infra Python)          → base para tudo
   ├── 4.1 logs rotativos
   ├── 4.2 UTC
   ├── 4.3 stateless/hydration
   ├── 4.4 .env
   ├── 4.5 heartbeat
   └── 4.6 metrics
Fase 2 (Multi-Setup)           → depende de 4.6 (expectância p/ validar)
   ├── 5.1 padrão plugin
   ├── 5.2–5.3 setups (9.4, PC, FFFD)
   ├── 5.4 filtros macro
   ├── 5.5 scoring
   ├── 5.6 alvos fib
   └── 5.7 trailing
Fase 3 (Maestro Go)            → depende de 4.5 (heartbeat emitido)
   ├── 6.3 ciclo de vida
   ├── 6.4 watchdog
   └── 6.6 testes Go
```

Cada fase entrega software testável e operável sozinha.

---

## 8. Riscos e decisões abertas

| Risco/Decisão | Impacto | Ação |
|---|---|---|
| `state.json` → stateless | Mudança de paradigma; risco de regressão na recuperação de ordens órfãs | Manter `_validate_state_against_mt5` como rede de segurança; testes de recuperação |
| Conflito de sinais multi-setup no mesmo ativo | 1 posição por símbolo; eleição por score | Motor de decisão resolve (5.5) |
| 9.2 atual (WATCHING_92 pós-lucro) vs 9.2 do livro (correção rápida) | Duas leituras do setup | Consolidar em detector único (5.2), mantendo flags de configuração |
| VWAP/MM200 em símbolos 24/7 (BTC/ETH) | VWAP diária sem sessão clara | Config por símbolo; desabilitar VWAP se ausente |
| Go exige toolchain na máquina | Fase 3 depende de instalação | Registrar pré-requisito; Fases 1–2 rodam sem Go |
| Expectância real negativa após medição | Bot lucrativo na teoria, perdedor na prática | `metrics.py` (4.6) expõe; regra de bloqueio manual |

---

## 9. Fora de escopo (futuro)

- Backtesting vetorizado e simulação de Monte Carlo (documentado no livro, sugerido para fase futura).
- Notificações Telegram/Discord (desagregadas pelo usuário).
- Deploy em VPS Linux (híbrido: MT5 em Windows + maestro/cérebro em Linux) — documentado no `aprofundamento.md` como evolução portável.
- Múltiplas posições por símbolo.
