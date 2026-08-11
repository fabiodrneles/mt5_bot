import MetaTrader5 as mt5
import logging
import config
import executor
import risk_calculator
import tracker
from brain.setups import StrategyScorer
from brain.indicators import check_mtf_trend, check_rvol_filter


def _is_bot_position(position) -> bool:
    """True se a posicao foi aberta pelo bot (magic identico)."""
    bot_magic = getattr(config, "MAGIC", 0)
    return getattr(position, "magic", None) == bot_magic


def _register_external_position(symbol, position):
    """Registra no tracker uma posicao aberta manualmente pelo usuario (setup MANUAL).

    Roda apenas uma vez por ticket: se o tracker ja possui um trade aberto
    com este ticket, nada e feito.
    """
    ticket = getattr(position, "ticket", None)
    if ticket is None:
        logging.warning(f"[{symbol}] Posicao externa sem ticket. Ignorando registro.")
        return None

    open_trades = tracker.get_open_trades()
    if any(t.get("ticket") == ticket for t in open_trades):
        return None

    side = "BUY" if getattr(position, "type", 0) == mt5.POSITION_TYPE_BUY else "SELL"
    setup_name = getattr(config, "EXTERNAL_POSITION_SETUP_NAME", "MANUAL")

    trade_id = tracker.record_entry(
        symbol=symbol,
        side=side,
        setup_type=setup_name,
        entry_price=getattr(position, "price_open", 0.0),
        sl_price=getattr(position, "sl", 0.0) or 0.0,
        volume=getattr(position, "volume", 0.0),
        ticket=ticket,
    )
    logging.info(f"[{symbol}] Posicao externa adotada (ticket={ticket}, {side}, setup={setup_name})."
                 f" Bot passa a guiar alvo/stop.")
    return trade_id


def _find_exit_price(position_ticket, symbol):
    """Busca o preco de saida real da posicao no historico de deals do MT5."""
    try:
        deals = mt5.history_deals_get(position=position_ticket)
        if deals:
            for d in reversed(deals):
                if getattr(d, "entry", None) == getattr(mt5, "DEAL_ENTRY_OUT", 1):
                    return float(d.price)
    except Exception as e:
        logging.warning(f"[{symbol}] Falha ao ler historico de deals de {position_ticket}: {e}")
    return None


def _reconcile_closed_trades(symbol, df=None):
    """Fecha no tracker qualquer trade registrado que nao existe mais no MT5.

    Cobre posicoes (externas ou do bot) encerradas no MT5 de forma manual ou
    por stop, mantendo o historico de performance e o Daily Max Loss sincronos.
    Usa o preco real de saida do MT5, se disponivel.
    """
    open_trades = tracker.get_open_trades()
    relevant = [t for t in open_trades if t.get("symbol") == symbol]
    if not relevant:
        return

    live = mt5.positions_get(symbol=symbol)
    live_tickets = {p.ticket for p in live} if live else set()

    for trade in relevant:
        ticket = trade.get("ticket")
        if ticket in live_tickets:
            continue

        exit_price = _find_exit_price(ticket, symbol)
        if exit_price is None and df is not None and len(df):
            exit_price = float(df['close'].iloc[-1])
            logging.warning(f"[{symbol}] Sem deal de saida para {ticket}. Usando ultimo close como referencia.")

        if exit_price is None:
            logging.warning(f"[{symbol}] Impossivel reconciliar {ticket}: nada para fechar no MT5.")
            continue

        # Determinar resultado a partir do lado do trade registrado
        if trade.get("side") == "BUY":
            result = "win" if exit_price > trade.get("entry_price", 0) else "loss"
        else:
            result = "win" if exit_price < trade.get("entry_price", 0) else "loss"
        if abs(exit_price - trade.get("entry_price", 0)) < 1e-12:
            result = "breakeven"

        logging.info(f"[{symbol}] Posicao {ticket} nao esta mais aberta no MT5. Registrando saida "
                     f"({result} @ {exit_price:.5f})...")
        tracker.record_exit(ticket, exit_price=exit_price, result=result)


def manage_cycle(symbol, df, timeframe_name="H1"):
    """
    Funcao principal chamada a cada avaliacao do bot (via Go Maestro).
    Infera o estado atual do simbolo no MT5 e despacha para a funcao de gestao correta.
    100% Stateless: Toda a tomada de decisao se baseia no que esta no MT5.
    """
    if df is None or len(df) < 5:
        return

    # 1. Sincronizar historico: se o usario fechou algo manualmente, registrar saida.
    _reconcile_closed_trades(symbol, df)

    # 2. Obter estado atual no MT5
    positions = mt5.positions_get(symbol=symbol)
    orders = mt5.orders_get(symbol=symbol)

    if positions:
        position = positions[0]
        # Posicoes externas (magic diferente) sao adotadas apenas se permitido.
        if not _is_bot_position(position):
            if not getattr(config, "MANAGE_EXTERNAL_POSITIONS", True):
                logging.info(f"[{symbol}] Posicao externa (ticket={getattr(position, 'ticket', '?')}) "
                             f"encontrada, mas MANAGE_EXTERNAL_POSITIONS=False. Ignorando.")
                return
            _register_external_position(symbol, position)
        # Estamos posicionados
        _manage_position(symbol, position, df)
    elif orders:
        # Temos ordem pendente
        _manage_pending_order(symbol, orders[0], df)
    else:
        # Nao temos nada, buscar novos setups
        _scan_and_execute(symbol, df, timeframe_name=timeframe_name)


def _manage_position(symbol, position, df):
    """
    Gerencia uma posicao aberta (Trailing Stop, Saida Parcial, Breakeven, Saida Final).
    """
    current_close = df['close'].iloc[-1]
    is_buy = position.type == mt5.POSITION_TYPE_BUY
    
    # --- 1. SAIDA PARCIAL ---
    if getattr(config, 'PARTIAL_EXIT_ENABLED', True):
        deals = mt5.history_deals_get(position=position.ticket)
        partial_done = False
        if deals:
            # Verifica se houve deal de saida (fechamento parcial)
            for d in deals:
                if d.entry == mt5.DEAL_ENTRY_OUT:
                    partial_done = True
                    break
        
        if not partial_done:
            # Simplificacao inicial: Se o preco alcancou 1x ATR de lucro, fecha metade.
            atr = df['atr'].iloc[-1]
            trigger_distance = atr * getattr(config, 'PARTIAL_EXIT_TARGET', 1.0)
            
            if is_buy:
                gain = current_close - position.price_open
            else:
                gain = position.price_open - current_close
                
            if gain >= trigger_distance:
                volume_to_close = position.volume * getattr(config, 'PARTIAL_EXIT_PERCENT', 0.5)
                # Ensure we don't close less than min volume
                if volume_to_close >= 0.01:
                    logging.info(f"[{symbol}] Alvo Parcial Atingido! (Lucro: {gain:.4f} >= {trigger_distance:.4f})")
                    result = executor.close_partial_position(position.ticket, symbol, volume_to_close)
                    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                        tracker.record_partial_exit(position.ticket, current_close, volume_to_close)

    # --- 2. BREAKEVEN ---
    if getattr(config, 'ENABLE_BREAKEVEN', True):
        atr = df['atr'].iloc[-1]
        trigger_distance = atr * getattr(config, 'BREAKEVEN_ATR_RATIO', 1.0)
        
        # Verificar se ja esta no breakeven
        if is_buy:
            gain = current_close - position.price_open
            if gain >= trigger_distance and position.sl < position.price_open:
                logging.info(f"[{symbol}] Breakeven Ativado! Ajustando SL para {position.price_open}")
                executor.modify_position_sl(position.ticket, symbol, position.price_open)
        else:
            gain = position.price_open - current_close
            if gain >= trigger_distance and (position.sl > position.price_open or position.sl == 0.0):
                logging.info(f"[{symbol}] Breakeven Ativado! Ajustando SL para {position.price_open}")
                executor.modify_position_sl(position.ticket, symbol, position.price_open)

    # --- 3. SAIDA FINAL (EMA9 VIRANDO CONTRA) ---
    info = mt5.symbol_info(symbol)
    tick_size = info.trade_tick_size if info else 0.01
    tick_offset = getattr(config, 'TICK_OFFSET', 1)
    offset = tick_size * tick_offset

    if is_buy and df['ema9_down'].iloc[-1]:
        new_sl = df['low'].iloc[-1] - offset
        if position.sl == 0.0 or new_sl > position.sl:
            logging.info(f"[{symbol}] EMA9 Virou Contra (Compra). Ajustando SL para a minima do candle: {new_sl}")
            executor.modify_position_sl(position.ticket, symbol, new_sl)
    elif not is_buy and df['ema9_up'].iloc[-1]:
        new_sl = df['high'].iloc[-1] + offset
        if position.sl == 0.0 or new_sl < position.sl:
            logging.info(f"[{symbol}] EMA9 Virou Contra (Venda). Ajustando SL para a maxima do candle: {new_sl}")
            executor.modify_position_sl(position.ticket, symbol, new_sl)


def _manage_pending_order(symbol, order, df):
    """
    Gerencia uma ordem pendente. Cancela se a EMA9 virar contra o setup.
    """
    virou_contra = False
    is_buy = order.type == mt5.ORDER_TYPE_BUY_STOP
    
    if is_buy and df['ema9_down'].iloc[-1]:
        virou_contra = True
    elif not is_buy and df['ema9_up'].iloc[-1]:
        virou_contra = True
        
    if virou_contra:
        logging.info(f"[{symbol}] EMA9 Virou Contra a ordem pendente. Cancelando {order.ticket}")
        executor.cancel_order(order.ticket)


def _scan_and_execute(symbol, df, timeframe_name="H1"):
    """
    Busca por setups e despacha ordem caso encontre e seja validada.
    """
    import os
    if os.path.exists(".no_new_trades"):
        logging.info(f"[{symbol}] Scan abortado. Lock .no_new_trades detectado (aguardando shutdown).")
        return

    # State global (simples) para lembrar o último candle que reportamos para não flodar o console
    if not hasattr(_scan_and_execute, "last_logged_candle"):
        _scan_and_execute.last_logged_candle = {}

    # 1. Obter o melhor setup e o motivo de rejeição (se houver)
    info = mt5.symbol_info(symbol)
    tick_size = info.trade_tick_size if info else 0.01
    tick_offset = getattr(config, 'TICK_OFFSET', 1)
    valid_setups, rejection_reason = StrategyScorer.evaluate_all(df, tick_size, tick_offset)
    current_candle_time = df['time'].iloc[-1] if 'time' in df.columns else None

    if not valid_setups:
        # Só imprime o motivo se ainda não imprimiu para este candle exato
        if current_candle_time and _scan_and_execute.last_logged_candle.get(symbol) != current_candle_time:
            logging.info(f"[{symbol}] Aguardando: {rejection_reason}")
            _scan_and_execute.last_logged_candle[symbol] = current_candle_time
        return

    # 2. Motor de decisao (spec 5.5): gate RRR + scoring multicriterio.
    #    Ordena por score decrescente; executa apenas o primeiro candidato.
    # 2.7 Filtro Multi-Timeframe (MTF) integrado ao scoring (spec 5.4): como
    #    exige MT5 (dados do timeframe superior), e pre-computado aqui, uma vez
    #    por side presente, e injetado no motor de decisao (veto por-setup).
    from brain.scoring import aplicar_scoring
    mtf_favoravel = {}
    for s in valid_setups:
        s_side = str(s.get("action", "BUY")).upper()
        if s_side not in mtf_favoravel:
            mtf_favoravel[s_side] = check_mtf_trend(symbol, timeframe_name, s_side)
    ranked_setups = aplicar_scoring(valid_setups, df, mtf_favoravel=mtf_favoravel)
    if not ranked_setups:
        logging.info(f"[{symbol}] Setups detectados, mas todos vetados pelo scoring/RRR.")
        return
    best_setup = ranked_setups[0]
    side = best_setup["action"].upper()
    setup_name = best_setup["setup"]
    entry_price = best_setup["trigger_price"]
    sl_price = best_setup["stop_loss"]

    # 2. Filtrar horario operacional (Risk Calculator)
    session_info = risk_calculator.get_trading_session_info(symbol=symbol)
    if not session_info["is_open"]:
        logging.info(f"[{symbol}] Setup {setup_name} de {side} ignorado (Fora de horario).")
        return

    # 2.5 Daily Max Loss Shield: bloqueia novas entradas se a perda diaria exceder o limite.
    try:
        limits = risk_calculator.calculate_risk_limits()
        daily_pnl = tracker.get_daily_pnl()
        if daily_pnl is not None and daily_pnl <= -limits["max_daily_loss_currency"]:
            logging.warning(f"[{symbol}] Daily Max Loss Shield ativo (perda diaria {daily_pnl:.2f} <= -{limits['max_daily_loss_currency']:.2f}). Sem novas ordens.")
            return
    except Exception as e:
        logging.warning(f"[{symbol}] Falha ao avaliar Daily Max Loss Shield: {e}")

    # 2.6 Gate de Risco/Retorno (spec 5.5): aplicado pelo motor de decisao em `aplicar_scoring`
    #     (setups com RRR < MIN_RISK_REWARD sao zerados e descartados antes da ordenacao).

    # 2.8 Filtro de Volume Relativo (RVOL): exige volume acima do limiar.
    if not check_rvol_filter(df, side):
        logging.info(f"[{symbol}] Setup {setup_name} de {side} rejeitado (filtro RVOL: volume abaixo do limiar).")
        return

        
    # 3. Calcular Tamanho da Posicao
    volume, risk_curr, is_safe, reason = risk_calculator.calculate_position_size(
        symbol=symbol,
        entry_price=entry_price,
        sl_price=sl_price,
    )
    
    if not is_safe:
        logging.warning(f"[{symbol}] Ordem rejeitada pelo Gestor de Risco: {reason}")
        return
        
    # 4. Enviar Ordem
    logging.info(f"[{symbol}] Sinal de {side} detectado (Setup {setup_name}). Enviando Ordem STOP.")
    
    if side == "BUY":
        result = executor.place_buy_stop(symbol, entry_price, sl_price, volume=volume)
    else:
        result = executor.place_sell_stop(symbol, entry_price, sl_price, volume=volume)
        
    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        logging.info(f"[{symbol}] Ordem colocada com sucesso. Ticket: {result.order}")
        tracker.record_entry(
            symbol=symbol,
            side=side,
            setup_type=setup_name,
            entry_price=entry_price,
            sl_price=sl_price,
            volume=volume,
            ticket=result.order
        )
    else:
        logging.error(f"[{symbol}] Falha ao colocar ordem. Erro: {result.retcode if result else 'N/A'}")
