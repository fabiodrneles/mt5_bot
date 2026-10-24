"""Gera as figuras das interfaces para o manual (docs/manual/img/*.png).

Uso:  python tools/manual_screenshots.py
Precisa do Go (Maestro) e do Chrome ou Edge (captura headless). Todas as telas usam
DADOS DE DEMONSTRACAO: conta demo ficticia, historico inventado, nenhum acesso ao MT5.
"""
import html
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "manual", "img")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

BROWSERS = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            "google-chrome", "chromium", "chromium-browser"]

DEMO_TRADES = [  # historico ficticio, so para ilustrar as telas
    {"symbol": "HK50", "side": "BUY", "setup": "PULLB", "result": "win", "pnl_money": 0.42,
     "entry_time": "2026-10-13T04:00", "exit_time": "2026-10-14T08:00"},
    {"symbol": "HK50", "side": "SELL", "setup": "PULLB", "result": "loss", "pnl_money": -0.21,
     "entry_time": "2026-10-15T00:00", "exit_time": "2026-10-15T12:00"},
    {"symbol": "US500", "side": "BUY", "setup": "RSI2MR", "result": "loss", "pnl_money": -1.21,
     "entry_time": "2026-10-16T00:00", "exit_time": "2026-10-20T00:00"},
    {"symbol": "HK50", "side": "BUY", "setup": "PULLB", "result": "win", "pnl_money": 0.43,
     "entry_time": "2026-10-20T08:00", "exit_time": "2026-10-21T16:00"},
    {"symbol": "HK50", "side": "BUY", "setup": "PULLB", "result": "loss", "pnl_money": -0.20,
     "entry_time": "2026-10-22T04:00", "exit_time": "2026-10-22T20:00"},
]
DEMO_ACCOUNT = {"login": 12345678, "real": False, "balance": 16.26, "equity": 16.48,
                "margin_free": 12.90, "currency": "USD"}
DEMO_POSITION = {"ticket": 1, "symbol": "HK50", "side": "BUY", "volume": 0.01, "open": 25840.0,
                 "sl": 25610.0, "tp": 26300.0, "profit": 0.22, "setup": "PULLB"}


# --- ANSI -> HTML ----------------------------------------------------------------

def _xterm(n):
    """Cor da paleta de 256 cores do xterm em #rrggbb."""
    base = ["000000", "800000", "008000", "808000", "000080", "800080", "008080", "c0c0c0",
            "808080", "ff0000", "00ff00", "ffff00", "0000ff", "ff00ff", "00ffff", "ffffff"]
    if n < 16:
        return "#" + base[n]
    if n < 232:
        n -= 16
        lv = [0, 95, 135, 175, 215, 255]
        return "#%02x%02x%02x" % (lv[n // 36], lv[(n // 6) % 6], lv[n % 6])
    g = 8 + (n - 232) * 10
    return "#%02x%02x%02x" % (g, g, g)


def ansi_to_html(text):
    """Converte SGR (negrito, 256 cores e true color) em <span style>."""
    out, style = [], {}
    pos = 0
    for m in re.finditer(r"\x1b\[([0-9;]*)m", text):
        out.append(html.escape(text[pos:m.start()]))
        pos = m.end()
        codes = [int(c) for c in m.group(1).split(";") if c != ""] or [0]
        i = 0
        while i < len(codes):
            c = codes[i]
            if c == 0:
                style = {}
            elif c == 1:
                style["font-weight"] = "bold"
            elif c == 2:
                style["opacity"] = ".65"
            elif c == 22:
                style.pop("font-weight", None); style.pop("opacity", None)
            elif c in (38, 48) and i + 2 < len(codes) and codes[i + 1] == 5:
                style["color" if c == 38 else "background"] = _xterm(codes[i + 2]); i += 2
            elif c in (38, 48) and i + 4 < len(codes) and codes[i + 1] == 2:
                style["color" if c == 38 else "background"] = "#%02x%02x%02x" % tuple(codes[i + 2:i + 5]); i += 4
            elif c == 39:
                style.pop("color", None)
            elif c == 49:
                style.pop("background", None)
            i += 1
        out.append("</span>" + ("<span style='%s'>" % ";".join(f"{k}:{v}" for k, v in style.items())))
    out.append(html.escape(text[pos:]) + "</span>")
    return "<span>" + "".join(out)


def terminal_page(ansi, title):
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>{html.escape(title)}</title><style>
body{{margin:0;background:#0c0c0c;padding:20px 24px}}
pre{{margin:0;color:#cccccc;font:14px/1.2 "Cascadia Mono",Consolas,"DejaVu Sans Mono",monospace}}
</style></head><body><pre>{ansi_to_html(ansi)}</pre></body></html>"""


# --- captura ---------------------------------------------------------------------

def browser():
    for b in BROWSERS:
        if os.path.isfile(b) or shutil.which(b):
            return b
    raise SystemExit("Chrome/Edge nao encontrado para a captura headless.")


def shoot(url, png, width, height):
    subprocess.run([browser(), "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    "--force-device-scale-factor=1", f"--window-size={width},{height}",
                    "--virtual-time-budget=5000", f"--screenshot={png}", url],
                   check=True, capture_output=True, timeout=120)
    print("ok", os.path.relpath(png, ROOT))


def shoot_terminal(ansi, name, title, cols, rows, tmp):
    page = os.path.join(tmp, name + ".html")
    with open(page, "w", encoding="utf-8") as f:
        f.write(terminal_page(ansi, title))
    shoot("file:///" + page.replace("\\", "/"), os.path.join(OUT, name + ".png"),
          int(cols * 8.3) + 56, int(rows * 17) + 44)


# --- telas -----------------------------------------------------------------------

def maestro_ansi(tmp):
    dump = os.path.join(tmp, "maestro.ansi")
    env = dict(os.environ, MT5BOT_SCREENSHOT=dump)
    # Sem check=True: no Windows o go test as vezes sai com erro so por nao conseguir
    # apagar o executavel temporario; o que importa e o arquivo gerado.
    run = subprocess.run(["go", "test", "-run", "TestManualScreenshot", "-count=1", "."],
                         cwd=os.path.join(ROOT, "maestro"), env=env, capture_output=True, text=True)
    if not os.path.isfile(dump):
        raise SystemExit("go test nao gerou a tela do Maestro:\n" + run.stdout + run.stderr)
    with open(dump, encoding="utf-8") as f:
        return f.read()


def quant_panel_ansi():
    import quant_runner
    from mt5bot.core import telemetry
    stats = telemetry.trade_stats(DEMO_TRADES)
    snap = {"login": DEMO_ACCOUNT["login"], "real": False, "balance": 16.26, "equity": 16.48, "free": 12.90,
            "today": 0.22, "n_trades": stats["trades"], "wins": stats["wins"], "net": stats["net"],
            "routes": [{"symbol": "HK50", "tf": "H4", "setup": "PULLB", "state": "EM POSICAO (BUY)",
                        "next_close": "1h12m", "risk": 0.21, "limit": 0.33},
                       {"symbol": "US500", "tf": "D1", "setup": "RSI2MR", "state": "AGUARDANDO SINAL",
                        "next_close": "9h40m", "risk": 1.62, "limit": 1.95}],
            "positions": [DEMO_POSITION],
            "events": [("08:00:03", logging.INFO, "[HK50] PULLB BUY: toque na EMA20, fechamento acima"),
                       ("08:00:03", logging.INFO, "[HK50] Enviando a MERCADO 0.01 SL 25610 TP 26300"),
                       ("08:00:04", logging.INFO, "[HK50] Posicao aberta: ticket 1, magic do robo")]}
    return quant_runner.render_panel(snap, now="24/10 08:00:05")


def dashboard_pages():
    from interfaces import dashboard
    from mt5bot.core import telemetry
    closed = sorted(DEMO_TRADES, key=lambda t: t["exit_time"])
    snap = {"mt5_ok": True, "generated_at": "08:00:05", "account": DEMO_ACCOUNT, "today": 0.22,
            "routes": [{"symbol": "HK50", "tf": "H4", "setup": "PULLB", "risk": 0.21, "limit": 0.33, "next_close": "1h12m"},
                       {"symbol": "US500", "tf": "D1", "setup": "RSI2MR", "risk": 1.62, "limit": 1.95, "next_close": "9h40m"}],
            "positions": [DEMO_POSITION], "stats": telemetry.trade_stats(closed),
            "by_setup": telemetry.group_stats(closed, "setup"),
            "history": [{"time": t["exit_time"].replace("T", " "), "symbol": t["symbol"], "side": t["side"],
                         "setup": t["setup"], "pnl": t["pnl_money"], "result": t["result"]} for t in reversed(closed)]}
    dashboard.live_snapshot = lambda: json.loads(json.dumps(snap))
    dashboard.config.USER_CONFIG_FILE = r"%APPDATA%\mt5bot\config.toml"  # nao expor a pasta temporaria
    server, url = dashboard.serve(open_browser=False, port=dashboard._find_free_port(5600))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        shoot(url, os.path.join(OUT, "dashboard-ao-vivo.png"), 1280, 1100)
        shoot(url + "config", os.path.join(OUT, "dashboard-config.png"), 1280, 820)
    finally:
        server.shutdown()


def wizard_text():
    """Assistente de primeiro uso numa conta REAL ficticia, ate a confirmacao explicita."""
    import contextlib
    import io as _io
    import setup_wizard
    report = {"connected": True, "problems": [], "account": dict(DEMO_ACCOUNT, real=True),
              "routes": [{"symbol": "HK50", "tf": "H4", "setup": "PULLB", "risk": 0.21, "limit": 0.33},
                         {"symbol": "US500", "tf": "D1", "setup": "RSI2MR", "risk": 1.62, "limit": 1.95}]}
    setup_wizard.check_environment = lambda: report
    setup_wizard.config.LIVE_CONFIRMED = False
    setup_wizard.user_config.set_value = lambda key, value: r"%APPDATA%\mt5bot\config.toml"
    stdin = sys.stdin
    sys.stdin = types.SimpleNamespace(isatty=lambda: True)
    buf = _io.StringIO()

    def ask(prompt):
        buf.write(prompt + "CONFIRMO\n")
        return "CONFIRMO"
    try:
        with contextlib.redirect_stdout(buf):
            setup_wizard.main(ask=ask)
    finally:
        sys.stdin = stdin
    return buf.getvalue()


def main():
    os.makedirs(OUT, exist_ok=True)
    # Pasta de dados temporaria: nada do usuario (trades, config.toml) aparece nas figuras.
    tmp = tempfile.mkdtemp(prefix="mt5bot-shots-")
    os.environ["MT5BOT_DATA_DIR"] = tmp
    try:
        import MetaTrader5  # noqa: F401
    except ImportError:  # Linux/macOS: as telas nao chamam o MT5
        sys.modules["MetaTrader5"] = types.ModuleType("MetaTrader5")
    shoot_terminal(maestro_ansi(tmp), "maestro", "Maestro", 120, 32, tmp)
    shoot_terminal(quant_panel_ansi(), "painel-quant", "Painel Quant", 80, 24, tmp)
    shoot_terminal(wizard_text(), "assistente-setup", "bot.bat setup", 92, 20, tmp)
    dashboard_pages()
    shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
