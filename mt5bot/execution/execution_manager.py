import MetaTrader5 as mt5
import logging
from mt5bot.core import config
from mt5bot.execution import executor
from mt5bot.risk import risk_calculator
from mt5bot.data import tracker
from mt5bot.engine.strategy import StrategyScorer
from mt5bot.engine.indicators import check_mtf_trend, check_rvol_filter


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


def manage_cycle(symbol, df, timeframe_name="H1", is_study_mode=False):
    """
    Funcao principal chamada a cada avaliacao do bot (via Go Maestro).
    Infera o estado atual do simbolo no MT5 e despacha para a funcao de gestao correta.
    100% Stateless: Toda a tomada de decisao se baseia no que esta no MT5.
    """
    if df is None or len(df) < 5:
        return "🔴 WAIT_DATA"

    if is_study_mode:
        return _manage_study_cycle(symbol, df, timeframe_name)

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
                return "🟢 EXTERNAL_POS"
            _register_external_position(symbol, position)
        # Estamos posicionados
        _manage_position(symbol, position, df)
        
        setup_name = "N/A"
        side = "BUY" if position.type == mt5.POSITION_TYPE_BUY else "SELL"
        open_trades = tracker.get_open_trades()
        for t in open_trades:
            if t.get("ticket") == position.ticket:
                setup_name = t.get("setup_type", "N/A")
                break
        return f"🟢 IN_POSITION ({setup_name} {side})"
        
    elif orders:
        # Temos ordem pendente
        _manage_pending_order(symbol, orders[0], df)
        side = "BUY" if orders[0].type == mt5.ORDER_TYPE_BUY_STOP else "SELL"
        return f"🟡 PENDING ({side})"
    else:
        # Nao temos nada, buscar novos setups
        scan_state = _scan_and_execute(symbol, df, timeframe_name=timeframe_name)
        return scan_state if scan_state else "🔵 SCANNING"


def _manage_study_cycle(symbol, df, timeframe_name):
    """
    Modo Telemetria / Simulador (Paper Trading).
    Avalia a estrategia sem enviar ordens reais, e rastreia o andamento usando o paper_tracker.
    """
    import time
    from mt5bot.data import paper_tracker
    from mt5bot.mentorship.supervisor import AdaptiveSupervisor
    from mt5bot.engine.indicators import check_mtf_trend, check_rvol_filter
    
    open_trades = [t for t in paper_tracker.get_open_trades() if t['symbol'] == symbol]
    current_candle = df.iloc[-1]
    
    for trade in open_trades:
        high = float(current_candle['high'])
        low = float(current_candle['low'])
        close = float(current_candle['close'])
        
        ticket = trade['ticket']
        sl = trade.get('sl_price', 0.0)
        
        # Extrai o Alvo calculado (Fibonacci fib_1_0) gravado pelo StrategyScorer
        target = 0.0
        ml_ctx = trade.get('ml_context', {})
        if ml_ctx and 'fibonacci' in ml_ctx:
            target = ml_ctx['fibonacci'].get('fib_1_0', 0.0)
        
        liquidar = False
        exit_price = 0.0
        
        if trade['side'] == 'BUY':
            if sl > 0 and low <= sl:
                liquidar = True
                exit_price = sl
            elif target > 0 and high >= target:
                liquidar = True
                exit_price = target
            elif current_candle['ema9_down'] and trade.get('setup') != 'FFFD':
                liquidar = True
                exit_price = close
        else:
            if sl > 0 and high >= sl:
                liquidar = True
                exit_price = sl
            elif target > 0 and low <= target:
                liquidar = True
                exit_price = target
            elif current_candle['ema9_up'] and trade.get('setup') != 'FFFD':
                liquidar = True
                exit_price = close
                
        if liquidar:
            paper_tracker.record_exit(ticket, exit_price)
            logging.info(f"[STUDY] {symbol} Posicao virtual encerrada a {exit_price}")
            
    # Se nao ha trades abertos, procura setups
    if not open_trades:
        if not hasattr(_manage_study_cycle, "last_logged_candle"):
            _manage_study_cycle.last_logged_candle = {}
        if not hasattr(_manage_study_cycle, "last_traded_candle"):
            _manage_study_cycle.last_traded_candle = {}

        info = mt5.symbol_info(symbol)
        tick_size = info.trade_tick_size if info else 0.01
        tick_offset = getattr(config, 'TICK_OFFSET', 1)
        current_candle_time = df['time'].iloc[-1] if 'time' in df.columns else None
        log_key = f"{symbol}_{timeframe_name}"
        
        # PREVENT RE-ENTRY ON SAME CANDLE
        if current_candle_time and _manage_study_cycle.last_traded_candle.get(log_key) == current_candle_time:
            return "🔵 STUDY_SCANNING"

        valid_setups, rejection = StrategyScorer.evaluate_all(df, tick_size, tick_offset, symbol=symbol)
        
        if not valid_setups:
            log_key = f"{symbol}_{timeframe_name}"
            if current_candle_time and _manage_study_cycle.last_logged_candle.get(log_key) != current_candle_time:
                logging.info(f"[STUDY] {symbol} Aguardando: {rejection}")
                _manage_study_cycle.last_logged_candle[log_key] = current_candle_time
            return "🔵 STUDY_SCANNING"
            
        from mt5bot.engine.scoring import aplicar_scoring
        mtf_favoravel = {}
        for s in valid_setups:
            s_side = str(s.get("action", "BUY")).upper()
            if s_side not in mtf_favoravel:
                mtf_favoravel[s_side] = check_mtf_trend(symbol, timeframe_name, s_side)
                
        ranked = aplicar_scoring(valid_setups, df, mtf_favoravel=mtf_favoravel)
        
        if not ranked:
            log_key = f"{symbol}_{timeframe_name}"
            if current_candle_time and _manage_study_cycle.last_logged_candle.get(log_key) != current_candle_time:
                override_approved = False
                if AdaptiveSupervisor.check_override(symbol, "Scoring/RRR/Macro"):
                    if valid_setups:
                        best = valid_setups[0]
                        override_approved = True
                        
                if not override_approved:
                    logging.info(f"[STUDY] {symbol} Setups detectados, mas vetados por Scoring/RRR/Filtros.")
                    _manage_study_cycle.last_logged_candle[log_key] = current_candle_time
                    for s in valid_setups:
                        paper_tracker.record_rejection(symbol, s['setup'], str(s.get("action", "BUY")).upper(), s['trigger_price'], s['stop_loss'], "Scoring/RRR/Macro", timeframe=timeframe_name, ml_context=s.get('ml_context'))
                    return "🔵 STUDY_SCANNING"
            else:
                return "🔵 STUDY_SCANNING"
            
        if 'best' not in locals():
            best = ranked[0]
            
        side = best['action'].upper()
        
        # Check rvol just like the real one
        if not check_rvol_filter(df, side):
            current_rvol = df['rvol'].iloc[-1] if 'rvol' in df.columns else None
            if not AdaptiveSupervisor.check_override(symbol, "RVOL", current_rvol=current_rvol):
                log_key = f"{symbol}_{timeframe_name}"
                if current_candle_time and _manage_study_cycle.last_logged_candle.get(log_key) != current_candle_time:
                    logging.info(f"[STUDY] {symbol} Setup {best['setup']} de {side} rejeitado (filtro RVOL).")
                    _manage_study_cycle.last_logged_candle[log_key] = current_candle_time
                    paper_tracker.record_rejection(symbol, best['setup'], side, best['trigger_price'], best['stop_loss'], "RVOL", timeframe=timeframe_name, ml_context=best.get('ml_context'))
                return "🔵 STUDY_SCANNING"
            
        # Filtro de Machine Learning (XGBoost Supervisor) no modo Study
        from mt5bot.mentorship.ml_xgboost import MLSupervisor
        ml_context = best.get('ml_context', {})
        if ml_context:
            is_approved, prob_win, ml_reason = MLSupervisor.predict_trade(symbol, best['setup'], ml_context)
            if not is_approved:
                log_key = f"{symbol}_{timeframe_name}"
                if current_candle_time and _manage_study_cycle.last_logged_candle.get(log_key) != current_candle_time:
                    logging.warning(f"[STUDY] {symbol} Setup {best['setup']} de {side} VETADO pela IA (Win Prob: {prob_win:.2f}): {ml_reason}. Criando Ordem Fantasma.")
                    _manage_study_cycle.last_logged_candle[log_key] = current_candle_time
                paper_tracker.record_rejection(symbol, best['setup'], side, best['trigger_price'], best['stop_loss'], "ML Veto", timeframe=timeframe_name, ml_context=ml_context)
                
                # DATA FLYWHEEL: Abrir a ordem fantasma para acompanhar o futuro do veto!
                ticket = int(time.time() * 1000)
                paper_tracker.record_entry(
                    symbol=symbol,
                    side=side,
                    setup_type=best['setup'],
                    entry_price=best['trigger_price'],
                    sl_price=best['stop_loss'],
                    volume=0.01,
                    ticket=ticket,
                    ml_context=ml_context,
                    is_vetoed=True,
                    veto_reason=f"ML Veto (Prob: {prob_win:.2f})"
                )
                return "🔵 STUDY_SCANNING"
            elif prob_win < 1.0:
                log_key = f"{symbol}_{timeframe_name}"
                if current_candle_time and _manage_study_cycle.last_logged_candle.get(log_key) != current_candle_time:
                    logging.info(f"[STUDY] {symbol} IA APROVOU Trade de {side} (Win Prob: {prob_win:.2f})")

        ticket = int(time.time() * 1000) # fake ticket
        paper_tracker.record_entry(
            symbol=symbol,
            side=side,
            setup_type=best['setup'],
            entry_price=best['trigger_price'],
            sl_price=best['stop_loss'],
            volume=1.0, # fake volume
            ticket=ticket,
            ml_context=best.get('ml_context')
        )
        _manage_study_cycle.last_traded_candle[log_key] = current_candle_time
        logging.info(f"[STUDY] {symbol} Sinal {side} (Setup {best['setup']}). Entrada virtual.")
        return f"🟣 PAPER_TRADE ({best['setup']} {side})"

    # Se chegou aqui, recarregue para ver o estado apos simulacoes
    open_trades = [t for t in paper_tracker.get_open_trades() if t['symbol'] == symbol]
    if open_trades:
        trade = open_trades[0]
        return f"🟣 PAPER_TRADE ({trade.get('setup', 'N/A')} {trade['side']})"
    return "🔵 STUDY_SCANNING"


def _manage_position(symbol, position, df):
    """
    Gerencia uma posicao aberta (Trailing Stop, Saida Parcial, Breakeven, Saida Final).
    """
    current_close = df['close'].iloc[-1]
    is_buy = position.type == mt5.POSITION_TYPE_BUY
    
    # --- 0. DAILY MAX LOSS CLOSE (protecao de capital) ---
    # Se a perda diaria (realizada + flutuante da posicao aberta) bater o limite,
    # liquida a posicao a mercado imediatamente. O shield base apenas bloqueava
    # novas entradas; aqui contemos o risco real da posicao atual.
    if getattr(config, 'DAILY_MAX_LOSS_CLOSE_ENABLED', True):
        try:
            limits = risk_calculator.calculate_risk_limits()
            daily_pnl = tracker.get_daily_pnl()
            floating = float(getattr(position, "profit", 0.0) or 0.0)
            if daily_pnl is not None and (daily_pnl + floating) <= -limits["max_daily_loss_currency"]:
                logging.warning(f"[{symbol}] Daily Max Loss Close ativo (perda diaria {daily_pnl:.2f}"
                                f" + flutuante {floating:.2f} = {daily_pnl + floating:.2f}"
                                f" <= -{limits['max_daily_loss_currency']:.2f}). Liquidando posicao {position.ticket} a mercado...")
                executor.close_full_position(position.ticket, symbol, position.type)
                return
        except Exception as e:
            logging.warning(f"[{symbol}] Falha ao avaliar Daily Max Loss Close: {e}")
    
    # --- 0. SAIDA FIM DE SESSAO (equivalente ao exit_both_sessions da otimizacao) ---
    # Se o horario institucional do ativo ja terminou, liquidar a posicao em vez
    # de manter abertas contra spreads de baixa liquidez.
    if getattr(config, 'TRADING_HOURS_ENABLED', True):
        if not risk_calculator.is_within_trading_hours(symbol=symbol):
            logging.info(f"[{symbol}] Fim da sessao institucional. Liquidando posicao a mercado...")
            executor.close_full_position(position.ticket, symbol, position.type)
            return
    
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

    # --- 2.5 TRAILING STOP DINAMICO (spec 5.7) ---
    # Apos o breakeven, o SL acompanha o mercado. Se o preco perder a media de
    # referencia do modo escolhido, o restante e liquidado a mercado.
    if getattr(config, 'TRAILING_ENABLED', True):
        from mt5bot.engine.trailing import aplicar_trailing
        modo = getattr(config, 'TRAILING_MODE', 'candle')
        side = "BUY" if is_buy else "SELL"
        novo_sl, liquidar = aplicar_trailing(
            df, side, sl_atual=float(position.sl or 0.0), modo=modo,
        )
        if liquidar:
            logging.info(f"[{symbol}] {side} perdeu a media de referencia ({modo}). Liquidando restante...")
            # O resultado real sera registrado pelo _reconcile_closed_trades
            # (usa o preco do deal real do MT5) no proximo ciclo.
            executor.close_full_position(position.ticket, symbol, position.type)
        elif novo_sl is not None:
            logging.info(f"[{symbol}] Trailing {modo}: movendo SL de {position.sl} para {novo_sl}")
            executor.modify_position_sl(position.ticket, symbol, novo_sl)

    # --- 3. SAIDA FINAL (EMA9 VIRANDO CONTRA) ---
    info = mt5.symbol_info(symbol)
    tick_size = info.trade_tick_size if info else 0.01
    tick_offset = getattr(config, 'TICK_OFFSET', 1)
    offset = tick_size * tick_offset

    # Descobrir qual o setup (para proteger FFFD da saida pela EMA9)
    open_trades = tracker.get_open_trades()
    setup_name = "N/A"
    for t in open_trades:
        if t.get("ticket") == position.ticket:
            setup_name = t.get("setup", "N/A")
            break

    if setup_name != "FFFD":
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
        return "🔴 BLOQUEADO"

    # State global (simples) para lembrar o último candle que reportamos para não flodar o console
    if not hasattr(_scan_and_execute, "last_logged_candle"):
        _scan_and_execute.last_logged_candle = {}

    # 0. Bloqueio de Garagem (Capital Mínimo)
    # Protege contra operacoes fora da margem antes mesmo de escanear o mercado
    min_balance_reqs = getattr(config, 'MIN_BALANCE_REQUIREMENTS', {})
    if symbol in min_balance_reqs:
        from mt5bot.risk.risk_calculator import get_account_balance
        balance = get_account_balance()
        required_balance = min_balance_reqs[symbol]
        if balance < required_balance:
            if not hasattr(_scan_and_execute, "last_logged_garage_warn"):
                _scan_and_execute.last_logged_garage_warn = {}
                
            import time
            current_time = time.time()
            last_warn = _scan_and_execute.last_logged_garage_warn.get(symbol, 0)
            
            # Loga no maximo a cada 5 minutos
            if current_time - last_warn > 300:
                logging.info(f"[{symbol}] GARAGE LOCK ativo. Saldo atual (${balance:.2f}) e menor que a margem exigida (${required_balance:.2f}).")
                _scan_and_execute.last_logged_garage_warn[symbol] = current_time
                
            return "🔒 GARAGE LOCK"

    # 1. Filtrar horario operacional (Risk Calculator)
    session_info = risk_calculator.get_trading_session_info(symbol=symbol)
    if not session_info["is_open"]:
        if not hasattr(_scan_and_execute, "last_logged_time_warn"):
            _scan_and_execute.last_logged_time_warn = {}
            
        import time
        current_time = time.time()
        last_warn = _scan_and_execute.last_logged_time_warn.get(symbol, 0)
        
        # Loga no maximo a cada 5 minutos
        if current_time - last_warn > 300:
            logging.info(f"[{symbol}] Aguardando: FORA da janela lucrativa ({session_info['start_time']} a {session_info['end_time']} BRT).")
            _scan_and_execute.last_logged_time_warn[symbol] = current_time
            
        return "⏳ HORÁRIO FECHADO"

    # 2. Obter o melhor setup e o motivo de rejeição (se houver)
    info = mt5.symbol_info(symbol)
    tick_size = info.trade_tick_size if info else 0.01
    tick_offset = getattr(config, 'TICK_OFFSET', 1)
    valid_setups, rejection_reason = StrategyScorer.evaluate_all(df, tick_size, tick_offset, symbol=symbol)
    current_candle_time = df['time'].iloc[-1] if 'time' in df.columns else None

    if not valid_setups:
        # Só imprime o motivo se ainda não imprimiu para este candle exato
        if current_candle_time and _scan_and_execute.last_logged_candle.get(symbol) != current_candle_time:
            logging.info(f"[{symbol}] Aguardando: {rejection_reason}")
            _scan_and_execute.last_logged_candle[symbol] = current_candle_time
        return None

    # 2. Motor de decisao (spec 5.5): gate RRR + scoring multicriterio.
    #    Ordena por score decrescente; executa apenas o primeiro candidato.
    # 2.7 Filtro Multi-Timeframe (MTF) integrado ao scoring (spec 5.4): como
    #    exige MT5 (dados do timeframe superior), e pre-computado aqui, uma vez
    #    por side presente, e injetado no motor de decisao (veto por-setup).
    from mt5bot.engine.scoring import aplicar_scoring
    mtf_favoravel = {}
    for s in valid_setups:
        s_side = str(s.get("action", "BUY")).upper()
        if s_side not in mtf_favoravel:
            mtf_favoravel[s_side] = check_mtf_trend(symbol, timeframe_name, s_side)
    ranked_setups = aplicar_scoring(valid_setups, df, mtf_favoravel=mtf_favoravel)
    if not ranked_setups:
        override_approved = False
        if AdaptiveSupervisor.check_override(symbol, "Scoring/RRR/Macro"):
            if valid_setups:
                # O supervisor mandou ignorar o macro e aprovar o melhor matematico
                ranked_setups = [valid_setups[0]]
                override_approved = True
                
        if not override_approved:
            if current_candle_time and _scan_and_execute.last_logged_candle.get(symbol) != current_candle_time:
                logging.info(f"[{symbol}] Setups detectados, mas todos vetados pelo scoring/RRR.")
                _scan_and_execute.last_logged_candle[symbol] = current_candle_time
            return None
    best_setup = ranked_setups[0]
    side = best_setup["action"].upper()
    setup_name = best_setup["setup"]
    entry_price = best_setup["trigger_price"]
    sl_price = best_setup["stop_loss"]
    tp_price = best_setup.get("target")

    # Horario operacional ja foi verificado no topo

    # 2.5 Daily Max Loss Shield: bloqueia novas entradas se a perda diaria exceder o limite.
    try:
        limits = risk_calculator.calculate_risk_limits()
        daily_pnl = tracker.get_daily_pnl()
        if daily_pnl is not None and daily_pnl <= -limits["max_daily_loss_currency"]:
            logging.warning(f"[{symbol}] Daily Max Loss Shield ativo (perda diaria {daily_pnl:.2f} <= -{limits['max_daily_loss_currency']:.2f}). Sem novas ordens.")
            return "🔴 MAX LOSS DIÁRIO"
    except Exception as e:
        logging.warning(f"[{symbol}] Falha ao avaliar Daily Max Loss Shield: {e}")

    # 2.6 Gate de Risco/Retorno (spec 5.5): aplicado pelo motor de decisao em `aplicar_scoring`
    #     (setups com RRR < MIN_RISK_REWARD sao zerados e descartados antes da ordenacao).

    # 2.8 Filtro de Volume Relativo (RVOL): exige volume acima do limiar.
    if not check_rvol_filter(df, side):
        current_rvol = df['rvol'].iloc[-1] if 'rvol' in df.columns else None
        if not AdaptiveSupervisor.check_override(symbol, "RVOL", current_rvol=current_rvol):
            if current_candle_time and _scan_and_execute.last_logged_candle.get(symbol) != current_candle_time:
                logging.info(f"[{symbol}] Setup {setup_name} de {side} rejeitado (filtro RVOL: volume abaixo do limiar).")
                _scan_and_execute.last_logged_candle[symbol] = current_candle_time
            return None

    # 2.9 Filtro de Machine Learning (XGBoost Supervisor)
    from mt5bot.mentorship.ml_xgboost import MLSupervisor
    ml_context = best_setup.get('ml_context', {})
    
    prob_win = None
    if ml_context:
        is_approved, prob_win, ml_reason = MLSupervisor.predict_trade(symbol, setup_name, ml_context)
        if not is_approved:
            if current_candle_time and _scan_and_execute.last_logged_candle.get(symbol) != current_candle_time:
                logging.warning(f"[{symbol}] Setup {setup_name} de {side} VETADO pela IA (Win Prob: {prob_win:.2f}): {ml_reason}")
                _scan_and_execute.last_logged_candle[symbol] = current_candle_time
            tracker.record_rejection(symbol, setup_name, side, entry_price, sl_price, "ML Veto", timeframe=timeframe_name, ml_context=ml_context)
            return "🔴 ML VETO"
        elif prob_win < 1.0:
            if current_candle_time and _scan_and_execute.last_logged_candle.get(symbol) != current_candle_time:
                logging.info(f"[{symbol}] IA APROVOU Trade de {side} (Win Prob: {prob_win:.2f})")

        
    # 3. Calcular Tamanho da Posicao
    volume, risk_curr, is_safe, reason = risk_calculator.calculate_position_size(
        symbol=symbol,
        entry_price=entry_price,
        sl_price=sl_price,
        prob_win=prob_win,
        tp_price=tp_price
    )
    
    if not is_safe:
        logging.warning(f"[{symbol}] Ordem rejeitada pelo Gestor de Risco: {reason}")
        if "Spread Trap" in reason:
            tracker.record_rejection(symbol, setup_name, side, entry_price, sl_price, "Spread Trap", timeframe=timeframe_name, ml_context=best_setup.get('ml_context'))
        elif "Risco do Stop Loss" in reason:
            tracker.record_rejection(symbol, setup_name, side, entry_price, sl_price, "Max Risk Exceeded", timeframe=timeframe_name, ml_context=best_setup.get('ml_context'))
        
        if "GARAGE LOCK" in reason:
            return "🔒 GARAGE LOCK"
        return "🟡 SINAL REJEITADO"
        
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
            ticket=result.order,
            ml_context=best_setup.get('ml_context')
        )
    else:
        logging.error(f"[{symbol}] Falha ao colocar ordem. Erro: {result.retcode if result else 'N/A'}")
        return "🔴 ERRO DE ORDEM"
    return "🟢 EM POSIÇÃO"
