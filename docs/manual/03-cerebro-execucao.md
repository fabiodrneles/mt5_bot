# 3. Cérebro e motor de execução

## 3.1 Protocolo do trabalhador

`interfaces/brain_worker.py` lê uma linha JSON por vez do stdin (`main`) e responde uma linha no stdout (`process_payload`):

| Entrada | Resposta |
|---|---|
| `{"ping": true}` | `{"pong": true}` |
| `{"symbol": "HK50", "timeframe": "H4", "action": "scan"}` | `{"symbol", "status": "processed", "state_text", "telemetry"}` |
| ativo inexistente / MT5 fora | `{"error": "..."}` (o Maestro encerra o trabalhador) |

Para depurar, o mesmo protocolo funciona no terminal: `echo '{"symbol":"HK50","timeframe":"H4","action":"scan"}' | python -m interfaces.brain_worker`.

## 3.2 Candles fechados: evitando o *look-ahead bias*

O trabalhador busca **400 candles a partir da posição 1** (`copy_rates_from_pos(symbol, tf, 1, 400)`); a posição 0 é o candle ainda em formação. Isso implementa uma regra fundamental de pesquisa e operação: **toda decisão usa só informação disponível no momento da decisão**. Avaliar o candle aberto produz sinais que aparecem e somem dentro do mesmo período (o máximo e o fechamento ainda mudam). É o equivalente operacional do *look-ahead bias* de backtests, que infla resultados ao usar dados do futuro [Bailey et al. 2014; López de Prado 2018].

```python
# Listagem 3.1 — interfaces/brain_worker.py
            start_pos = 0 if data.get("action") == "study" else 1
            # 400 velas: SMA200/EMA50 das rotas quant precisam de aquecimento
            # (com 200 a SMA200 tem um unico valor valido).
            rates = mt5.copy_rates_from_pos(symbol, tf, start_pos, 400)
```

Por que 400? A SMA200 precisa de 200 candles para ter **um** valor válido, e as médias exponenciais precisam de "aquecimento": com $\alpha = 2/(n+1)$, o peso do valor inicial após $k$ passos é $(1-\alpha)^k$, que para a EMA50 cai abaixo de 1% depois de cerca de 115 candles. Com 400 candles, a SMA200 tem histórico e as EMAs convergiram. O modo `study` (simulação) usa a posição 0 de propósito, porque acompanha SL e alvo virtuais no candle corrente.

## 3.3 Máquina de estados *stateless*

`mt5bot/execution/execution_manager.py:manage_cycle` é uma máquina de estados cujo estado **não fica guardado**: ele é deduzido do MT5 a cada ciclo.

```
                    ┌─ rota quant? ─ sim ─▶ quant_manager.quant_cycle (§3.5)
manage_cycle(df) ───┤
                    └─ não ─▶ reconcilia histórico
                              ├─ posição do robô? ──▶ _manage_position (gestão)
                              ├─ ordem pendente? ───▶ _manage_pending_order
                              └─ nada ─▶ travas (§3.4) ─▶ _scan_and_execute
```

O despacho em código é direto; note que nada é lido de uma variável de estado do próprio programa, só do MT5:

```python
# Listagem 3.2 — mt5bot/execution/execution_manager.py
    # Rotas quant (setups validados fora da amostra) tem caminho proprio.
    from mt5bot.execution import quant_manager
    route = quant_manager.get_route(symbol, timeframe_name)
    if route:
        return quant_manager.quant_cycle(symbol, df, timeframe_name, route)

    # 1. Sincronizar historico: se o usario fechou algo manualmente, registrar saida.
    _reconcile_closed_trades(symbol, df)

    # 2. Obter estado atual no MT5 (posicoes quant sao geridas so pela rota quant)
    positions = [p for p in (mt5.positions_get(symbol=symbol) or [])
                 if not quant_manager.is_quant_position(p)]
    orders = mt5.orders_get(symbol=symbol)
```

Cada ciclo devolve um **texto de estado** (ex.: `🟢 IN_POSITION (9.1 BUY)`, `🔒 SÓ SIMULAÇÃO`) que vira o selo do Maestro (cap. 2 §2.4).

**Por que deduzir o estado em vez de guardá-lo?** Uma FSM com estado em memória precisa sincronizar com a corretora em todos os eventos (preenchimento parcial, stop atingido, fechamento manual), e qualquer evento perdido deixa o robô "acreditando" numa posição que não existe. Deduzir do MT5 elimina essa classe de inconsistência (cap. 1 §1.4).

### Reconciliação
`_reconcile_closed_trades` compara os trades marcados como abertos no `trades.json` com as posições e ordens vivas:
- ordem **pendente** ainda existe → não é fechamento (antes da v2.9.1, virava um trade falso);
- sem *deals* → era ordem cancelada: o registro é removido;
- com *deals* → registra a saída com **lucro real** = Σ(profit + comissão + swap) de todos os *deals* da posição.

### Uma entrada por candle
`_scan_and_execute.last_traded_candle` (clássico) e `quant_manager._last_signal_candle` (quant) impedem uma segunda tentativa no mesmo candle. Sem isso, um stop atingido dentro da hora fazia o *scan* (a cada segundo) reabrir o mesmo sinal e repetir o prejuízo.

## 3.4 Travas antes de abrir posição

Na ordem em que são avaliadas:

| Trava | Efeito | Origem |
|---|---|---|
| `.no_new_trades` | `/quit wait-flat` impede novas entradas | `shutdown_manager.create_no_trade_lock` |
| Setup não validado | Ativo sem rota quant não abre ao vivo (D5), salvo `allow_unvalidated_live` | `_unvalidated_blocked` |
| Conta REAL não confirmada | Não abre até `bot.bat setup` + "CONFIRMO" | `quant_manager.real_account_unconfirmed` |
| Garage lock | Saldo abaixo do mínimo do ativo | `MIN_BALANCE_REQUIREMENTS` |
| Janela de horário | Fora da sessão configurada (clássico) | `risk_calculator.get_trading_session_info` |
| Perda diária | Bloqueia entradas após perder X% no dia | `calculate_risk_limits` |

Posições **já abertas** continuam sendo gerenciadas mesmo com as travas ativas: travar a gestão deixaria uma posição sem acompanhamento.

## 3.5 Caminho quant (`quant_manager.py`)

Executa exatamente a regra validada no cap. 8:

1. Calcula o sinal no último candle fechado (`quant_setups.evaluate`, cap. 5 §5.1).
2. **Atraso de entrada:** só entra se o candle seguinte abriu há no máximo 10% da duração do candle (24 min no H4, 2,4 h no D1). O atraso é medido a partir da **abertura do candle em formação**, e não do relógio, para que um sinal de sexta seja executado na abertura de segunda, como no backtest (que entra na abertura de $t+1$).
3. Confere o *stops level* da corretora, o risco no SL × limite da rota e a reserva de margem (cap. 6 §6.3).
4. Envia **a mercado** com lote mínimo, SL e (no PULLB) TP gravados na ordem e comentário `Q <setup>`.
5. Gestão: o PULLB sai só por SL/TP; o RSI2MR sai quando o fechamento cruza a SMA5 ou após 15 candles. A saída é avaliada só depois que o candle de entrada fecha (`held >= 1`), como no backtest.

O caminho quant **ignora** posições sem o *magic* do robô. Numa conta *hedging*, uma posição manual do usuário no mesmo ativo coexiste e nunca é tocada; o caminho clássico, por sua vez, ignora posições quant (`is_quant_position`).

## 3.6 Caminho clássico (`_scan_and_execute`)

1. `StrategyScorer.evaluate_all`: todos os setups habilitados para o ativo (cap. 5 §5.2) e o filtro de tendência SMA200.
2. Filtro multi-timeframe (`check_mtf_trend`), pré-calculado uma vez por lado.
3. `aplicar_scoring`: gate RRR ≥ 1 e pontuação multicritério (cap. 5 §5.4); executa só o primeiro colocado.
4. RVOL (volume relativo) e veto do XGBoost (cap. 7), com possível *override* do supervisor adaptativo.
5. Dimensionamento (cap. 6 §6.1) e envio: ordem **STOP** no rompimento do candle de sinal ou, nos setups de entrada a mercado (`russian_bb`, `judas`), ordem a mercado com SL e TP.

Gestão (`_manage_position`): perda diária com liquidação, fim de sessão, saída parcial, breakeven com trava, trailing e saída quando a EMA9 vira contra (cap. 6). Os setups de alvo próprio (`TARGET_EXIT_SETUPS`) saem só por SL/TP, para não serem cortados por regras de seguimento de tendência que contradizem uma operação de reversão.

## 3.7 Limitações

- O caminho clássico concentra muitas responsabilidades numa função longa (`_scan_and_execute`, cerca de 200 linhas), e a cobertura de testes do `execution_manager` é de 52%. Uma evolução natural seria um *pipeline* de filtros com interface comum (*chain of responsibility*).
- O primeiro candle após um fim de semana é tratado como o seguinte ao último candle de sexta, o mesmo que o backtest faz, mas o *gap* de abertura não é modelado separadamente.

## 3.8 Referencial teórico

*Look-ahead bias* e disciplina temporal: [Bailey et al. 2014; López de Prado 2018]. Fonte da verdade externa: [Kleppmann 2017]. Máquinas de estados e diagramas: [Harel 1987].
