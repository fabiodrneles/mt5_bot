"""
TUI (Terminal User Interface) para configuracao do MT5Bot.
Interface limpa e neutra para configurar todos os parametros antes de operar.
"""
import os
import sys
import getpass
import shutil
import textwrap

import MetaTrader5 as mt5
import config


# --- Cores ANSI (neutras/clean) ---
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
WHITE = "\033[97m"
GRAY = "\033[90m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


VERSION = "1.3.0"


def print_header():
    term_w = shutil.get_terminal_size((80, 20)).columns
    max_box_w = min(64, max(50, term_w - 10))

    title_text = f"MT5Bot v{VERSION}"
    slogan = "Measured, disciplined execution — performance varies with market conditions."
    slogan_lines = textwrap.wrap(slogan, width=max_box_w - 6)

    content_width = max(len(title_text), *(len(line) for line in slogan_lines))
    inner_w = min(max_box_w - 4, max(40, content_width))
    box_w = inner_w + 4

    top = f"{BOLD}{WHITE}    ╔" + "═" * box_w + "╗\n"
    blank = f"    ║{' ' * box_w}║\n"

    title_line = title_text.center(inner_w)
    title_row = f"    ║  {BOLD}{WHITE}{title_line}{RESET}  ║\n"

    slogan_rows = ""
    for ln in slogan_lines:
        slogan_rows += f"    ║  {ln.center(inner_w)}  ║\n"

    bottom = f"    ╚" + "═" * box_w + "╝\n"
    print(top + blank + title_row + slogan_rows + blank + bottom + RESET)


def print_section(title):
    print(f"\n{BOLD}{CYAN}  [{title}]{RESET}")
    print(f"  {DIM}{'─' * 50}{RESET}")


def print_param(key, value, description=""):
    desc = f"  {DIM}{description}{RESET}" if description else ""
    print(f"    {WHITE}{key:<28}{RESET} {GREEN}{value}{RESET}{desc}")


def print_menu_option(num, label, current=""):
    cur = f" {DIM}(atual: {current}){RESET}" if current else ""
    print(f"    {BOLD}{num}.{RESET} {label}{cur}")


def input_prompt(msg, default=None):
    if default is not None:
        raw = input(f"  {GRAY}>{RESET} {msg} [{GREEN}{default}{RESET}]: ").strip()
        return raw if raw else str(default)
    return input(f"  {GRAY}>{RESET} {msg}: ").strip()


def input_password(msg):
    """Input de senha sem exibir caracteres."""
    return getpass.getpass(f"  {GRAY}>{RESET} {msg}: ")


# ============================================================
# CONEXAO MT5
# ============================================================

def connect_mt5_tui():
    """Tela de conexao com o MetaTrader 5.
    Tenta conectar automaticamente. Se falhar, pede credenciais.
    Retorna True se conectado, False se cancelado.
    """
    print_section("CONEXAO MetaTrader 5")
    print()

    # Tentar inicializar MT5 (ja logado no terminal)
    print(f"    {DIM}Tentando conectar ao terminal MT5...{RESET}")

    if mt5.initialize():
        account = mt5.account_info()
        if account:
            print(f"    {GREEN}Conectado automaticamente!{RESET}")
            print()
            print_param("Conta", account.login)
            print_param("Nome", account.name)
            print_param("Servidor", account.server)
            print_param("Balance", f"{account.balance:.2f} {account.currency}")
            print_param("Tipo", "Demo" if account.trade_mode == 0 else "Real")
            print()

            resp = input_prompt("Usar esta conta? (s/n)", "s")
            if resp.lower() in ("s", "sim", "y", "yes", ""):
                return True
            else:
                mt5.shutdown()
    else:
        print(f"    {YELLOW}Terminal MT5 nao detectado ou nao esta logado.{RESET}")
        print()

    # Login manual
    print()
    print(f"    {DIM}Para conectar, informe os dados da sua conta MT5.{RESET}")
    print(f"    {DIM}Voce encontra essas informacoes no email da corretora{RESET}")
    print(f"    {DIM}ou nas configuracoes do seu terminal MT5.{RESET}")
    print()

    # Pedir path do MT5 (opcional)
    mt5_path = input_prompt("Caminho do terminal.exe (Enter=automatico)", "")

    login_str = input_prompt("Numero da conta (login)")
    if not login_str:
        print(f"    {RED}Login obrigatorio. Cancelando.{RESET}")
        return False

    try:
        login = int(login_str)
    except ValueError:
        print(f"    {RED}Login deve ser numerico. Cancelando.{RESET}")
        return False

    password = input_password("Senha da conta")
    if not password:
        print(f"    {RED}Senha obrigatoria. Cancelando.{RESET}")
        return False

    server = input_prompt("Servidor (ex: MetaQuotes-Demo)")
    if not server:
        print(f"    {RED}Servidor obrigatorio. Cancelando.{RESET}")
        return False

    # Tentar conectar
    print(f"\n    {DIM}Conectando...{RESET}")

    init_kwargs = {
        "login": login,
        "password": password,
        "server": server,
    }
    if mt5_path:
        init_kwargs["path"] = mt5_path

    if not mt5.initialize(**init_kwargs):
        error = mt5.last_error()
        print(f"    {RED}Falha na conexao: {error}{RESET}")
        print()
        print(f"    {DIM}Verifique:{RESET}")
        print(f"    {DIM}  - O MetaTrader 5 esta instalado?{RESET}")
        print(f"    {DIM}  - Login, senha e servidor estao corretos?{RESET}")
        print(f"    {DIM}  - O terminal MT5 consegue conectar manualmente?{RESET}")
        print()

        resp = input_prompt("Tentar novamente? (s/n)", "s")
        if resp.lower() in ("s", "sim", "y", "yes", ""):
            return connect_mt5_tui()
        return False

    account = mt5.account_info()
    if account:
        print(f"    {GREEN}Conectado com sucesso!{RESET}")
        print()
        print_param("Conta", account.login)
        print_param("Nome", account.name)
        print_param("Servidor", account.server)
        print_param("Balance", f"{account.balance:.2f} {account.currency}")
        print()
        return True
    else:
        print(f"    {RED}Conexao estabelecida mas nao foi possivel obter info da conta.{RESET}")
        return False


# ============================================================
# ATIVOS
# ============================================================

def select_symbols_tui():
    """Menu de selecao de ativos."""
    print_section("ATIVOS")
    print()
    for i, sym in enumerate(config.AVAILABLE_SYMBOLS, 1):
        # Verificar se ativo existe no broker
        info = mt5.symbol_info(sym)
        status = f"{GREEN}disponivel{RESET}" if info else f"{RED}indisponivel{RESET}"
        print(f"    {BOLD}{i}.{RESET} {sym}  {status}")

    print_menu_option(len(config.AVAILABLE_SYMBOLS) + 1, "Todos os disponiveis")
    print_menu_option(len(config.AVAILABLE_SYMBOLS) + 2, "Combinacao (ex: 1,3)")
    print()

    while True:
        opcao = input_prompt("Selecione")

        if opcao == str(len(config.AVAILABLE_SYMBOLS) + 1):
            config.SYMBOLS = [s for s in config.AVAILABLE_SYMBOLS if mt5.symbol_info(s)]
            break
        elif opcao == str(len(config.AVAILABLE_SYMBOLS) + 2):
            indices_str = input_prompt("Indices separados por virgula (ex: 1,3)")
            try:
                indices = [int(x.strip()) for x in indices_str.split(",")]
                selected = []
                for idx in indices:
                    if 1 <= idx <= len(config.AVAILABLE_SYMBOLS):
                        sym = config.AVAILABLE_SYMBOLS[idx - 1]
                        if mt5.symbol_info(sym):
                            selected.append(sym)
                        else:
                            print(f"    {YELLOW}{sym} indisponivel, ignorado.{RESET}")
                if selected:
                    config.SYMBOLS = selected
                    break
                else:
                    print(f"    {RED}Nenhum ativo valido.{RESET}")
            except ValueError:
                print(f"    {RED}Formato invalido.{RESET}")
        elif opcao.isdigit() and 1 <= int(opcao) <= len(config.AVAILABLE_SYMBOLS):
            sym = config.AVAILABLE_SYMBOLS[int(opcao) - 1]
            if mt5.symbol_info(sym):
                config.SYMBOLS = [sym]
                break
            else:
                print(f"    {RED}{sym} nao disponivel no broker.{RESET}")
        else:
            print(f"    {RED}Opcao invalida.{RESET}")

    # Ativar simbolos no Market Watch
    for sym in config.SYMBOLS:
        mt5.symbol_select(sym, True)

    print(f"\n    {DIM}Selecionados:{RESET} {GREEN}{', '.join(config.SYMBOLS)}{RESET}")


# ============================================================
# VOLUME
# ============================================================

def configure_volume_tui():
    """Configuracao de volume."""
    print_section("VOLUME")
    print()
    print_param("Volume por operacao", f"{config.VOLUME_INITIAL} lote")
    print(f"    {DIM}Pressione Enter para manter o valor default.{RESET}")
    print()
    resp = input_prompt("Volume (Enter=manter)", config.VOLUME_INITIAL)
    try:
        vol = float(resp)
        if vol > 0:
            config.VOLUME_INITIAL = vol
        else:
            print(f"    {YELLOW}Valor invalido. Mantendo {config.VOLUME_INITIAL}{RESET}")
    except ValueError:
        print(f"    {YELLOW}Mantendo {config.VOLUME_INITIAL}{RESET}")


# ============================================================
# ESTRATEGIA
# ============================================================

def configure_strategy_tui():
    """Configuracao de estrategia."""
    print_section("ESTRATEGIA")
    print()
    print_param("EMA rapida", config.EMA_PERIOD, "periodo para sinal")
    print_param("EMA filtro", config.EMA_FILTER_PERIOD, "filtro de tendencia")
    print_param("Setup 9.2", "Ativado" if config.SETUP_92_ENABLED else "Desativado")
    print_param("Filtro Flat", "Ativado" if config.FLAT_FILTER_ENABLED else "Desativado")
    print()

    resp = input_prompt("Ativar Setup 9.2? (s/n, Enter=manter)", "s" if config.SETUP_92_ENABLED else "n")
    if resp.lower() == "s":
        config.SETUP_92_ENABLED = True
    elif resp.lower() == "n":
        config.SETUP_92_ENABLED = False


# ============================================================
# RISCO
# ============================================================

def configure_risk_tui():
    """Configuracao de risco."""
    print_section("GESTAO DE RISCO")
    print()
    print_param("Saida parcial", "Ativada" if config.PARTIAL_EXIT_ENABLED else "Desativada")
    print_param("Percentual parcial", f"{int(config.PARTIAL_EXIT_PERCENT * 100)}%", "do volume")
    print_param("Alvo parcial", f"{int(config.PARTIAL_EXIT_TARGET * 100)}%", "da amplitude")
    print_param("Alvo adaptativo", "Ativado" if config.ADAPTIVE_TARGET_ENABLED else "Desativado", "ajusta alvo pela volatilidade")
    print_param("ATR dinamico", f"Threshold {config.ATR_HIGH_VOL_THRESHOLD}x")
    print_param("Tick offset (SL/Entry)", f"{config.TICK_OFFSET} tick(s)")
    print()

    resp = input_prompt("Ativar saida parcial? (s/n, Enter=manter)", "s" if config.PARTIAL_EXIT_ENABLED else "n")
    if resp.lower() == "s":
        config.PARTIAL_EXIT_ENABLED = True
    elif resp.lower() == "n":
        config.PARTIAL_EXIT_ENABLED = False

    resp = input_prompt("Ativar alvo adaptativo? (s/n, Enter=manter)", "s" if config.ADAPTIVE_TARGET_ENABLED else "n")
    if resp.lower() == "s":
        config.ADAPTIVE_TARGET_ENABLED = True
    elif resp.lower() == "n":
        config.ADAPTIVE_TARGET_ENABLED = False

    resp = input_prompt("ATR threshold para alargar stop (Enter=manter)", config.ATR_HIGH_VOL_THRESHOLD)
    try:
        val = float(resp)
        if val > 0:
            config.ATR_HIGH_VOL_THRESHOLD = val
    except ValueError:
        pass


# ============================================================
# INTERVALOS
# ============================================================

def configure_timing_tui():
    """Configuracao de intervalos."""
    print_section("INTERVALOS")
    print()
    print_param("Intervalo de scan", f"{config.SCAN_INTERVAL_SECONDS}s")
    print_param("Retry em erro", f"{config.RETRY_INTERVAL_SECONDS}s")
    print_param("Candles historicos", config.RATES_COUNT)
    print()

    resp = input_prompt("Intervalo de scan em segundos (Enter=manter)", config.SCAN_INTERVAL_SECONDS)
    try:
        val = int(resp)
        if val >= 5:
            config.SCAN_INTERVAL_SECONDS = val
    except ValueError:
        pass


# ============================================================
# TIMEFRAME
# ============================================================

def configure_timeframe_tui():
    """Configuracao de timeframe."""
    print_section("TIMEFRAME")
    print()
    print_param("Timeframe atual", config.TIMEFRAME_NAME)
    print(f"    {DIM}Selecione um timeframe da lista abaixo.{RESET}")
    print()

    tf_list = list(config.AVAILABLE_TIMEFRAMES.keys())
    for i, tf_name in enumerate(tf_list, 1):
        current = " (atual)" if tf_name == config.TIMEFRAME_NAME else ""
        print(f"    {BOLD}{i}.{RESET} {tf_name}{f'{DIM}{current}{RESET}' if current else ''}")

    print(f"    {BOLD}0.{RESET} Manter atual ({config.TIMEFRAME_NAME})")
    print()

    while True:
        opcao = input_prompt("Selecione")

        if opcao == "0" or opcao == "":
            break

        if opcao.isdigit() and 1 <= int(opcao) <= len(tf_list):
            tf_name = tf_list[int(opcao) - 1]
            config.TIMEFRAME = config.AVAILABLE_TIMEFRAMES[tf_name]
            config.TIMEFRAME_NAME = tf_name
            print(f"\n    {DIM}Timeframe selecionado:{RESET} {GREEN}{tf_name}{RESET}")
            break
        else:
            print(f"    {RED}Opcao invalida.{RESET}")


# ============================================================
# RESUMO E FLOWS
# ============================================================

def show_summary():
    """Mostra resumo final antes de iniciar."""
    print_section("RESUMO DA CONFIGURACAO")
    print()

    account = mt5.account_info()
    if account:
        print_param("Conta", f"{account.login} @ {account.server}")

    print_param("Ativos", ", ".join(config.SYMBOLS))
    print_param("Volume", f"{config.VOLUME_INITIAL} lote")
    print_param("Timeframe", config.TIMEFRAME_NAME)
    print_param("Setup 9.1", "Ativado")
    print_param("Setup 9.2", "Ativado" if config.SETUP_92_ENABLED else "Desativado")
    print_param("Saida parcial",
                f"{int(config.PARTIAL_EXIT_PERCENT*100)}% a {int(config.PARTIAL_EXIT_TARGET*100)}% amplitude"
                if config.PARTIAL_EXIT_ENABLED else "Desativada")
    print_param("Alvo adaptativo", "Ativado" if config.ADAPTIVE_TARGET_ENABLED else "Desativado")
    print_param("ATR dinamico", f">{config.ATR_HIGH_VOL_THRESHOLD}x alarga stop")
    print_param("Filtro Flat", "Ativado" if config.FLAT_FILTER_ENABLED else "Desativado")
    print_param("Magic Number", config.MAGIC)
    print()


def run_tui():
    """Executa a TUI completa de configuracao.
    Retorna True para iniciar, False para sair.
    """
    clear_screen()
    print_header()

    # 1. Conexao MT5
    if not connect_mt5_tui():
        return False

    # 2. Selecao de ativos
    select_symbols_tui()
    if not config.SYMBOLS:
        print(f"    {RED}Nenhum ativo disponivel. Encerrando.{RESET}")
        return False

    # 3. Timeframe
    configure_timeframe_tui()

    # 4. Volume
    configure_volume_tui()

    # 5. Estrategia
    configure_strategy_tui()

    # 6. Risco
    configure_risk_tui()

    # 7. Intervalos
    configure_timing_tui()

    # Resumo final
    clear_screen()
    print_header()
    show_summary()

    print(f"  {DIM}{'─' * 50}{RESET}")
    print()
    resp = input_prompt("Iniciar bot? (s/n)", "s")

    if resp.lower() in ("s", "sim", "y", "yes", ""):
        print(f"\n  {GREEN}Iniciando operacao...{RESET}\n")
        return True
    else:
        print(f"\n  {YELLOW}Operacao cancelada.{RESET}\n")
        mt5.shutdown()
        return False


def run_quick_start():
    """Inicio rapido — apenas conexao, ativo e volume."""
    clear_screen()
    print_header()
    print(f"  {DIM}Modo rapido — configuracoes default{RESET}\n")

    # Conexao
    if not connect_mt5_tui():
        return False

    # Ativo + volume
    select_symbols_tui()
    if not config.SYMBOLS:
        print(f"    {RED}Nenhum ativo disponivel.{RESET}")
        return False

    configure_volume_tui()

    # Resumo
    show_summary()

    print(f"  {DIM}{'─' * 50}{RESET}")
    print()
    resp = input_prompt("Iniciar bot? (s/n)", "s")

    if resp.lower() in ("s", "sim", "y", "yes", ""):
        print(f"\n  {GREEN}Iniciando operacao...{RESET}\n")
        return True
    else:
        print(f"\n  {YELLOW}Operacao cancelada.{RESET}\n")
        mt5.shutdown()
        return False