# MT5Bot — Documentacao Tecnica Completa

Este documento explica toda a arquitetura, logica de negocios, fluxo de dados e decisoes de design do MT5Bot. Destinado a qualquer desenvolvedor ou IA que precise entender, manter ou corrigir a aplicacao.

---

## 1. O que e este sistema

Bot de trading automatizado para MetaTrader 5 (MT5). Opera no timeframe H1 usando dois setups tecnicos (9.1 e 9.2 de Palex/Larry Williams) com gestao de risco adaptativa. O bot:

1. Conecta ao terminal MT5 via API Python
2. Monitora candles H1 a cada 10 segundos
3. Detecta sinais de entrada baseados em EMA9/EMA21
4. Coloca ordens stop (pendentes) no broker
5. Gerencia posicoes abertas (saida parcial + saida pela EMA9)
6. Registra todas as operacoes para relatorio de performance

---

## 2. Estrutura de arquivos

```
mt5_bot-main/
├── main.py            → Entry point, CLI, loop principal
├── tui.py             → Interface terminal (conexao MT5 + config)
├── dashboard.py       → Interface web (config + relatorio)
├── config.py          → Parametros globais (constantes)
├── indicators.py      → Calculos tecnicos (EMA, ATR, alvo adaptativo)
├── strategy.py        → Maquina de estados (cerebro do bot)
├── executor.py        → Comunicacao com MT5 (ordens, posicoes)
├── persistence.py     → Salvar/carregar estado em JSON
├── tracker.py         → Registro de trades + calculo de performance
├── logger.py          → Sistema de log (arquivo + console)
├── test_strategy.py   → 15 testes unitarios (mocks, sem MT5 real)
├── pyproject.toml     → Empacotamento pip (CLI: mt5bot)
├── __init__.py        → Versao do pacote
├── __main__.py        → Suporte a python -m mt5bot
├── state.json         → Estado atual da maquina (gerado em runtime)
├── trades.json        → Historico de operacoes (gerado em runtime)
└── logs/bot_YYYYMMDD.log → Logs diarios
```

---

## 3. Fluxo de execucao (do inicio ao fim)

```
[Usuario executa: mt5bot]
        │
        ▼
main.main()
        │
        ├── Flags CLI (--help, --version, --report, --dashboard, --quick)
        │
        ▼
_show_startup_menu()  →  Opcao 1: Iniciar direto
                         Opcao 2: tui.run_tui() (config terminal)
                         Opcao 3: dashboard.open_config() (config web)
                         Opcao 4: tracker.print_report() ou dashboard.open_report()
        │
        ▼
tui.connect_mt5_tui()  →  mt5.initialize() ou mt5.initialize(login, password, server)
        │
        ▼
run_bot()
        │
        ├── Registra signal handlers (SIGINT, SIGTERM)
        ├── Valida conexao MT5 (account_info)
        ├── Valida simbolos no broker (_validate_symbols_on_broker)
        ├── strategy.initialize_symbol_states() (carrega persistencia + valida MT5)
        │
        ▼
    LOOP PRINCIPAL (while not _shutdown_requested):
        │
        ├── Para cada symbol em config.SYMBOLS:
        │       │
        │       ├── Verifica mercado aberto (trade_mode)
        │       ├── Busca 100 candles H1: mt5.copy_rates_from_pos()
        │       ├── Extrai candle fechado: rates[-2] (rates[-1] esta formando)
        │       ├── Verifica se e candle NOVO (compara timestamp)
        │       │
        │       └── strategy.evaluate(symbol, candle_fechado, all_rates)
        │               │
        │               ├── Calcula EMA9, EMA21
        │               ├── Aplica filtros (flat, EMA21)
        │               └── Roteia para handler do estado atual
        │
        ├── sleep(SCAN_INTERVAL_SECONDS)
        │
        └── Em caso de excecao: log + sleep(RETRY_INTERVAL_SECONDS)

    [Ctrl+C]
        │
        ▼
_cancel_pending_orders()  →  Cancela todas as ordens stop do bot
mt5.shutdown()
tracker.print_report()    →  Mostra resumo de performance
```

---

## 4. Maquina de estados (strategy.py)

### Estados

| Estado | Significado | O que o bot faz |
|--------|-------------|-----------------|
| `SCANNING` | Aguardando sinal | Calcula EMA9, verifica se virou |
| `SIGNAL_READY` | Ordem stop pendente | Monitora se ordem foi preenchida ou se deve cancelar |
| `IN_POSITION` | Posicao aberta | Gerencia saida parcial e saida final |
| `WATCHING_92` | Apos lucro, observando | Espera pullback a EMA9 para Setup 9.2 |

### Transicoes

```
SCANNING
    │
    │ [EMA9 virou + filtros OK]
    ▼
SIGNAL_READY ──[EMA9 virou contra]──→ SCANNING (cancela ordem)
    │
    │ [ordem preenchida pelo mercado]
    ▼
IN_POSITION ──[EMA9 virou contra + prejuizo]──→ SCANNING
    │
    │ [EMA9 virou contra + lucro + 9.2 ativo]
    ▼
WATCHING_92 ──[timeout ou EMA contra 2+ candles]──→ SCANNING
    │
    │ [pullback a EMA9 + direcao favoravel]
    ▼
SIGNAL_READY (Setup 9.2)
```

### SymbolState — dados de cada simbolo

```python
class SymbolState:
    symbol                  # "HK50", "EURUSD", etc.
    state                   # State enum (SCANNING, SIGNAL_READY, IN_POSITION, WATCHING_92)
    pending_order_ticket    # Ticket da ordem stop pendente (int ou None)
    position_ticket         # Ticket da posicao aberta (int ou None)
    position_type           # TradeSide.BUY ou TradeSide.SELL
    candle_referencia       # Tuple (time, open, high, low, close, tick_vol, spread, real_vol)
    entry_price             # Preco de entrada da ordem stop
    sl_price                # Preco do stop loss
    partial_exit_done       # True se ja fez saida parcial de 50%
    watching_92_candles     # Contador de candles em WATCHING_92
    setup_type              # "9.1" ou "9.2"
    exit_profit             # True se ultima saida foi com lucro
```

---

## 5. Logica de entrada (Setup 9.1)

### Condicoes para COMPRA
```
1. EMA9 slope[-2→-1] era NEGATIVO (apontando para baixo)
2. EMA9 slope[-1→0] agora e POSITIVO (virou para cima)
3. Close do candle > EMA21 (filtro de tendencia)
4. EMA9 NAO esta flat (moveu mais de 5 ticks nos ultimos 5 candles)
```

### Condicoes para VENDA
```
1. EMA9 slope[-2→-1] era POSITIVO (apontando para cima)
2. EMA9 slope[-1→0] agora e NEGATIVO (virou para baixo)
3. Close do candle < EMA21 (filtro de tendencia)
4. EMA9 NAO esta flat
```

### Onde entra a ordem
```
COMPRA: BUY STOP em high do candle de referencia + 1 tick
VENDA:  SELL STOP em low do candle de referencia - 1 tick
```

### Onde fica o stop loss
```
COMPRA: low do candle de referencia - 1 tick (ajustado por ATR se volatil)
VENDA:  high do candle de referencia + 1 tick (ajustado por ATR se volatil)
```

---

## 6. Logica de entrada (Setup 9.2)

### Pre-condicao
- Um Setup 9.1 saiu com LUCRO (close > entry para BUY, close < entry para SELL)
- `config.SETUP_92_ENABLED = True`

### Condicoes
```
1. Estado: WATCHING_92 (apos saida com lucro)
2. EMA9 retomou/manteve direcao favoravel (apontando para cima para BUY)
3. Candle atual TOCOU a EMA9 (pullback):
   - Para BUY: low <= ema9_value
   - Para SELL: high >= ema9_value
4. Filtro EMA21 ainda OK
5. Nao ultrapassou SETUP_92_MAX_CANDLES_WATCHING (10)
6. EMA9 nao virou contra por >= SETUP_92_EMA_AGAINST_LIMIT (2) candles
```

### Entrada
Mesma logica do 9.1: ordem stop 1 tick alem do candle que fez pullback.

---

## 7. Logica de saida

### Saida parcial (50% no alvo)
```
Condicoes:
- PARTIAL_EXIT_ENABLED = True
- partial_exit_done = False
- candle_referencia e entry_price existem

Alvo:
  amplitude = high - low do candle de referencia
  target_mult = PARTIAL_EXIT_TARGET * adaptive_multiplier

  BUY: target = entry_price + (amplitude * target_mult)
  SELL: target = entry_price - (amplitude * target_mult)

Se close atingiu target E volume >= volume_to_close:
  → fecha 50% do volume
  → partial_exit_done = True
```

### Saida total (EMA9 virou contra)
```
BUY: se EMA9 virou para baixo → fecha tudo
SELL: se EMA9 virou para cima → fecha tudo
```

### Apos saida total
Se saiu com LUCRO e 9.2 ativo:
  → estado = WATCHING_92

Se saiu com PREJUIZO:
  → estado = SCANNING

---

## 8. Alvo Adaptativo (indicators.adaptive_target_multiplier)

### Objetivo
Evitar que o bot busque alvos irreais quando o mercado esta pagando pouco, ou que trave lucro cedo demais quando o mercado esta generoso.

### Calculo
1. Pegar amplitudes (high-low) dos ultimos 20 candles fechados
2. Calcular MEDIANA dessas amplitudes
3. Pegar amplitude do candle de referencia (rates[-2], o ultimo fechado)
4. ratio = amplitude_referencia / mediana

5. Converter ratio em multiplicador:
   ratio > 1.5  → mult = 0.6  (candle muito grande, alvo reduzido)
   ratio > 1.2  → mult = 0.8
   ratio ~ 1.0  → mult = 1.0  (normal)
   ratio < 0.8  → mult = 1.1
   ratio < 0.6  → mult = 1.2  (candle pequeno, alvo aumentado)

### Aplicacao
target final = amplitude * PARTIAL_EXIT_TARGET * multiplicador

---

## 9. ATR Dinamico (stop adaptativo)

### Objetivo
Alargar o stop loss quando a volatilidade esta acima do normal, para nao ser "estopado" por ruido.

### Calculo
1. Calcular ATR(14) sobre todos os rates
2. ATR_current = ultimo valor ATR
3. ATR_avg = media dos ultimos 50 valores ATR
4. ratio = ATR_current / ATR_avg

5. Se ratio > ATR_HIGH_VOL_THRESHOLD (1.5):
   distancia_original = |entry - sl|
   nova_distancia = distancia_original * ratio * ATR_DAMPING_FACTOR (0.8)
   sl_ajustado = entry -/+ nova_distancia

---

## 10. EMA — Como e calculada

def ema(values, period):
    alpha = 2.0 / (period + 1.0)

    # Primeiros 'period' valores: usa SMA como seed
    ema_value = media(values[0:period])
    result = values[0:period]  # Primeiros valores sao raw

    # A partir do periodo: suavizacao exponencial
    for v in values[period:]:
        ema_value = alpha * v + (1 - alpha) * ema_value
        result.append(ema_value)

    return result  # Mesmo tamanho que input

### Deteccao de virada
slope_current = ema9[-1] - ema9[-2]    # Slope do candle atual
slope_previous = ema9[-2] - ema9[-3]   # Slope do candle anterior

virou_para_cima = slope_previous < 0 AND slope_current > 0
virou_para_baixo = slope_previous > 0 AND slope_current < 0

### Deteccao de flat
flat = |ema9[-1] - ema9[-5]| < FLAT_THRESHOLD_TICKS * tick_size

---

## 11. Executor — Como ordens sao enviadas ao MT5

### Tipos de ordem usados

| Situacao | Acao MT5 | Tipo |
|----------|----------|------|
| Colocar entrada | TRADE_ACTION_PENDING | ORDER_TYPE_BUY_STOP ou SELL_STOP |
| Cancelar entrada | TRADE_ACTION_REMOVE | — |
| Fechar parcial | TRADE_ACTION_DEAL | Oposto da posicao |
| Fechar total | TRADE_ACTION_DEAL | Oposto da posicao |

### Protecoes implementadas

1. *Volume normalizado*: _normalize_volume() arredonda para volume_step do broker
2. *Filling dinamico*: _get_filling_type() consulta symbol_info.filling_mode
3. *Null check em tick*: Verifica se symbol_info_tick() retornou dados
4. *Null check em positions*: Verifica antes de acessar [0].volume
5. *Preco formatado*: _format_price() arredonda para symbol.digits

### Magic Number
Todas as ordens do bot usam config.MAGIC = 20260731. Isso permite:
- Filtrar ordens/posicoes do bot vs manuais
- Identificar trades do bot no historico do MT5

---

## 12. Persistencia (state.json)

### Quando salva
A cada transicao de estado (signal detectado, ordem preenchida, saida parcial, saida total, cancelamento).

### Estrutura do JSON
{
  "HK50": {
    "state": "IN_POSITION",
    "pending_order_ticket": null,
    "position_ticket": 67890,
    "position_type": "BUY",
    "candle_referencia": [1722434400, 18500.0, 18560.0, 18480.0, 18540.0, 100, 2, 50],
    "entry_price": 18561.0,
    "sl_price": 18479.0,
    "partial_exit_done": true,
    "watching_92_candles": 0,
    "setup_type": "9.1",
    "exit_profit": null
  }
}

### No startup
1. Tenta carregar state.json
2. Se existe: aplica estados aos SymbolState objects
3. Valida contra MT5 (ordem/posicao ainda existe?)
4. Se nao existe no MT5: reseta para SCANNING

---

## 13. Tracker (trades.json)

### Quando registra
- record_entry(): quando ordem stop e preenchida (IN_POSITION)
- record_partial_exit(): quando saida parcial e executada
- record_exit(): quando posicao e fechada totalmente

### Metricas calculadas
- Win Rate (% vitorias)
- Profit Factor (lucro total / perda total)
- Max Drawdown (maior sequencia de perdas acumuladas)
- Media vitoria/derrota em pips
- Performance por simbolo e por setup
- Sequencias consecutivas de vitorias/derrotas

### Limitacao conhecida
O tracker registra P&L em *pips* (diferenca de preco), nao em dinheiro. Cada instrumento tem pip value diferente que depende da moeda da conta e do tamanho do contrato.

---

## 14. Interface Web (dashboard.py)

### Implementacao
- Servidor HTTP built-in do Python (http.server)
- Sem dependencias externas (HTML/CSS inline)
- Porta dinamica: tenta 5555, incrementa se ocupada
- Thread daemon: encerra com o processo principal

### Rotas

| Rota | Metodo | Funcao |
|------|--------|--------|
| / ou /config | GET | Formulario de configuracao |
| /config/save | POST | Salva config e sinaliza para o terminal |
| /report | GET | Pagina de relatorio de performance |
| /api/summary | GET | JSON com metricas (para integracao) |

### Fluxo de configuracao via web
1. main.py chama dashboard.open_config()
2. Servidor HTTP inicia em thread daemon
3. Navegador abre automaticamente (webbrowser.open)
4. Terminal bloqueia em _config_ready.wait(timeout=300)
5. Usuario preenche formulario e clica "Salvar"
6. POST /config/save → parse params → apply_config → _config_ready.set()
7. Terminal desbloqueia, servidor encerra
8. Bot inicia com configuracao aplicada

---

## 15. Candle — Estrutura de dados

Cada candle retornado por mt5.copy_rates_from_pos() e uma tuple:

Indice  Campo       Exemplo         Uso no bot
[0]     time        1722434400      Timestamp UTC (epoch seconds)
[1]     open        18500.0         Preco de abertura
[2]     high        18560.0         Maxima do candle ← usado em entry BUY, SL SELL
[3]     low         18480.0         Minima do candle ← usado em entry SELL, SL BUY
[4]     close       18540.0         Preco de fechamento ← usado em EMA, filtros
[5]     tick_volume 1523            Volume de ticks
[6]     spread      2               Spread em pontos
[7]     real_volume 0               Volume real (nem todo broker fornece)

### Importante
- rates[-1] = candle FORMANDO (incompleto, high/low podem mudar)
- rates[-2] = ultimo candle FECHADO (completo, usado para sinais)
- O bot SEMPRE usa rates[-2] como candle_fechado para avaliacao

---

## 16. Configuracao (config.py) — Todos os parametros

# Simbolos
AVAILABLE_SYMBOLS = ["HK50", "EURUSD", "US500"]  # Opcoes no menu
SYMBOLS = []                                       # Preenchido no startup
TIMEFRAME = mt5.TIMEFRAME_H1                       # Sempre H1

# EMAs
EMA_PERIOD = 9                   # EMA rapida (sinal)
EMA_FILTER_PERIOD = 21           # EMA lenta (filtro de tendencia)

# Volume
VOLUME_INITIAL = 0.01            # Lote por operacao

# Saida parcial
PARTIAL_EXIT_ENABLED = True      # Ativar saida parcial
PARTIAL_EXIT_PERCENT = 0.50      # 50% do volume
PARTIAL_EXIT_TARGET = 1.00       # Alvo = 100% da amplitude

# Alvo adaptativo
ADAPTIVE_TARGET_ENABLED = True   # Ajusta alvo pela volatilidade
ADAPTIVE_TARGET_LOOKBACK = 20    # Candles para mediana

# Filtro flat
FLAT_FILTER_ENABLED = True       # Ignora sinais em mercado lateral
FLAT_THRESHOLD_TICKS = 5         # Limiar de movimento minimo

# Offsets
TICK_OFFSET = 1                  # 1 tick alem do candle para entry/SL

# Intervalos
SCAN_INTERVAL_SECONDS = 10       # Tempo entre verificacoes
RETRY_INTERVAL_SECONDS = 30      # Tempo de espera apos erro

# Dados
RATES_COUNT = 100                # Candles historicos para calculos

# Identificacao
MAGIC = 20260731                 # Numero magico das ordens do bot

# ATR
ATR_PERIOD = 14                  # Periodo do ATR
ATR_AVG_PERIOD = 50              # Candles para media do ATR
ATR_HIGH_VOL_THRESHOLD = 1.5    # Ratio para alargar stop
ATR_DAMPING_FACTOR = 0.8        # Amortecimento do alargamento

# Setup 9.2
SETUP_92_ENABLED = True          # Ativar segundo setup
SETUP_92_MAX_CANDLES_WATCHING = 10  # Timeout do watching
SETUP_92_EMA_AGAINST_LIMIT = 2     # Candles contra para cancelar

# Persistencia
STATE_FILE = "state.json"        # Arquivo de estado

---

## 17. Dependencias

### Runtime
MetaTrader5>=5.0.45    # API oficial MT5 (so Windows)
pytz>=2023.3           # Timezone UTC

### Embutido (stdlib Python)
http.server            # Dashboard web
threading              # Servidor em background
json                   # Persistencia
signal                 # Graceful shutdown
getpass                # Senha oculta
webbrowser             # Abrir dashboard
collections.namedtuple # Candle struct

### Desenvolvimento
pytest>=7.0            # Se quiser rodar testes com pytest

---

## 18. Testes (test_strategy.py)

### Como rodar
python test_strategy.py

### Como funciona
- Substitui MetaTrader5 por um mock em sys.modules ANTES dos imports
- Mock simula: initialize, symbol_info, order_send, positions_get, orders_get
- Desabilita persistencia real (save_states = lambda x: None)
- Cada teste reseta o estado e configura mocks especificos

### Cenarios cobertos (15 testes)

| # | Teste | O que valida |
|---|-------|-------------|
| 1 | scanning_to_signal_ready_buy | EMA9 vira → BUY STOP colocado |
| 2 | scanning_to_signal_ready_sell | EMA9 vira → SELL STOP colocado |
| 3 | signal_ready_cancel | EMA9 contra → ordem cancelada |
| 4 | signal_ready_to_in_position | Ordem preenchida → posicao aberta |
| 5 | in_position_partial_exit | Alvo atingido → fecha 50% |
| 6 | in_position_full_exit | EMA9 contra + prejuizo → SCANNING |
| 7 | exit_profit_to_watching | EMA9 contra + lucro → WATCHING_92 |
| 8 | watching_timeout | 10+ candles sem sinal → SCANNING |
| 9 | watching_pullback | Pullback detectado → SIGNAL_READY 9.2 |
| 10 | atr_ratio_calculation | ATR calcula corretamente |
| 11 | atr_stop_adjustment | Stop alargado quando ATR alto |
| 12 | volume_normalization | Volume arredondado para step |
| 13 | close_full_trade_side | Aceita TradeSide enum sem crash |
| 14 | close_full_empty | Retorna None se posicao nao existe |
| 15 | adaptive_target | Multiplicador correto por cenario |

### Como gerar dados de teste
# Rates onde EMA9 vira PARA CIMA no ultimo candle:
# 29 candles descendo + 1 candle spike para cima
rates = [(i, c, c+0.02, c-0.02, c=1.2-i*0.005) for i in range(29)]
rates.append((29, 1.10, 1.25, 1.05, 1.20))  # Spike

# Rates onde EMA9 vira PARA BAIXO no ultimo candle:
# 29 candles subindo + 1 candle queda forte
rates = [(i, c, c+0.02, c-0.02, c=1.0+i*0.005) for i in range(29)]
rates.append((29, 1.10, 1.15, 0.90, 0.92))  # Queda

---

## 19. Bugs conhecidos e corrigidos

| Bug | Arquivo | Causa | Correcao |
|-----|---------|-------|----------|
| Type mismatch no fechamento | executor.py | TradeSide enum vs mt5.ORDER_TYPE | Comparacao por .value |
| Crash em positions_get None | executor.py | mt5.positions_get() retorna None | Check if not positions |
| Volume rejeitado pelo broker | executor.py | 0.01 * 0.50 = 0.005 invalido | _normalize_volume() com volume_step |
| symbol_info_tick None | executor.py | Mercado fechado → tick None | Null check antes de .bid`/.ask` |
| Alvo adaptativo candle errado | indicators.py | Usava rates[-1] (formando) | Corrigido para rates[-2] (fechado) |
| partial_exit_done no 9.2 | strategy.py | Flag nao resetada para nova entrada | Reset em _place_entry_order() |
| Dashboard crash em input invalido | dashboard.py | int("abc") sem try/except | try/except + validacao min/max |
| Logger sem permissao | logger.py | os.makedirs em dir protegido | Fallback para console-only |
| Porta fixa no dashboard | dashboard.py | Porta 5555 ocupada → bind error | _find_free_port() com retry |

---

## 20. Reconnect Automatico (main.py)

### Como funciona
A cada iteracao do loop principal, ANTES de consultar dados, o bot verifica a conexao:

_ensure_connected():
    1. Chama mt5.account_info()
    2. Se retornou dados → conexao OK, retorna True
    3. Se retornou None → conexao perdida:
       a. mt5.shutdown()
       b. Espera 2 segundos
       c. mt5.initialize() (reconecta)
       d. Reativa simbolos no Market Watch
       e. Retorna True se sucesso, False se falhou

### Backoff exponencial
Se a reconexao falhar repetidamente, o tempo de espera aumenta:
- 1a falha: espera 30s
- 2a falha: espera 60s
- 3a falha: espera 90s
- Maximo: 120s

Ao reconectar com sucesso, o contador reseta para 0.

### O que NAO se perde ao reconectar
- Estado da maquina (persistido em state.json)
- Ordens pendentes (vivem no servidor do broker)
- Posicoes abertas (vivem no servidor do broker)
- Historico de trades (trades.json)

---

## 21. P&L em Dinheiro (tracker.py)

### Problema
Cada instrumento tem um "pip value" diferente. 1 pip no EURUSD ≠ 1 ponto no HK50 em termos de dinheiro.

### Formula
pnl_money = (pnl_pips / tick_size) * tick_value * volume

Onde:
- pnl_pips = diferenca de preco (entry vs exit)
- tick_size = menor variacao do preco (symbol_info.trade_tick_size)
- tick_value = valor monetario de 1 tick para 1 lote (symbol_info.trade_tick_value)
- volume = tamanho da posicao em lotes

### Exemplo pratico
EURUSD: tick_size=0.00001, tick_value=$1.00 por lote
  Comprou 0.01 lote em 1.08500, vendeu em 1.08650
  pnl_pips = 0.00150
  pnl_ticks = 0.00150 / 0.00001 = 150 ticks
  pnl_money = 150 * $1.00 * 0.01 = $1.50

HK50: tick_size=1.0, tick_value=$1.00 por lote
  Comprou 0.01 lote em 18500, vendeu em 18570
  pnl_pips = 70
  pnl_ticks = 70 / 1.0 = 70 ticks
  pnl_money = 70 * $1.00 * 0.01 = $0.70

### Fallback
Se MT5 nao estiver conectado no momento do calculo (ex: relatorio offline), pnl_money fica como None e o relatorio mostra pips.

---

## 22. Limitacoes e dividas tecnicas

1. *Sem backtest* — Nao ha mecanismo para rodar a estrategia em dados historicos.
2. *Sem rate limiting* — Se MT5 API throttlear, nao ha backoff exponencial.
3. *Single process* — Nao usa multiprocessing. Um simbolo lento bloqueia os outros.
4. *Windows only* — MetaTrader5 package so funciona no Windows.
5. *P&L money offline* — Se MT5 nao conectado, relatorio mostra pips (sem conversao).

---

## 23. Como corrigir / estender

### Adicionar novo ativo
1. Editar config.py → AVAILABLE_SYMBOLS.append("USDJPY")
2. Testar se o broker fornece dados para o ativo
3. Verificar volume_step e volume_min do ativo

### Mudar timeframe
1. Editar config.py → TIMEFRAME = mt5.TIMEFRAME_M15 (ex: 15 minutos)
2. Ajustar SCAN_INTERVAL_SECONDS proporcionalmente
3. Considerar ajustar FLAT_THRESHOLD_TICKS (timeframes menores sao mais ruidosos)

### Adicionar novo setup (ex: 9.3)
1. Criar novo estado em State enum (strategy.py)
2. Adicionar handler _handle_new_state()
3. Definir transicoes de/para o novo estado
4. Adicionar condicoes de entrada em indicators.py
5. Registrar parametros em config.py
6. Atualizar persistence.py para salvar campos novos
7. Adicionar testes em test_strategy.py

### Adicionar reconnect MT5
1. Em main.py, no bloco except do loop principal:
   
   if not mt5.account_info():
       logger.warning("Conexao MT5 perdida. Tentando reconectar...")
       mt5.shutdown()
       time.sleep(5)
       if not mt5.initialize():
           continue  # Tenta novamente no proximo ciclo
   

### Adicionar P&L em dinheiro
1. Em tracker.py, na funcao record_exit():
   
   # Obter pip value do simbolo
   symbol_info = mt5.symbol_info(trade["symbol"])
   contract_size = symbol_info.trade_contract_size
   pip_value = contract_size * symbol_info.point * trade["volume"]
   trade["pnl_money"] = pnl_pips / symbol_info.point * pip_value
   

---

## 24. Convencoes do codigo

- *Nomes em ingles* para codigo, *portugues* para logs e mensagens ao usuario
- *Sem type hints* (mantido simples propositalmente)
- *Sem classes complexas* — funcoes + dicionarios + enums
- *Logger global* — importar logger e usar logger.info(), logger.error()
- *Config global* — importar config e acessar config.VOLUME_INITIAL
- *State mutavel* — symbol_states[symbol] e modificado in-place
- *Persistencia explicita* — _save_states() chamado apos cada transicao

---

## 25. Glossario

| Termo | Significado |
|-------|-------------|
| Setup 9.1 | Entrada na virada da EMA9 |
| Setup 9.2 | Entrada no primeiro pullback apos lucro do 9.1 |
| EMA9 | Media Movel Exponencial de 9 periodos |
| EMA21 | Media Movel Exponencial de 21 periodos |
| ATR | Average True Range — mede volatilidade |
| Candle de referencia | O candle que gerou o sinal (determina entry e SL) |
| Amplitude | high - low do candle |
| Virada (virou) | Slope da EMA mudou de sinal (positivo→negativo ou vice-versa) |
| Flat | EMA9 quase sem movimento (mercado lateral) |
| Pullback | Retorno temporario do preco ate a EMA |
| Stop loss (SL) | Preco de saida com prejuizo maximo |
| Saida parcial | Fechar 50% no alvo para travar lucro |
| Magic number | ID numerico que identifica ordens do bot vs manuais |
| Tick | Menor variacao de preco possivel para o ativo |
| Pip | Unidade de medida de variacao (geralmente = tick) |
| Volume step | Incremento minimo de lote aceito pelo broker |
| Filling type | Como a ordem e preenchida (FOK, IOC, RETURN) |