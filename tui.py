"""
TUI (Terminal User Interface) para configuracao do MT5Bot.
Interface limpa e neutra para configurar todos os parametros antes de operar.
"""
import os
import sys
import re
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

VERSION = "1.5.2"


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def _visible_len(text: str) -> int:
    """Calcula o tamanho visível do texto descartando códigos de cor ANSI."""
    return len(re.sub(r'\033\[[0-9;]*m|\x1b\[[0-9;]*m', '', text))


def print_header():
    """Imprime o cabeçalho principal em uma caixa perfeitamente retangular."""
    box_w = 68
    inner_w = box_w - 2  # 66 caracteres entre │ e │

    title_text = f"MT5Bot v{VERSION}"
    slogan = "Measured, disciplined execution — performance varies with market conditions."
    slogan_lines = textwrap.wrap(slogan, width=inner_w - 6)

    top = f"  {BOLD}{CYAN}┌" + "─" * inner_w + f"┐{RESET}"
    bottom = f"  {BOLD}{CYAN}└" + "─" * inner_w + f"┘{RESET}"

    print(top)

    # Linha do título
    t_len = len(title_text)
    t_left = (inner_w - t_len) // 2
    t_right = inner_w - t_len - t_left
    print(f"  {CYAN}│{RESET}{' ' * t_left}{BOLD}{WHITE}{title_text}{RESET}{' ' * t_right}{CYAN}│{RESET}")

    # Linha em branco
    print(f"  {CYAN}│{RESET}{' ' * inner_w}{CYAN}│{RESET}")

    # Linhas do slogan
    for ln in slogan_lines:
        l_len = len(ln)
        l_left = (inner_w - l_len) // 2
        l_right = inner_w - l_len - l_left
        print(f"  {CYAN}│{RESET}{' ' * l_left}{DIM}{ln}{RESET}{' ' * l_right}{CYAN}│{RESET}")

    print(bottom)


def print_section(title):
    print(f"\n  \033[90m┌──\033[0m \033[1m\033[96m[ {title} ]\033[0m \033[90m──────────────────────────────────────────────────┐\033[0m\n")


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
    """Tela de conexao com o MetaTrader 5."""
    print_section("CONEXAO MetaTrader 5")
    print()

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

    print()
    print(f"    {DIM}Para conectar, informe os dados da sua conta MT5.{RESET}")
    print(f"    {DIM}Voce encontra essas informacoes no email da corretora{RESET}")
    print(f"    {DIM}ou nas configuracoes do seu terminal MT5.{RESET}")
    print()

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
    """Mostra resumo final em caixa retangular perfeitamente alinhada."""
    account = mt5.account_info()
    account_str = f"{account.login} ({account.name}) @ {account.server}" if account else "Demonstração / Teste"
    balance_str = f"{account.balance:.2f} {account.currency}" if account else "N/A"
    symbols_str = ", ".join(config.SYMBOLS) if config.SYMBOLS else "Nenhum selecionado"

    box_w = 74
    inner_w = box_w - 2  # 72 caracteres internos entre │ e │

    def print_row(label: str, value_formatted: str):
        lbl = f"\033[90m{label:<18}\033[0m"
        raw_content = f"  {lbl} {value_formatted}"
        vis_len = _visible_len(raw_content)
        padding = max(0, inner_w - vis_len)
        print(f"  \033[96m│\033[0m{raw_content}{' ' * padding}\033[96m│\033[0m")

    def print_center_row(title_text: str):
        vis_len = len(title_text)
        left_pad = (inner_w - vis_len) // 2
        right_pad = inner_w - vis_len - left_pad
        print(f"  \033[1m\033[96m│\033[0m{' ' * left_pad}\033[1m\033[96m{title_text}\033[0m{' ' * right_pad}\033[1m\033[96m│\033[0m")

    top_border = f"  \033[1m\033[96m┌" + "─" * inner_w + f"┐\033[0m"
    mid_border_cyan = f"  \033[1m\033[96m├" + "─" * inner_w + f"┤\033[0m"
    mid_border_gray = f"  \033[90m├" + "─" * inner_w + f"┤\033[0m"
    bot_border = f"  \033[1m\033[96m└" + "─" * inner_w + f"┘\033[0m"

    print("\n")
    print(top_border)
    print_center_row("RESUMO DA CONFIGURAÇÃO")
    print(mid_border_cyan)

    print_row("Conta:", f"\033[97m\033[1m{account_str}\033[0m")
    print_row("Saldo:", f"\033[92m\033[1m{balance_str}\033[0m")
    print(mid_border_gray)

    print_row("Ativos:", f"\033[93m\033[1m{symbols_str}\033[0m")
    print_row("Volume Inicial:", f"\033[97m{config.VOLUME_INITIAL:.2f} lote(s)\033[0m")
    print_row("Timeframe:", f"\033[96m\033[1m{config.TIMEFRAME_NAME}\033[0m")
    print(mid_border_gray)

    strat_str = f"\033[97mSetup 9.1\033[0m" + (f" + \033[97mSetup 9.2\033[0m" if config.SETUP_92_ENABLED else "")
    print_row("Estratégia:", strat_str)

    risk_str = f"\033[92m{config.MAX_RISK_PER_TRADE_PERCENT:.1f}% do saldo\033[0m | \033[91mCorte Absoluto: {config.ABSOLUTE_MAX_TRADE_RISK_PERCENT:.1f}%\033[0m"
    print_row("Risco por Trade:", risk_str)

    daily_str = f"\033[91mPerda Máxima {config.MAX_DAILY_LOSS_PERCENT:.1f}% do saldo\033[0m"
    print_row("Trava Diária:", daily_str)

    print_row("Filtros:", "\033[97mMTF Trend\033[0m | \033[97mRVOL Volume\033[0m | \033[97mBreakeven ATR\033[0m")

    print(bot_border)
    print("\n")


def run_tui():
    """Executa a TUI completa de configuracao.
    Retorna True para iniciar, False para sair.
    """
    clear_screen()
    print_header()

    if not connect_mt5_tui():
        return False

    select_symbols_tui()
    if not config.SYMBOLS:
        print(f"    {RED}Nenhum ativo disponivel. Encerrando.{RESET}")
        return False

    configure_timeframe_tui()
    configure_volume_tui()
    configure_strategy_tui()
    configure_risk_tui()
    configure_timing_tui()

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

    if not connect_mt5_tui():
        return False

    select_symbols_tui()
    if not config.SYMBOLS:
        print(f"    {RED}Nenhum ativo disponivel.{RESET}")
        return False

    configure_volume_tui()

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