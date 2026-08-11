import MetaTrader5 as mt5
import logging
import config
import executor
import risk_calculator
import tracker
from brain.setups import PalexScorer


def manage_cycle(symbol, df):
    """
    Funcao principal chamada a cada avaliacao do bot (via Go Maestro).
    Infera o estado atual do simbolo no MT5 e despacha para a funcao de gestao correta.
    100% Stateless: Toda a tomada de decisao se baseia no que esta no MT5.
    """
    if df is None or len(df) < 5:
        return

    # 1. Obter estado atual no MT5
    positions = mt5.positions_get(symbol=symbol)
    orders = mt5.orders_get(symbol=symbol)

    if positions:
        # Estamos posicionados
        _manage_position(symbol, positions[0], df)
    elif orders:
        # Temos ordem pendente
        _manage_pending_order(symbol, orders[0], df)
    else:
        # Nao temos nada, buscar novos setups
        _scan_and_execute(symbol, df)


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
    virou_contra = False
    if is_buy and df['ema9_down'].iloc[-1]:
        virou_contra = True
    elif not is_buy and df['ema9_up'].iloc[-1]:
        virou_contra = True
        
    if virou_contra:
        logging.info(f"[{symbol}] EMA9 Virou Contra. Fechando Posicao {position.ticket}")
        result = executor.close_full_position(position.ticket, symbol, position.type)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            if is_buy:
                gain = current_close - position.price_open
            else:
                gain = position.price_open - current_close
            tracker.record_exit(position.ticket, current_close, result="win" if gain > 0 else "loss")


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


def _scan_and_execute(symbol, df):
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
    valid_setups, rejection_reason = PalexScorer.evaluate_all(df)
    current_candle_time = df['time'].iloc[-1] if 'time' in df.columns else None

    if not valid_setups:
        # Só imprime o motivo se ainda não imprimiu para este candle exato
        if current_candle_time and _scan_and_execute.last_logged_candle.get(symbol) != current_candle_time:
            logging.info(f"[{symbol}] Aguardando: {rejection_reason}")
            _scan_and_execute.last_logged_candle[symbol] = current_candle_time
        return
    best_setup = valid_setups[0]
    side = best_setup["action"].upper()
    setup_name = best_setup["setup"]
    entry_price = best_setup["trigger_price"]
    sl_price = best_setup["stop_loss"]

    # 2. Filtrar horario operacional (Risk Calculator)
    session_info = risk_calculator.get_trading_session_info(symbol=symbol)
    if not session_info["is_open"]:
        logging.info(f"[{symbol}] Setup {setup_name} de {side} ignorado (Fora de horario).")
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
