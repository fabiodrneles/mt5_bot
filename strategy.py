import MetaTrader5 as mt5
import config
import logger
import indicators
import executor
import persistence
import tracker
import risk_calculator
from enum import Enum


class State(Enum):
    SCANNING = 1
    SIGNAL_READY = 2
    IN_POSITION = 3
    WATCHING_92 = 4


class TradeSide(Enum):
    BUY = 1
    SELL = 2


class SymbolState:
    def __init__(self, symbol):
        self.symbol = symbol
        self.state = State.SCANNING
        self.pending_order_ticket = None
        self.position_ticket = None
        self.position_type = None  # TradeSide enum
        self.candle_referencia = None  # tuple (time, open, high, low, close, ...)
        self.entry_price = None
        self.sl_price = None
        self.partial_exit_done = False
        # Setup 9.2
        self.watching_92_candles = 0  # Contagem de candles em WATCHING_92
        self.setup_type = "9.1"  # "9.1" ou "9.2"
        self.exit_profit = None  # True se saiu com lucro, False se prejuizo


symbol_states = {}


def initialize_symbol_states():
    """Inicializa estados dos simbolos. Tenta carregar do arquivo primeiro."""
    if not mt5.initialize():
        logger.error("Falha ao inicializar MT5 no Strategy. Verifique se o terminal esta rodando.")
        return False

    for symbol in config.SYMBOLS:
        symbol_states[symbol] = SymbolState(symbol)

    # Tentar carregar estados persistidos
    loaded = persistence.load_states()
    if loaded:
        persistence.apply_loaded_states(symbol_states, loaded, State, TradeSide)

    # Validar estados contra MT5 (confirmar que ordens/posicoes ainda existem)
    for symbol in config.SYMBOLS:
        s_state = symbol_states[symbol]
        _validate_state_against_mt5(s_state)
        _check_orphaned_mt5_state(s_state)

    return True


def _validate_state_against_mt5(s_state):
    """Valida que o estado persistido ainda corresponde a realidade no MT5."""
    symbol = s_state.symbol

    if s_state.state == State.SIGNAL_READY and s_state.pending_order_ticket:
        orders = executor.get_current_orders(symbol)
        our_orders = [o for o in orders if o.magic == config.MAGIC and o.ticket == s_state.pending_order_ticket]
        if not our_orders:
            # Verificar se virou posicao
            positions = executor.get_current_positions(symbol)
            our_positions = [p for p in positions if p.magic == config.MAGIC]
            if our_positions:
                s_state.state = State.IN_POSITION
                s_state.position_ticket = our_positions[0].ticket
                s_state.position_type = TradeSide.BUY if our_positions[0].type == mt5.POSITION_TYPE_BUY else TradeSide.SELL
                s_state.pending_order_ticket = None
                logger.info(f"[{symbol}] Ordem preenchida durante offline. IN_POSITION ticket={s_state.position_ticket}")
            else:
                _reset_to_scanning(s_state)
                logger.warning(f"[{symbol}] Ordem pendente nao encontrada no MT5. Resetando para SCANNING.")

    elif s_state.state == State.IN_POSITION and s_state.position_ticket:
        positions = executor.get_current_positions(symbol)
        our_positions = [p for p in positions if p.magic == config.MAGIC and p.ticket == s_state.position_ticket]
        if not our_positions:
            _reset_to_scanning(s_state)
            logger.warning(f"[{symbol}] Posicao nao encontrada no MT5. Resetando para SCANNING.")
        else:
            # Atualizar partial_exit_done pelo volume
            position = our_positions[0]
            s_state.partial_exit_done = (position.volume < config.VOLUME_INITIAL)

    elif s_state.state == State.WATCHING_92:
        # WATCHING_92 nao tem ordem/posicao ativa, so manter estado
        pass


def _check_orphaned_mt5_state(s_state):
    """Verifica posicoes ou ordens no MT5 que nao estao no state.json."""
    if s_state.state != State.SCANNING:
        return

    symbol = s_state.symbol
    orders = executor.get_current_orders(symbol)
    our_orders = [o for o in orders if o.magic == config.MAGIC]
    if our_orders:
        order = our_orders[0]
        logger.warning(f"[{symbol}] ORDEM ORFA detectada! Ticket={order.ticket}")
        logger.warning(f"[{symbol}] Restaurando estado SIGNAL_READY para ordem orfa.")
        s_state.state = State.SIGNAL_READY
        s_state.pending_order_ticket = order.ticket
        return

    positions = executor.get_current_positions(symbol)
    our_positions = [p for p in positions if p.magic == config.MAGIC]
    if our_positions:
        position = our_positions[0]
        logger.warning(f"[{symbol}] POSICAO ORFA detectada! "
                       f"Ticket={position.ticket} "
                       f"Tipo={'BUY' if position.type == mt5.POSITION_TYPE_BUY else 'SELL'} "
                       f"Volume={position.volume}")
        logger.warning(f"[{symbol}] Restaurando estado IN_POSITION para posicao orfa.")
        s_state.state = State.IN_POSITION
        s_state.position_ticket = position.ticket
        s_state.position_type = TradeSide.BUY if position.type == mt5.POSITION_TYPE_BUY else TradeSide.SELL
        s_state.partial_exit_done = (position.volume < config.VOLUME_INITIAL)


def _reset_to_scanning(s_state):
    """Reseta um SymbolState para SCANNING."""
    s_state.state = State.SCANNING
    s_state.pending_order_ticket = None
    s_state.position_ticket = None
    s_state.position_type = None
    s_state.candle_referencia = None
    s_state.entry_price = None
    s_state.sl_price = None
    s_state.partial_exit_done = False
    s_state.watching_92_candles = 0
    s_state.setup_type = "9.1"
    s_state.exit_profit = None


def _save_states():
    """Wrapper para salvar estados."""
    persistence.save_states(symbol_states)


def evaluate(symbol, candle_fechado, all_rates):
    """Funcao principal de avaliacao chamada a cada candle fechado."""
    s_state = symbol_states.get(symbol)
    if not s_state:
        logger.error(f"[{symbol}] Estado nao inicializado. Abortando avaliacao.")
        return

    current_close = candle_fechado[4]
    logger.info(
        f"[{symbol}] Estado atual: {s_state.state.name} | Close={current_close:.5f} | "
        f"Buscando Setup 9.1{'/9.2' if s_state.state == State.WATCHING_92 else ''}."
    )

    # Verificar dados suficientes
    min_required = max(config.EMA_PERIOD, config.EMA_FILTER_PERIOD) + 2
    if len(all_rates) < min_required:
        logger.warning(f"[{symbol}] Dados insuficientes ({len(all_rates)} rates). Necessarios: {min_required}")
        return

    ema9_values = indicators.get_ema9(all_rates)
    ema21_values = indicators.get_ema21(all_rates)

    if ema9_values is None or ema21_values is None:
        logger.warning(f"[{symbol}] Erro no calculo da EMA. Ignorando candle.")
        return

    current_close = candle_fechado[4]

    symbol_info = executor.get_symbol_info(symbol)
    if not symbol_info:
        logger.error(f"[{symbol}] Nao foi possivel obter informacoes do simbolo.")
        return

    # Filtro flat (aplica para SCANNING e SIGNAL_READY)
    if config.FLAT_FILTER_ENABLED and s_state.state in (State.SCANNING, State.SIGNAL_READY):
        if indicators.check_flat(ema9_values, symbol_info):
            diff_ticks = abs(ema9_values[-1] - ema9_values[-5]) / (symbol_info.trade_tick_size or symbol_info.point)
            multiplier = config.FLAT_THRESHOLD_MULTIPLIERS.get(config.TIMEFRAME_NAME, 1.0)
            threshold = config.FLAT_THRESHOLD_TICKS * multiplier
            logger.info(
                f"[{symbol}] Sinal rejeitado: mercado lateral (EMA9 FLAT). "
                f"A variação foi {diff_ticks:.1f} ticks, abaixo do threshold {threshold:.1f}. "
                "Buscando uma virada clara de EMA9 para 9.1."
            )
            if s_state.state == State.SIGNAL_READY and s_state.pending_order_ticket:
                logger.info(
                    f"[{symbol}] Cancelando ordem {s_state.pending_order_ticket} porque o mercado está lateral "
                    f"e não há virada clara de EMA9."
                )
                executor.cancel_order(s_state.pending_order_ticket)
                _reset_to_scanning(s_state)
                _save_states()
            return

    filtro_compra_ok = indicators.check_filtro_ema21(current_close, ema21_values)
    filtro_venda_ok = indicators.check_filtro_ema21_venda(current_close, ema21_values)

    # Maquina de estados
    if s_state.state == State.SCANNING:
        _handle_scanning(s_state, candle_fechado, ema9_values, filtro_compra_ok, filtro_venda_ok, symbol_info, all_rates)
    elif s_state.state == State.SIGNAL_READY:
        _handle_signal_ready(s_state, ema9_values)
    elif s_state.state == State.IN_POSITION:
        _handle_in_position(s_state, ema9_values, current_close, candle_fechado, symbol_info, all_rates)
    elif s_state.state == State.WATCHING_92:
        _handle_watching_92(s_state, candle_fechado, ema9_values, filtro_compra_ok, filtro_venda_ok, symbol_info, all_rates)


# --- SCANNING ---

def _handle_scanning(s_state, candle_fechado, ema9_values, filtro_compra_ok, filtro_venda_ok, symbol_info, all_rates):
    ema9_was_pointing_down = indicators.check_apontando_para_baixo(ema9_values[:-1])
    ema9_was_pointing_up = indicators.check_apontando_para_cima(ema9_values[:-1])

    virou_para_cima = indicators.check_virou_para_cima(ema9_values)
    virou_para_baixo = indicators.check_virou_para_baixo(ema9_values)

    tick_size = executor.get_tick_size(symbol_info)

    # Log de debug com flags utilizadas na decisao para facilitar analise
    logger.debug(
        f"[{s_state.symbol}] scan flags: virou_up={virou_para_cima} virou_down={virou_para_baixo} "
        f"was_up={ema9_was_pointing_up} was_down={ema9_was_pointing_down} "
        f"filtro_compra_ok={filtro_compra_ok} filtro_venda_ok={filtro_venda_ok} "
        f"close={candle_fechado[4]:.5f} ema9_last={ema9_values[-1]:.5f}"
    )

    if virou_para_cima and ema9_was_pointing_down and filtro_compra_ok:
        logger.info(f"[{s_state.symbol}] Sinal de COMPRA detectado (Setup 9.1).")
        _place_entry_order(s_state, candle_fechado, TradeSide.BUY, tick_size, symbol_info, all_rates, "9.1")

    elif virou_para_baixo and ema9_was_pointing_up and filtro_venda_ok:
        logger.info(f"[{s_state.symbol}] Sinal de VENDA detectado (Setup 9.1).")
        _place_entry_order(s_state, candle_fechado, TradeSide.SELL, tick_size, symbol_info, all_rates, "9.1")

    # --- SETUP 9.3 (Larry Williams) ---
    elif config.SETUP_93_ENABLED and indicators.check_setup_93_buy(all_rates, ema9_values) and filtro_compra_ok:
        logger.info(f"[{s_state.symbol}] Sinal de COMPRA detectado (Setup 9.3).")
        _place_entry_order(s_state, candle_fechado, TradeSide.BUY, tick_size, symbol_info, all_rates, "9.3")

    elif config.SETUP_93_ENABLED and indicators.check_setup_93_sell(all_rates, ema9_values) and filtro_venda_ok:
        logger.info(f"[{s_state.symbol}] Sinal de VENDA detectado (Setup 9.3).")
        _place_entry_order(s_state, candle_fechado, TradeSide.SELL, tick_size, symbol_info, all_rates, "9.3")

    elif virou_para_cima and ema9_was_pointing_down and not filtro_compra_ok:
        logger.info(
            f"[{s_state.symbol}] Rejeitado: EMA9 virou para cima, mas a tendência maior "
            f"(EMA21) ainda está contra. Close={candle_fechado[4]:.5f} < EMA21. "
            "Buscando um sinal 9.1 com EMA21 de compra confirmando."
        )

    elif virou_para_baixo and ema9_was_pointing_up and not filtro_venda_ok:
        logger.info(
            f"[{s_state.symbol}] Rejeitado: EMA9 virou para baixo, mas a tendência maior "
            f"(EMA21) ainda está contra. Close={candle_fechado[4]:.5f} > EMA21. "
            "Buscando um sinal 9.1 com EMA21 de venda confirmando."
        )

    elif not virou_para_cima and not virou_para_baixo:
        slopes = indicators.get_ema9_slopes(ema9_values)
        slope_str = f"{slopes[0]:.6f}" if slopes else "N/A"
        logger.info(
            f"[{s_state.symbol}] Rejeitado: nenhuma virada clara de EMA9. "
            f"Slope atual={slope_str}. Buscando uma reversão definida para 9.1."
        )


def _place_entry_order(s_state, candle_ref, side, tick_size, symbol_info, all_rates, setup_type):
    """Coloca ordem de entrada (BUY ou SELL STOP) com ajuste ATR se necessario e controle de risco."""
    # 1. FILTRO DE HORARIO DE NEGOCIACAO:
    if not risk_calculator.is_within_trading_hours(symbol=s_state.symbol):
        logger.warning(
            f"[{s_state.symbol}] [TRADING HOURS REJECTED] Fora da janela operacional permitida para {s_state.symbol}. Ordem nao enviada."
        )
        return

    # 2. FILTRO DE TENDENCIA MULTI-TIMEFRAME (MTF):
    if getattr(config, "MTF_FILTER_ENABLED", True):
        if not indicators.check_mtf_trend(s_state.symbol, config.TIMEFRAME_NAME, side.name):
            logger.warning(
                f"[{s_state.symbol}] [MTF REJECTED] Operacao de {side.name} nao confirmada "
                f"pela tendencia no timeframe superior."
            )
            return

    # 3. FILTRO DE VOLUME RELATIVO (RVOL):
    if getattr(config, "RVOL_FILTER_ENABLED", True):
        rvol_ratio, curr_v, avg_v = indicators.calculate_rvol(all_rates, config.RVOL_LOOKBACK)
        if rvol_ratio < config.RVOL_THRESHOLD:
            logger.warning(
                f"[{s_state.symbol}] [RVOL REJECTED] Volume da vela (RVOL {rvol_ratio:.2f}x) "
                f"abaixo do limiar minimo de {config.RVOL_THRESHOLD}x a media ({avg_v:.0f})."
            )
            return

    # 4. FILTRO DE PERDA MAXIMA DIARIA (DAILY MAX LOSS):
    balance = risk_calculator.get_account_balance()
    if config.MAX_DAILY_LOSS_PERCENT is not None:
        daily_pnl = tracker.get_daily_pnl()
        max_daily_loss_curr = balance * (config.MAX_DAILY_LOSS_PERCENT / 100.0)
        if daily_pnl <= -max_daily_loss_curr:
            logger.warning(
                f"[{s_state.symbol}] [DAILY MAX LOSS SHIELD] Limite de perda diaria (R$ {abs(daily_pnl):.2f}) "
                f"atingiu o teto maximo de {config.MAX_DAILY_LOSS_PERCENT}% do saldo (R$ {max_daily_loss_curr:.2f}). "
                f"Novas ordens bloqueadas hoje."
            )
            return

    s_state.candle_referencia = candle_ref
    s_state.partial_exit_done = False  # Reset para nova entrada (importante para 9.2)

    if side == TradeSide.BUY:
        entry_price = candle_ref[2] + tick_size * config.TICK_OFFSET  # high + 1 tick
        sl_price = candle_ref[3] - tick_size * config.TICK_OFFSET  # low - 1 tick
    else:
        entry_price = candle_ref[3] - tick_size * config.TICK_OFFSET  # low - 1 tick
        sl_price = candle_ref[2] + tick_size * config.TICK_OFFSET  # high + 1 tick

    # Ajuste ATR dinamico no stop
    sl_price = _apply_atr_adjustment(s_state.symbol, entry_price, sl_price, all_rates)

    # 3. CALCULADORA DE RISCO & DIMENSIONAMENTO DINAMICO DE LOTE:
    volume, risk_curr, is_safe, reason = risk_calculator.calculate_position_size(
        symbol=s_state.symbol,
        entry_price=entry_price,
        sl_price=sl_price,
        balance=balance,
    )
    if not is_safe:
        logger.warning(f"[{s_state.symbol}] {reason}")
        return

    s_state.entry_price = entry_price
    s_state.sl_price = sl_price

    if side == TradeSide.BUY:
        if setup_type == "9.2":
            result = executor.place_buy_stop_92(s_state.symbol, entry_price, sl_price, volume=volume)
        else:
            result = executor.place_buy_stop(s_state.symbol, entry_price, sl_price, volume=volume)
    else:
        if setup_type == "9.2":
            result = executor.place_sell_stop_92(s_state.symbol, entry_price, sl_price, volume=volume)
        else:
            result = executor.place_sell_stop(s_state.symbol, entry_price, sl_price, volume=volume)

    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        s_state.pending_order_ticket = result.order
        s_state.state = State.SIGNAL_READY
        s_state.position_type = side
        s_state.setup_type = setup_type
        logger.info(
            f"[{s_state.symbol}] Ordem {side.name} STOP colocada ({setup_type}). "
            f"Ticket={result.order} Entry={entry_price} SL={sl_price} Volume={volume} (Risco: R$ {risk_curr:.2f})"
        )
        _save_states()
    else:
        logger.error(
            f"[{s_state.symbol}] Falha ao colocar ordem {side.name} STOP. "
            f"Retcode: {result.retcode if result else 'N/A'}"
        )


def _apply_atr_adjustment(symbol, entry_price, sl_price, all_rates):
    """Aplica ajuste de volatilidade ATR ao stop loss."""
    atr_data = indicators.get_atr_ratio(all_rates)
    if atr_data is None:
        return sl_price

    atr_current, atr_avg, ratio = atr_data

    if ratio > config.ATR_HIGH_VOL_THRESHOLD:
        # Stop alargado
        distance = abs(entry_price - sl_price)
        new_distance = distance * ratio * config.ATR_DAMPING_FACTOR
        if entry_price > sl_price:  # BUY: stop abaixo
            new_sl = entry_price - new_distance
        else:  # SELL: stop acima
            new_sl = entry_price + new_distance
        logger.info(f"[{symbol}] Stop alargado por ATR (ratio={ratio:.2f}). "
                    f"SL original={sl_price:.5f} → SL ajustado={new_sl:.5f}")
        return new_sl

    return sl_price


# --- SIGNAL_READY ---

def _handle_signal_ready(s_state, ema9_values):
    orders = executor.get_current_orders(s_state.symbol)
    our_orders = [o for o in orders if o.magic == config.MAGIC and o.ticket == s_state.pending_order_ticket]

    if not our_orders:
        # Verificar se virou posicao (ordem preenchida)
        positions = executor.get_current_positions(s_state.symbol)
        our_positions = [p for p in positions if p.magic == config.MAGIC]

        if our_positions:
            s_state.state = State.IN_POSITION
            s_state.position_ticket = our_positions[0].ticket
            s_state.position_type = TradeSide.BUY if our_positions[0].type == mt5.POSITION_TYPE_BUY else TradeSide.SELL
            s_state.pending_order_ticket = None
            logger.info(f"[{s_state.symbol}] Ordem acionada! IN_POSITION ({s_state.setup_type}). "
                        f"Posicao={s_state.position_ticket}")
            # Registrar entrada no tracker
            tracker.record_entry(
                symbol=s_state.symbol,
                side=s_state.position_type.name,
                setup_type=s_state.setup_type,
                entry_price=s_state.entry_price,
                sl_price=s_state.sl_price,
                volume=config.VOLUME_INITIAL,
                ticket=s_state.position_ticket,
            )
            _save_states()
        else:
            ticket = s_state.pending_order_ticket
            _reset_to_scanning(s_state)
            logger.warning(f"[{s_state.symbol}] Ordem {ticket} nao encontrada. Voltando a SCANNING.")
            _save_states()
        return

    # Verificar se EMA9 virou contra (cancelar ordem)
    virou_contra = False
    if s_state.position_type == TradeSide.BUY and indicators.check_virou_para_baixo(ema9_values):
        virou_contra = True
    elif s_state.position_type == TradeSide.SELL and indicators.check_virou_para_cima(ema9_values):
        virou_contra = True

    if virou_contra:
        ticket = s_state.pending_order_ticket
        logger.info(f"[{s_state.symbol}] EMA9 virou contra. Cancelando ordem {ticket}.")
        result = executor.cancel_order(ticket)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            _reset_to_scanning(s_state)
            logger.info(f"[{s_state.symbol}] Ordem {ticket} cancelada.")
            _save_states()
        else:
            logger.error(f"[{s_state.symbol}] Falha ao cancelar ordem {ticket}. "
                            f"Retcode: {result.retcode if result else 'N/A'}")  


# --- IN_POSITION ---

def _handle_in_position(s_state, ema9_values, current_close, candle_fechado, symbol_info, all_rates):
    positions = executor.get_current_positions(s_state.symbol)
    our_positions = [p for p in positions if p.magic == config.MAGIC and p.ticket == s_state.position_ticket]

    if not our_positions:
        ticket = s_state.position_ticket
        _reset_to_scanning(s_state)
        logger.warning(f"[{s_state.symbol}] Posicao {ticket} nao encontrada. Voltando a SCANNING.")
        _save_states()
        return

    position = our_positions[0]
    current_volume = position.volume

    # --- BREAKEVEN AUTOMATICO ---
    if config.ENABLE_BREAKEVEN and s_state.entry_price and s_state.position_ticket:
        atr_data = indicators.get_atr_ratio(all_rates)
        if atr_data:
            atr_val = atr_data[0]
            trigger_distance = atr_val * config.BREAKEVEN_ATR_RATIO
            current_sl = getattr(position, "sl", 0.0) or 0.0

            if s_state.position_type == TradeSide.BUY:
                gain = current_close - s_state.entry_price
                if gain >= trigger_distance and current_sl < s_state.entry_price:
                    logger.info(
                        f"[{s_state.symbol}] [BREAKEVEN ACTIVATED] Ganho de {gain:.5f} atingiu {config.BREAKEVEN_ATR_RATIO}x ATR ({trigger_distance:.5f}). "
                        f"Ajustando SL para preco de entrada ({s_state.entry_price:.5f})."
                    )
                    executor.modify_position_sl(s_state.position_ticket, s_state.symbol, s_state.entry_price)
            elif s_state.position_type == TradeSide.SELL:
                gain = s_state.entry_price - current_close
                if gain >= trigger_distance and (current_sl > s_state.entry_price or current_sl == 0.0):
                    logger.info(
                        f"[{s_state.symbol}] [BREAKEVEN ACTIVATED] Ganho de {gain:.5f} atingiu {config.BREAKEVEN_ATR_RATIO}x ATR ({trigger_distance:.5f}). "
                        f"Ajustando SL para preco de entrada ({s_state.entry_price:.5f})."
                    )
                    executor.modify_position_sl(s_state.position_ticket, s_state.symbol, s_state.entry_price)


    # --- SAIDA PARCIAL ---
    if config.PARTIAL_EXIT_ENABLED and not s_state.partial_exit_done and s_state.candle_referencia and s_state.entry_price:
        amplitude = indicators.amplitude_candle(s_state.candle_referencia)
        volume_to_close = config.VOLUME_INITIAL * config.PARTIAL_EXIT_PERCENT

        # Alvo adaptativo: ajusta multiplicador baseado na volatilidade recente
        target_mult = config.PARTIAL_EXIT_TARGET
        if config.ADAPTIVE_TARGET_ENABLED:
            adaptive = indicators.adaptive_target_multiplier(all_rates)
            if adaptive:
                median_amp, multiplier = adaptive
                target_mult = config.PARTIAL_EXIT_TARGET * multiplier
                if multiplier != 1.0:
                    logger.debug(f"[{s_state.symbol}] Alvo adaptativo: mult={multiplier:.1f} "
                                 f"(mediana={median_amp:.5f}, ref={amplitude:.5f})")

        if s_state.position_type == TradeSide.BUY:
            target_price = s_state.entry_price + (amplitude * target_mult)
            if current_close >= target_price and current_volume >= volume_to_close:
                logger.info(f"[{s_state.symbol}] Alvo parcial BUY atingido ({target_price:.5f}, "
                            f"mult={target_mult:.1f}). Fechando {volume_to_close} lote.")
                result = executor.close_partial_position(s_state.position_ticket, s_state.symbol, volume_to_close)
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    s_state.partial_exit_done = True
                    tracker.record_partial_exit(s_state.position_ticket, current_close, volume_to_close)
                    _save_states()
                else:
                    logger.error(f"[{s_state.symbol}] Falha fechamento parcial. "
                                 f"Retcode: {result.retcode if result else 'N/A'}")

        elif s_state.position_type == TradeSide.SELL:
            target_price = s_state.entry_price - (amplitude * target_mult)
            if current_close <= target_price and current_volume >= volume_to_close:
                logger.info(f"[{s_state.symbol}] Alvo parcial SELL atingido ({target_price:.5f}, "
                            f"mult={target_mult:.1f}). Fechando {volume_to_close} lote.")
                result = executor.close_partial_position(s_state.position_ticket, s_state.symbol, volume_to_close)
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    s_state.partial_exit_done = True
                    tracker.record_partial_exit(s_state.position_ticket, current_close, volume_to_close)
                    _save_states()
                else:
                    logger.error(f"[{s_state.symbol}] Falha fechamento parcial. "
                                 f"Retcode: {result.retcode if result else 'N/A'}")

    # --- SAIDA FINAL PELA EMA9 ---
    virou_contra = False
    if s_state.position_type == TradeSide.BUY and indicators.check_virou_para_baixo(ema9_values):
        virou_contra = True
    elif s_state.position_type == TradeSide.SELL and indicators.check_virou_para_cima(ema9_values):
        virou_contra = True

    if virou_contra:
        ticket = s_state.position_ticket
        logger.info(f"[{s_state.symbol}] EMA9 virou contra posicao. Fechando {ticket}.")
        result = executor.close_full_position(ticket, s_state.symbol, s_state.position_type)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            # Determinar se saiu com lucro (comparar preco de saida com entry)
            exit_profit = _check_exit_profit(s_state, current_close)
            logger.info(f"[{s_state.symbol}] Posicao fechada. Lucro: {exit_profit}")

            # Registrar saida no tracker
            tracker.record_exit(ticket, current_close,
                              result="win" if exit_profit else "loss")

            # Se saiu com lucro e 9.2 habilitado, ir para WATCHING_92
            if config.SETUP_92_ENABLED and exit_profit:
                original_side = s_state.position_type
                s_state.state = State.WATCHING_92
                s_state.position_ticket = None
                s_state.pending_order_ticket = None
                s_state.partial_exit_done = False
                s_state.watching_92_candles = 0
                s_state.exit_profit = True
                # Manter position_type e candle_referencia para contexto do 9.2
                logger.info(f"[{s_state.symbol}] Saida com lucro. Entrando em WATCHING_92 ({original_side.name}).")
            else:
                _reset_to_scanning(s_state)

            _save_states()
        else:
            logger.error(f"[{s_state.symbol}] Falha ao fechar posicao {ticket}. "
                         f"Retcode: {result.retcode if result else 'N/A'}")


def _check_exit_profit(s_state, current_close):
    """Verifica se a saida foi com lucro baseado no preco de entrada."""
    if s_state.entry_price is None:
        return False
    if s_state.position_type == TradeSide.BUY:
        return current_close > s_state.entry_price
    else:
        return current_close < s_state.entry_price


# --- WATCHING_92 ---

def _handle_watching_92(s_state, candle_fechado, ema9_values, filtro_compra_ok, filtro_venda_ok, symbol_info, all_rates):
    """Monitora para entrada no Setup 9.2.
    Apos sair de IN_POSITION com lucro, espera pullback a EMA9 com EMA9 retomando direcao.
    """
    s_state.watching_92_candles += 1
    is_long = (s_state.position_type == TradeSide.BUY)
    logger.info(f"[{s_state.symbol}] WATCHING_92 candle {s_state.watching_92_candles} | is_long={is_long}")

    # Timeout: se passou muitos candles sem sinal 9.2, voltar a SCANNING
    if s_state.watching_92_candles > config.SETUP_92_MAX_CANDLES_WATCHING:
        logger.info(f"[{s_state.symbol}] Timeout WATCHING_92 ({s_state.watching_92_candles} candles). Voltando a SCANNING.")
        _reset_to_scanning(s_state)
        _save_states()
        return

    # Verificar se EMA9 virou definitivamente contra (>= N candles)
    candles_against = indicators.count_ema9_against(ema9_values, is_long)
    if candles_against >= config.SETUP_92_EMA_AGAINST_LIMIT:
        logger.info(f"[{s_state.symbol}] EMA9 virou contra por {candles_against} candles. Cancelando WATCHING_92.")
        _reset_to_scanning(s_state)
        _save_states()
        return

    # Verificar pullback: candle toca EMA9 E EMA9 manteve/retomou direcao favoravel
    ema9_current = ema9_values[-1] if ema9_values else None
    if ema9_current is None:
        return

    pullback = indicators.check_pullback_to_ema9(candle_fechado, ema9_current, is_long)
    ema9_favoravel = indicators.check_ema9_retomou_direcao(ema9_values, is_long)

    if pullback and ema9_favoravel:
        # Aplicar filtro EMA21
        if is_long and not filtro_compra_ok:
            logger.info(
                f"[{s_state.symbol}] Pullback 9.2 detectado mas EMA21 nao valida para compra. "
                "Aguarda confirmação de tendencia maior antes de entrar."
            )
            return
        if not is_long and not filtro_venda_ok:
            logger.info(
                f"[{s_state.symbol}] Pullback 9.2 detectado mas EMA21 nao valida para venda. "
                "Aguarda confirmação de tendencia maior antes de entrar."
            )
            return

        logger.info(
            f"[{s_state.symbol}] Setup 9.2 detectado: pullback à EMA9 + EMA9 favorável. "
            "Preparando ordem de entrada 9.2."
        )
        tick_size = executor.get_tick_size(symbol_info)
        _place_entry_order(s_state, candle_fechado, s_state.position_type, tick_size, symbol_info, all_rates, "9.2")
    else:
        if pullback:
            logger.info(
                f"[{s_state.symbol}] Pullback 9.2 detectado, mas EMA9 ainda nao retomou a direcao favoravel. "
                f"EMA9 favoravel={ema9_favoravel}."
            )
        else:
            logger.info(
                f"[{s_state.symbol}] WATCHING_92 ativo: aguardando pullback à EMA9. "
                f"Pullback detectado={pullback}, EMA9 favoravel={ema9_favoravel}."
            )
