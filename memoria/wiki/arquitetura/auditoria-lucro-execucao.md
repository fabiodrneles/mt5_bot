# Auditoria de execucao — por que o bot nao fechava no lucro (v2.9.1)

Decisoes e bugs encontrados na revisao de 2026-10-24. Valem para o caminho real
de execucao: Maestro Go -> `interfaces/brain_worker.py` -> `execution_manager.manage_cycle`
(chamado a cada 1 segundo por ativo).

## Bugs corrigidos
1. **Candle em formacao**: o worker puxava `copy_rates_from_pos(..., 0, 200)`, entao
   `df.iloc[-1]` era a vela aberta. Setups, EMA9 virando, RVOL e trailing eram
   avaliados tick a tick sobre um candle que ainda muda. Agora usa pos 1 (so
   velas fechadas) no modo real; o modo estudo segue com pos 0.
2. **russian_bb / judas nunca abriam**: entrada = close atual enviada como BUY/SELL
   STOP no proprio preco -> MT5 recusa (invalid price). Agora vao a mercado
   (`executor.place_market_order`) com SL e TP (`MARKET_ENTRY_SETUPS`).
3. **Saida diferente do backtest**: o backtest (`tools/backtest.py`) sai por TP
   (banda oposta) ou SL. Ao vivo nao havia TP e a EMA9/trailing ATR cortava o
   trade de reversao logo apos a entrada (EMA9 aponta contra por definicao).
   Agora `TARGET_EXIT_SETUPS` (russian_bb, judas, GAP) levam TP ao MT5 e saem
   so por TP/SL + fim de sessao + Daily Max Loss.
4. **Breakeven no preco exato** devolvia o lucro e pagava comissao. Agora o SL vai
   para entrada +/- (spread x `BREAKEVEN_LOCK_SPREAD_MULT`) + 1 tick.
5. **Reconciliacao fantasma**: ordem pendente registrada como "open" era fechada
   no ciclo seguinte (nao estava em positions_get) com win/loss falso pelo ultimo
   close. Agora pendentes sao ignoradas, canceladas sao removidas e o resultado
   usa o lucro real dos deals (profit + comissao + swap).
6. **Reentrada no mesmo candle**: apos stop dentro da hora, o scan (1 s) reabria o
   mesmo sinal. Agora 1 tentativa de entrada por candle por ativo.
7. `AdaptiveSupervisor` sem import no modo real (NameError quando scoring/RVOL vetava).
8. Lookup de setup usava a chave `setup_type` (o tracker grava `setup`).
9. `TRADE_ACTION_SLTP` sem `tp` zerava o TP da posicao: `modify_position_sl` preserva.
10. EMA9 contra com preco ja abaixo da minima: SL seria recusado; agora liquida a mercado.

## Limitacoes conhecidas (nao corrigidas)
- Com lote 0.01 a saida parcial de 50% nunca acontece (0.005 < lote minimo).
- O Judas compara `HH:MM` do candle (hora do servidor) com horarios BRT.
- Testes: `tests/test_profit_fixes.py`.
