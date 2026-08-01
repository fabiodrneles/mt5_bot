# Design: Bot MT5 — Setup 9.1 (EMA9) com Python

*Data:* 2026-07-31
*Status:* Aprovado (pending user review)
*Autor:* Usuario + opencode

---

## 1. Objetivo

Automatizar o Setup 9.1 (Larry Williams / Palex) no MetaTrader 5 via Python, operando HK50 e EURUSD em timeframe H1, com a menor exposicao possivel (lote 0.01), visando perdas minimas enquanto testa.

## 2. Estrategia — Setup 9.1

### 2.1 Configuracao do grafico

- *Indicador principal:* EMA9 (Media Movel Exponencial de 9 periodos) plotada sobre os precos
- *Indicador de filtro:* EMA21 (Media Movel Exponencial de 21 periodos)
- *Timeframe:* H1 (1 hora)

### 2.2 Logica operacional

O setup captura o momento em que a EMA9 muda de direcao (virada de inclinacao).

### 2.3 Setup 9.1 de Compra

1. *Condicao previa:* EMA9 apontando para baixo (slope negativo)
2. *Gatilho:* Candle H1 fecha e faz a EMA9 virar para cima (slope passa de negativo para positivo). Esse candle = Candle de Referencia.
3. *Entrada:* Ordem stop de compra pendurada 1 tick acima da maxima do candle de referencia
4. *Stop loss:* 1 tick abaixo da minima do candle de referencia
5. *Acionamento:* Se a ordem stop for acionada no(s) candle(s) seguinte(s), posicao entra em execucao
6. *Anulacao:* A qualquer candle fechado apos o sinal, se a EMA9 voltar a virar para baixo e a ordem ainda nao foi acionada, o setup e cancelado — ordem removida. Nao ha limite de candles para aguardar acionamento; a ordem permanece pendurada enquanto a EMA9 mantiver a direcao favoravel.

### 2.4 Setup 9.1 de Venda (simetrico)

1. *Condicao previa:* EMA9 apontando para cima (slope positivo)
2. *Gatilho:* Candle H1 fecha e faz a EMA9 virar para baixo (slope passa de positivo para negativo). Candle de Referencia.
3. *Entrada:* Ordem stop de venda 1 tick abaixo da minima do candle de referencia
4. *Stop loss:* 1 tick acima da maxima do candle de referencia
5. *Acionamento:* Ordem stop acionada nos candles seguintes
6. *Anulacao:* A qualquer candle fechado apos o sinal, se a EMA9 voltar a virar para cima e a ordem ainda nao foi acionada, o setup e cancelado — ordem removida. Nao ha limite de candles para aguardar acionamento; a ordem permanece pendurada enquanto a EMA9 mantiver a direcao favoravel.

### 2.5 Conducao e saida

- *Saida parcial (50%):* Ao alcancar 100% da amplitude do candle de referencia como alvo, fecha 50% do lote a mercado
- *Saida final:* Quando a EMA9 virar contra a posicao (fecha candle e slope inverte), fecha o restante a mercado
- *Sem take profit fixo no restante* — conduz pela EMA9 ate ela virar

### 2.6 Filtros

| Filtro | Estado | Logica |
|---|---|---|
| EMA21 (obrigatorio) | Sempre ligado | Compra permitida apenas se close > EMA21; venda apenas se close < EMA21 |
| EMA9 flat (opcional) | Ligado por padrao, ajustavel | Se \|ema9[-1] - ema9[-5]\| < threshold, sinal ignorado (EMA andando de lado) |
| Saida parcial no alvo 100% | Ligado por padrao | Fecha 50% no alvo, conduz resto pela EMA9 |

## 3. Arquitetura

### 3.1 Estrutura de arquivos

mt5_bot/
  config.py       # simbolos, timeframe, parametros EMA, lote, thresholds
  indicators.py   # calculo EMA9, EMA21, deteccao de virada e flat
  strategy.py     # maquina de estados do setup 9.1
  executor.py     # envio/cancelamento de ordens stop, monitoracao de posicao
  logger.py       # log em arquivo + console
  main.py         # loop principal

### 3.2 Loop principal (main.py)

1. Inicializa conexao MT5 (mt5.initialize())
2. Carrega configuracao
3. Para cada simbolo, determina estado inicial (scanning, ou assume posicao/ordem existente)
4. Loop infinito:
   - A cada 10 segundos, verifica se um candle H1 fechou
   - Se fechou, para cada simbolo:
     - Busca 100 candles H1 (mt5.copy_rates)
     - Recalcula EMA9 e EMA21
     - Chama strategy.evaluate(symbol, candle_fechado, dados)
     - Strategy aplica transicoes de estado e chama executor conforme necessario
5. Trata erros de conexao com retry em 30s

### 3.3 Maquina de estados (strategy.py)

Cada simbolo tem estado independente:

mermaid
stateDiagram-v2
    direction TB

    [*] --> SCANNING

    SCANNING --> SIGNAL_READY : EMA9 vira\n+ filtros OK
    SIGNAL_READY --> IN_POSITION : Ordem stop acionada
    SIGNAL_READY --> SCANNING : EMA9 volta contra\n(anulacao, remove ordem)
    IN_POSITION --> SCANNING : EMA9 vira contra\n(fecha posicao a mercado)

    SCANNING : Procurando sinal\nEMA9 nao virou
    SIGNAL_READY : Ordem stop pendurada\nAguarda acionamento
    IN_POSITION : Posicao aberta\nConduz pela EMA9

### 3.4 Indicadores (indicators.py)

def ema(values, period):
    alpha = 2 / (period + 1)
    result = [values[0]]
    for v in values[1:]:
        result.append(alpha * v + (1 - alpha) * result[-1])
    return result

# Deteccao de virada:
slope_current  = ema9[-1] - ema9[-2]
slope_previous = ema9[-2] - ema9[-3]
virou_para_cima  = slope_previous < 0 and slope_current > 0
virou_para_baixo = slope_previous > 0 and slope_current < 0

# Filtro EMA21:
filtro_compra = close > ema21[-1]
filtro_venda  = close < ema21[-1]

# Filtro flat:
ema9_flat = abs(ema9[-1] - ema9[-5]) < (flat_threshold * tick_size)

### 3.5 Executor (executor.py)

Operacoes suportadas:
- place_buy_stop(symbol, entrada, sl, volume) — ordem pendente buy stop
- place_sell_stop(symbol, entrada, sl, volume) — ordem pendente sell stop
- cancel_order(ticket) — remove ordem pendente (anulacao)
- close_partial(ticket, volume) — fecha 50% no alvo
- close_all(ticket) — fecha posicao inteira a mercado (saida pela EMA9)

Parametros de offset (1 tick) obtidos de mt5.symbol_info(symbol).point.

Volume inicial: 0.01 (lote minimo) para ambos os simbolos.

### 3.6 Configuracao (config.py)

SYMBOLS = ["HK50", "EURUSD"]
TIMEFRAME = mt5.TIMEFRAME_H1
EMA_PERIOD = 9
EMA_FILTER_PERIOD = 21
VOLUME_INITIAL = 0.01
PARTIAL_EXIT_ENABLED = True
PARTIAL_EXIT_PERCENT = 0.50       # 50% no alvo
PARTIAL_EXIT_TARGET = 1.00         # 100% da amplitude do candle ref
FLAT_FILTER_ENABLED = True
FLAT_THRESHOLD = 5                  # 5 ticks (ajustavel)
TICK_OFFSET = 1                     # 1 tick acima/abaixo para entrada e SL
SCAN_INTERVAL_SECONDS = 10
RETRY_INTERVAL_SECONDS = 30

## 4. Gestao de risco

- *1 posicao por simbolo* — nao acumula
- *Lote minimo (0.01)* — menor exposicao possivel
- *Stop loss sempre definido* — 1 tick alem do candle de referencia
- *Saida parcial trava 50% do lucro* no alvo de 100% da amplitude
- *Nunca opera sem filtro EMA21* — apenas sinais a favor da tendencia maior

## 5. Tratamento de erros

| Cenario | Acao |
|---|---|
| MT5 desconectado | Log + retry em 30s |
| Ordem rejeitada (retcode != 10009) | Log detalhado com motivo + nao tenta reenviar automaticamente |
| Dados insuficientes para EMA | Aguarda mais candles antes de operar |
| Posicao/ordem ja existe no arranque | Assume estado correspondente (IN_POSITION ou SIGNAL_READY) |
| Sinal duplicado (mesmo candle de ref) | Ignora — estado ja em SIGNAL_READY |

## 6. Logging

- Arquivo mt5_bot/logs/bot_YYYYMMDD.log
- Niveis: INFO (decisoes), WARNING (anulacoes, retries), ERROR (falhas)
- Cada decisao logada: simbolo, estado, acao, preco, ticket, motivo

## 7. Pre-requisitos

- Python 3.13+ (instalado)
- Pacote MetaTrader5 (a instalar via pip install MetaTrader5)
- MetaTrader 5 aberto e logado na conta do broker
- Simbolos HK50 e EURUSD disponiveis no broker

## 8. Fora de escopo (futuro)

- Dashboard web para monitoracao
- Backtesting historico
- Multiplas posicoes por simbolo
- Outros setups (9.2, ORB, etc.)
- Notificacoes push/Telegram