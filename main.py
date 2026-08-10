"""
MT5Bot — Bot de trading automatizado.
Ponto de entrada principal e loop de operacao.
"""
import MetaTrader5 as mt5
import time
import signal
import sys
from datetime import datetime
from collections import namedtuple
import pytz

import config
import logger
import strategy
import executor
import tracker
import tui
import dashboard
import threading

# Namedtuple para candles
Candle = namedtuple("Candle", ["time", "open", "high", "low", "close", "tick_vol", "spread", "real_vol"])

# Flag para graceful shutdown
_shutdown_requested = False
# shutdown action: 'save-only' (default), 'wait-flat', 'cancel-open'
_shutdown_action = None


def _signal_handler(sig, frame):
    global _shutdown_requested
    _shutdown_requested = True
    logger.info("Shutdown solicitado (Ctrl+C). Finalizando apos cleanup...")


def parse_shutdown_action(argv):
    """Parseia `--shutdown-action` de uma lista argv e retorna o valor valido ou None.

    Retorna uma das: 'save-only', 'wait-flat', 'cancel-open', ou None se nao definido/valido.
    """
    try:
        if "--shutdown-action" in argv:
            idx = argv.index("--shutdown-action")
            if idx + 1 < len(argv):
                val = argv[idx + 1].lower()
                if val in ("save-only", "wait-flat", "cancel-open"):
                    return val
    except Exception:
        pass
    return None


def wait_until_flat(max_seconds):
    """Aguarda até que nao haja posicoes nem ordens pendentes do bot.

    Retorna True se ficou flat antes do timeout, False se timeout expirou.
    Usa `executor.get_current_positions` e `executor.get_current_orders`.
    """
    start = time.time()
    while True:
        any_positions = False
        any_orders = False
        for symbol in config.SYMBOLS:
            positions = executor.get_current_positions(symbol)
            orders = executor.get_current_orders(symbol)
            if any([p for p in positions if getattr(p, 'magic', None) == config.MAGIC]):
                any_positions = True
            if any([o for o in orders if getattr(o, 'magic', None) == config.MAGIC]):
                any_orders = True
        if not any_positions and not any_orders:
            return True
        if time.time() - start > max_seconds:
            return False
        time.sleep(0.05)


def _cancel_pending_orders():
    """Cancela todas as ordens pendentes do bot antes de encerrar."""
    for symbol in config.SYMBOLS:
        orders = executor.get_current_orders(symbol)
        our_orders = [o for o in orders if o.magic == config.MAGIC]
        for order in our_orders:
            logger.info(f"[{symbol}] Cancelando ordem pendente {order.ticket} no shutdown.")
            executor.cancel_order(order.ticket)


def _ensure_connected():
    """Verifica se MT5 esta conectado. Se nao, tenta reconectar.
    Retorna True se conectado, False se falhou.
    """
    # Teste rapido: account_info retorna None se desconectado
    if mt5.account_info() is not None:
        return True

    # Conexao perdida — tentar reconectar
    logger.warning("Conexao MT5 perdida. Tentando reconectar...")
    mt5.shutdown()
    time.sleep(2)

    if mt5.initialize():
        account = mt5.account_info()
        if account:
            logger.info(f"Reconectado com sucesso: {account.login}")
            # Reativar simbolos no Market Watch
            for sym in config.SYMBOLS:
                mt5.symbol_select(sym, True)
            return True

    logger.error(f"Falha ao reconectar: {mt5.last_error()}")
    return False


def _validate_symbols_on_broker():
    """Valida e ativa simbolos no broker."""
    validated = []
    for sym in config.SYMBOLS:
        info = mt5.symbol_info(sym)
        if info is None:
            logger.warning(f"{sym} nao encontrado no broker. Removido.")
        elif not info.visible:
            mt5.symbol_select(sym, True)
            validated.append(sym)
        else:
            validated.append(sym)
    config.SYMBOLS = validated
    return len(validated) > 0


def run_bot():
    """Loop principal do bot."""
    global _shutdown_requested
    global _shutdown_action

    # Registrar handler para graceful shutdown
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    # MT5 ja conectado pela TUI/dashboard. Verificar conexao.
    account_info = mt5.account_info()
    if account_info is None:
        if not mt5.initialize():
            logger.error(f"Falha ao inicializar MT5: {mt5.last_error()}")
            return
        account_info = mt5.account_info()
        if account_info is None:
            logger.error(f"MT5 nao logado: {mt5.last_error()}")
            mt5.shutdown()
            return

    logger.info(f"Conectado: {account_info.login} ({account_info.name}) | "
                f"Balance: {account_info.balance} {account_info.currency}")

    # Validar simbolos no broker
    if not _validate_symbols_on_broker():
        logger.error("Nenhum ativo valido disponivel no broker.")
        mt5.shutdown()
        return

    # Timezone UTC
    timezone = pytz.timezone("Etc/UTC")
    logger.info(f"Bot iniciado | Ativos: {', '.join(config.SYMBOLS)} | "
                f"Volume: {config.VOLUME_INITIAL} | "
                f"Timeframe: {config.TIMEFRAME_NAME} | "
                f"Setups: 9.1" + (" + 9.2" if config.SETUP_92_ENABLED else ""))

    # Inicializar estados (com persistencia)
    if not strategy.initialize_symbol_states():
        logger.error("Falha ao inicializar estados. Encerrando.")
        mt5.shutdown()
        return

    last_candle_time = {symbol: None for symbol in config.SYMBOLS}
    _consecutive_failures = 0

    # Loop principal
    # Start console watcher thread to accept interactive 'exit' command for immediate shutdown
    def _console_watcher():
        global _shutdown_requested
        global _shutdown_action
        try:
            while not _shutdown_requested:
                try:
                    line = sys.stdin.readline()
                except Exception:
                    break
                if not line:
                    break
                cmd = line.strip().lower()
                if cmd in ('exit', 'quit', 'q'):
                    _shutdown_action = config.SHUTDOWN_DEFAULT_ACTION
                    _shutdown_requested = True
                    logger.info(f"Shutdown solicitado via console input ('exit'). Acao: {_shutdown_action}")
                    break
                if cmd in ('exit now', 'exit cancel', 'exit cancel-open'):
                    _shutdown_action = 'cancel-open'
                    _shutdown_requested = True
                    logger.info("Shutdown solicitado (cancel-open) via console input. Cancelando ordens pendentes e saindo.")
                    break
                if cmd in ('exit when flat', 'exit when-flat', 'exit flat'):
                    _shutdown_action = 'wait-flat'
                    _shutdown_requested = True
                    logger.info("Shutdown solicitado (wait-flat) via console input. Aguardando posicoes fecharem antes de encerrar.")
                    break
        except Exception:
            pass

    watcher = threading.Thread(target=_console_watcher, daemon=True)
    watcher.start()
    while not _shutdown_requested:
        try:
            # --- RECONNECT: verificar se MT5 ainda esta conectado ---
            if not _ensure_connected():
                _consecutive_failures += 1
                wait = min(config.RETRY_INTERVAL_SECONDS * _consecutive_failures, 120)
                logger.warning(f"Sem conexao MT5. Tentativa {_consecutive_failures}. "
                              f"Proxima em {wait}s...")
                time.sleep(wait)
                continue
            _consecutive_failures = 0

            for symbol in list(config.SYMBOLS):
                if _shutdown_requested:
                    break

                # Verificar horario de mercado
                sym_info = mt5.symbol_info(symbol)
                if sym_info and sym_info.trade_mode == mt5.SYMBOL_TRADE_MODE_DISABLED:
                    logger.debug(f"[{symbol}] Mercado fechado. Pulando.")
                    continue

                rates = mt5.copy_rates_from_pos(symbol, config.TIMEFRAME, 0, config.RATES_COUNT)

                if rates is None or len(rates) < config.RATES_COUNT:
                    count = len(rates) if rates is not None else 0
                    logger.warning(f"[{symbol}] Dados insuficientes ({count} rates).")
                    continue

                if len(rates) < 2:
                    continue

                # O ultimo candle completo e rates[-2] (rates[-1] esta formando)
                current_closed_candle = rates[-2]
                candle_dt = datetime.fromtimestamp(current_closed_candle[0], timezone)

                if last_candle_time[symbol] is None or candle_dt > last_candle_time[symbol]:
                    logger.info(f"[{symbol}] Novo candle {config.TIMEFRAME_NAME} fechado: {candle_dt}")
                    last_candle_time[symbol] = candle_dt
                    strategy.evaluate(symbol, current_closed_candle, rates)
                else:
                    logger.debug(f"[{symbol}] Candle {candle_dt} ja processado.")

        except Exception as e:
            logger.error(f"Erro no loop principal: {e}", exc_info=True)
            _consecutive_failures += 1
            time.sleep(config.RETRY_INTERVAL_SECONDS)

        if not _shutdown_requested:
            time.sleep(config.SCAN_INTERVAL_SECONDS)

    # Graceful shutdown
    logger.info("Executando shutdown...")
    # Determine action
    action = _shutdown_action or config.SHUTDOWN_DEFAULT_ACTION
    logger.info(f"Shutdown action: {action}")
    if action == 'cancel-open':
        _cancel_pending_orders()
    elif action == 'wait-flat':
        # Wait until no positions and no pending orders for our magic, or timeout
        logger.info(f'Aguardando posicoes/ordens encerrarem (wait-flat)... max {config.SHUTDOWN_WAIT_SECONDS}s')
        start_wait = time.time()
        while True:
            any_positions = False
            any_orders = False
            for symbol in config.SYMBOLS:
                positions = executor.get_current_positions(symbol)
                orders = executor.get_current_orders(symbol)
                # consider only our positions/orders by magic tag when available
                if any([p for p in positions if getattr(p, 'magic', getattr(p, 'ticket', None)) == config.MAGIC or getattr(p, 'magic', None) == config.MAGIC]):
                    any_positions = True
                if any([o for o in orders if getattr(o, 'magic', getattr(o, 'ticket', None)) == config.MAGIC or getattr(o, 'magic', None) == config.MAGIC]):
                    any_orders = True
            if not any_positions and not any_orders:
                logger.info('Sem posicoes nem ordens pendentes. Prosseguindo com shutdown.')
                break
            if time.time() - start_wait > config.SHUTDOWN_WAIT_SECONDS:
                logger.warning('Timeout aguardando posicoes/ordens. Salvando estado e encerrando mesmo assim.')
                break
            time.sleep(5)
    else:
        # save-only (default) — do not cancel orders, just persist state
        logger.info('Shutdown default (save-only): nao sera cancelada ordens pendentes.')
    strategy._save_states()
    mt5.shutdown()
    logger.info("Bot encerrado.")


def _show_startup_menu():
    """Menu principal de inicializacao."""
    tui.clear_screen()
    tui.print_header()

    print(f"  {tui.BOLD}{tui.WHITE}Como deseja iniciar?{tui.RESET}\n")
    print(f"    {tui.BOLD}1.{tui.RESET} {tui.GREEN}Iniciar direto{tui.RESET}              {tui.DIM}pronto para operar, sem alterar nada{tui.RESET}")
    print(f"    {tui.BOLD}2.{tui.RESET} Configurar no terminal      {tui.DIM}ajustar parametros via CLI{tui.RESET}")
    print(f"    {tui.BOLD}3.{tui.RESET} Configurar no navegador     {tui.DIM}interface visual no browser{tui.RESET}")
    print(f"    {tui.BOLD}4.{tui.RESET} Ver relatorio               {tui.DIM}performance e historico{tui.RESET}")
    print()

    opcao = tui.input_prompt("Opcao", "1")
    return opcao


def main():
    """Entry point da CLI."""
    # Flags de linha de comando
    if "--version" in sys.argv or "-v" in sys.argv:
        print("MT5Bot v1.1.0 — Measured, disciplined execution — performance varies with market conditions.")
        return

    if "--help" in sys.argv or "-h" in sys.argv:
        print("""
  MT5Bot — Measured, disciplined execution — performance varies with market conditions.

  USO:
    mt5bot              Menu principal (recomendado no primeiro uso)
    mt5bot --quick      Conecta e opera direto, sem alterar nada
    mt5bot --report     Relatorio de performance no terminal
    mt5bot --dashboard  Relatorio visual no navegador
    mt5bot --timeframe <TF>  Define o timeframe (ex: M1, M5, H1)
    mt5bot --version    Versao instalada
    mt5bot --help       Esta ajuda

  PRIMEIRO USO:
    1. Execute: mt5bot
    2. Escolha opcao 1 (Iniciar direto)
    3. Conecte sua conta MT5
    4. O bot opera sozinho — apenas observe

  REQUISITOS:
    - Windows 10/11
    - Python 3.10+
    - MetaTrader 5 instalado com conta ativa
""")
        return

    # Processar argumento --timeframe
    if "--timeframe" in sys.argv:
        try:
            tf_index = sys.argv.index("--timeframe")
            if tf_index + 1 < len(sys.argv):
                tf_name = sys.argv[tf_index + 1].upper()
                if tf_name in config.AVAILABLE_TIMEFRAMES:
                    config.TIMEFRAME = config.AVAILABLE_TIMEFRAMES[tf_name]
                    config.TIMEFRAME_NAME = tf_name
                    logger.info(f"Timeframe definido via CLI: {tf_name}")
                else:
                    logger.warning(f"Timeframe '{tf_name}' invalido. Usando padrao: {config.TIMEFRAME_NAME}")
            else:
                logger.warning("Argumento --timeframe requer um valor (ex: --timeframe H1). Usando padrao.")
        except ValueError:
            pass # Nao deveria acontecer pois ja verificamos "--timeframe" in sys.argv


    if "--report" in sys.argv:
        tracker.print_report()
        return

    if "--dashboard" in sys.argv:
        dashboard.open_report()
        return

    # Shutdown action CLI (save-only | wait-flat | cancel-open)
    if "--shutdown-action" in sys.argv:
        try:
            idx = sys.argv.index("--shutdown-action")
            if idx + 1 < len(sys.argv):
                val = sys.argv[idx + 1].lower()
                if val in ("save-only", "wait-flat", "cancel-open"):
                    global _shutdown_action
                    _shutdown_action = val
                    logger.info(f"Shutdown action definido via CLI: {val}")
                else:
                    logger.warning(f"Valor invalido para --shutdown-action: {val}. Usando padrao.")
        except ValueError:
            pass

    # Modo rapido: apenas conecta MT5 e usa config default
    if "--quick" in sys.argv or "-q" in sys.argv:
        tui.clear_screen()
        tui.print_header()
        print(f"  {tui.DIM}Modo rapido — usando configuracao padrao{tui.RESET}\n")

        if not tui.connect_mt5_tui():
            return

        # Usar todos os ativos disponiveis
        config.SYMBOLS = list(config.AVAILABLE_SYMBOLS)
        tui.show_summary()
        print(f"\n  {tui.GREEN}Iniciando...{tui.RESET}\n")

        try:
            run_bot()
        except KeyboardInterrupt:
            pass
        finally:
            _safe_shutdown()
        return

    # Menu principal interativo
    opcao = _show_startup_menu()

    if opcao == "1":
        # Iniciar direto — apenas conectar MT5
        if not tui.connect_mt5_tui():
            return
        config.SYMBOLS = list(config.AVAILABLE_SYMBOLS)
        tui.show_summary()
        print(f"\n  {tui.GREEN}Iniciando com configuracao padrao...{tui.RESET}\n")

    elif opcao == "2":
        # Configurar no terminal (TUI completa)
        if not tui.run_tui():
            return

    elif opcao == "3":
        # Configurar no navegador
        # Primeiro conectar MT5
        if not tui.connect_mt5_tui():
            return
        print(f"\n  {tui.DIM}Abrindo configuracao no navegador...{tui.RESET}")
        if not dashboard.open_config():
            print(f"\n  {tui.YELLOW}Configuracao cancelada ou timeout.{tui.RESET}\n")
            return
        print(f"\n  {tui.GREEN}Configuracao salva via navegador. Iniciando...{tui.RESET}\n")

    elif opcao == "4":
        # Relatorio
        print(f"\n  {tui.DIM}Escolha o formato:{tui.RESET}")
        tui.print_menu_option(1, "Terminal", "texto no terminal")
        tui.print_menu_option(2, "Navegador", "interface visual")
        fmt = tui.input_prompt("Formato", "1")
        if fmt == "2":
            dashboard.open_report()
        else:
            tracker.print_report()
        return

    else:
        print(f"  {tui.RED}Opcao invalida.{tui.RESET}")
        return

    # Rodar o bot
    try:
        run_bot()
    except KeyboardInterrupt:
        pass
    finally:
        _safe_shutdown()

    # Mostrar resumo apos encerrar
    print()
    tracker.print_report()


def _safe_shutdown():
    try:
        mt5.shutdown()
    except Exception:
        pass


if __name__ == "__main__":
    main()