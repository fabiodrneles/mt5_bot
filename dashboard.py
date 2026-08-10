"""
Dashboard web para configuracao e relatorio de performance.
Usa apenas modulos built-in do Python (sem dependencias externas).
Abre no navegador para configuracao visual e mostra resultados.
"""
import http.server
import json
import threading
import webbrowser
import urllib.parse
import os

import config
import tracker

_PORT = 5555
_server = None
_config_ready = threading.Event()
_configured_data = {}


def _find_free_port(start=5555, attempts=10):
    """Encontra uma porta livre a partir de start."""
    import socket
    for port in range(start, start + attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    return start  # fallback


def _html_head(title):
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
       background: #1a1a2e; color: #e0e0e0; line-height: 1.6; padding: 2rem; }}
.container {{ max-width: 900px; margin: 0 auto; }}
h1 {{ color: #ffffff; margin-bottom: 0.3rem; font-size: 1.8rem; }}
h2 {{ color: #a0a0b0; margin: 2rem 0 1rem; font-size: 1.2rem; border-bottom: 1px solid #2a2a4e; padding-bottom: 0.5rem; }}
.tagline {{ color: #4a9eff; font-size: 0.9rem; margin-bottom: 1.5rem; font-style: italic; }}
.subtitle {{ color: #707090; font-size: 0.9rem; margin-bottom: 2rem; }}
.card {{ background: #16213e; border-radius: 8px; padding: 1.5rem; margin-bottom: 1.5rem; border: 1px solid #2a2a4e; }}
label {{ display: block; color: #a0a0b0; font-size: 0.85rem; margin-bottom: 0.3rem; }}
input, select {{ width: 100%; padding: 0.6rem; border-radius: 4px; border: 1px solid #2a2a4e;
               background: #0f3460; color: #e0e0e0; font-size: 0.95rem; margin-bottom: 1rem; }}
input:focus, select:focus {{ outline: none; border-color: #4a9eff; }}
.row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }}
.row-3 {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem; }}
button {{ padding: 0.8rem 2rem; border-radius: 6px; border: none; cursor: pointer;
         font-size: 1rem; font-weight: 600; transition: all 0.2s; }}
.btn-primary {{ background: #4a9eff; color: #fff; }}
.btn-primary:hover {{ background: #3a8eef; }}
.btn-secondary {{ background: #2a2a4e; color: #a0a0b0; }}
.btn-secondary:hover {{ background: #3a3a5e; }}
.actions {{ display: flex; gap: 1rem; justify-content: flex-end; margin-top: 2rem; }}
table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
th {{ text-align: left; padding: 0.6rem; color: #707090; border-bottom: 1px solid #2a2a4e; font-weight: 500; }}
td {{ padding: 0.6rem; border-bottom: 1px solid #1a1a3e; }}
.win {{ color: #4ecdc4; }}
.loss {{ color: #ff6b6b; }}
.stat-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; }}
.stat {{ background: #0f3460; padding: 1rem; border-radius: 6px; text-align: center; }}
.stat-value {{ font-size: 1.5rem; font-weight: 700; color: #fff; }}
.stat-label {{ font-size: 0.75rem; color: #707090; margin-top: 0.3rem; }}
.nav {{ display: flex; gap: 1rem; margin-bottom: 2rem; }}
.nav a {{ color: #4a9eff; text-decoration: none; padding: 0.5rem 1rem; border-radius: 4px; }}
.nav a:hover {{ background: #16213e; }}
.nav a.active {{ background: #16213e; font-weight: 600; }}
.success-msg {{ background: #1a4a3a; color: #4ecdc4; padding: 1rem; border-radius: 6px; text-align: center; margin: 2rem 0; }}
</style>
</head>
<body>
<div class="container">
"""


def _html_nav(active="config"):
    config_cls = "active" if active == "config" else ""
    report_cls = "active" if active == "report" else ""
    return f"""
<div class="nav">
    <a href="/config" class="{config_cls}">Configuracao</a>
    <a href="/report" class="{report_cls}">Relatorio</a>
</div>
"""


def _html_footer():
    return """
</div>
</body>
</html>"""


def _build_timeframe_options():
    """Gera as <option> HTML para o seletor de timeframe."""
    options = []
    for tf_name, tf_value in config.AVAILABLE_TIMEFRAMES.items():
        selected = "selected" if tf_name == config.TIMEFRAME_NAME else ""
        options.append(f'<option value="{tf_name}" {selected}>{tf_name}</option>')
    return "\n".join(options)


def _page_config():
    """Pagina de configuracao."""
    html = _html_head("MT5Bot — Configuracao")
    html += f"""
<h1>MT5Bot</h1>
    <p class="tagline">Measured, disciplined execution — performance varies with market conditions.</p>
<p class="subtitle">Configure os parametros abaixo e clique em "Salvar e Iniciar".</p>
"""
    html += _html_nav("config")
    html += """
<form method="POST" action="/config/save">

<div class="card">
<h2>Ativos e Volume</h2>
<div class="row">
<div>
<label>Ativos (separados por virgula)</label>
<input type="text" name="symbols" value="{symbols}" placeholder="HK50, EURUSD, US500">
</div>
<div>
<label>Volume por operacao (lotes)</label>
<input type="number" name="volume" value="{volume}" step="0.01" min="0.01">
</div>
</div>
<div>
<label>Timeframe</label>
<select name="timeframe">
{timeframe_options}
</select>
</div>
</div>

<div class="card">
<h2>Estrategia</h2>
<div class="row-3">
<div>
<label>EMA Rapida (periodo)</label>
<input type="number" name="ema_period" value="{ema_period}" min="3" max="50">
</div>
<div>
<label>EMA Filtro (periodo)</label>
<input type="number" name="ema_filter" value="{ema_filter}" min="10" max="200">
</div>
<div>
<label>Setup 9.2</label>
<select name="setup_92">
<option value="1" {s92_on}>Ativado</option>
<option value="0" {s92_off}>Desativado</option>
</select>
</div>
</div>
<div class="row">
<div>
<label>Filtro Flat</label>
<select name="flat_filter">
<option value="1" {flat_on}>Ativado</option>
<option value="0" {flat_off}>Desativado</option>
<div class="row-3">
<div>
<label>Setup 9.3 (Larry Williams)</label>
<select name="setup_93">
<option value="1" {s93_on}>Ativado</option>
<option value="0" {s93_off}>Desativado</option>
</select>
</div>
<div>
<label>Filtro MTF (Timeframe Maior)</label>
<select name="mtf_filter">
<option value="1" {mtf_on}>Ativado</option>
<option value="0" {mtf_off}>Desativado</option>
</select>
</div>
<div>
<label>Filtro de Volume (RVOL)</label>
<select name="rvol_filter">
<option value="1" {rvol_on}>Ativado</option>
<option value="0" {rvol_off}>Desativado</option>
</select>
</div>
</div>
<div class="row">
<div>
<label>RVOL Limiar Minimo (ex: 1.15 = 15% acima)</label>
<input type="number" name="rvol_threshold" value="{rvol_threshold}" step="0.05" min="1.0" max="3.0">
</div>
<div>
<label>RVOL Periodos Média (Lookback)</label>
<input type="number" name="rvol_lookback" value="{rvol_lookback}" min="5" max="50">
</div>
</div>
</div>

<div class="card">
<h2>Proteção de Capital & Escudo de Risco</h2>
<div class="row-3">
<div>
<label>Risco por Trade (% saldo)</label>
<input type="number" name="max_risk_pct" value="{max_risk_pct}" step="0.1" min="0.1" max="5.0">
</div>
<div>
<label>Corte Absoluto (% saldo)</label>
<input type="number" name="abs_max_risk_pct" value="{abs_max_risk_pct}" step="0.1" min="0.5" max="10.0">
</div>
<div>
<label>Perda Diaria Max (% saldo)</label>
<input type="number" name="max_daily_loss_pct" value="{max_daily_loss_pct}" step="0.1" min="0.5" max="20.0">
</div>
</div>
<div class="row-3">
<div>
<label>Spread Maximo (pontos)</label>
<input type="number" name="max_spread" value="{max_spread}" min="5" max="500">
</div>
<div>
<label>Breakeven Automatico</label>
<select name="enable_breakeven">
<option value="1" {be_on}>Ativado</option>
<option value="0" {be_off}>Desativado</option>
</select>
</div>
<div>
<label>Filtro de Horario</label>
<select name="trading_hours_enabled">
<option value="1" {th_on}>Ativado</option>
<option value="0" {th_off}>Desativado</option>
</select>
</div>
</div>
<div class="row">
<div>
<label>Horario de Inicio (HH:MM)</label>
<input type="text" name="trading_start_time" value="{trading_start_time}" placeholder="09:15">
</div>
<div>
<label>Horario de Fim (HH:MM)</label>
<input type="text" name="trading_end_time" value="{trading_end_time}" placeholder="16:45">
</div>
</div>
</div>

<div class="card">
<h2>Gestao de Risco</h2>
<div class="row-3">
<div>
<label>Saida Parcial</label>
<select name="partial_exit">
<option value="1" {pe_on}>Ativada</option>
<option value="0" {pe_off}>Desativada</option>
</select>
</div>
<div>
<label>% Volume Parcial</label>
<input type="number" name="partial_pct" value="{partial_pct}" step="0.1" min="0.1" max="0.9">
</div>
<div>
<label>Alvo Parcial (% amplitude)</label>
<input type="number" name="partial_target" value="{partial_target}" step="0.1" min="0.5" max="3.0">
</div>
</div>
<div class="row-3">
<div>
<label>Alvo Adaptativo</label>
<select name="adaptive_target">
<option value="1" {at_on}>Ativado</option>
<option value="0" {at_off}>Desativado</option>
</select>
</div>
<div>
<label>ATR Threshold (volatilidade)</label>
<input type="number" name="atr_threshold" value="{atr_threshold}" step="0.1" min="1.0" max="3.0">
</div>
<div>
<label>Tick Offset (SL/Entry)</label>
<input type="number" name="tick_offset" value="{tick_offset}" min="1" max="5">
</div>
</div>
</div>

<div class="card">
<h2>Intervalos</h2>
<div class="row-3">
<div>
<label>Scan (segundos)</label>
<input type="number" name="scan_interval" value="{scan_interval}" min="5" max="60">
</div>
<div>
<label>Retry em erro (segundos)</label>
<input type="number" name="retry_interval" value="{retry_interval}" min="10" max="120">
</div>
<div>
<label>Candles historicos</label>
<input type="number" name="rates_count" value="{rates_count}" min="50" max="500">
</div>
</div>
</div>

<div class="actions">
<button type="button" class="btn-secondary" onclick="window.close()">Cancelar</button>
<button type="submit" class="btn-primary">Salvar e Iniciar</button>
</div>
</form>
""".format(
        symbols=", ".join(config.AVAILABLE_SYMBOLS),
        volume=config.VOLUME_INITIAL,
        timeframe_options=_build_timeframe_options(),
        ema_period=config.EMA_PERIOD,
        ema_filter=config.EMA_FILTER_PERIOD,
        flat_on="selected" if config.FLAT_FILTER_ENABLED else "",
        flat_off="" if config.FLAT_FILTER_ENABLED else "selected",
        flat_threshold=config.FLAT_THRESHOLD_TICKS,
        s93_on="selected" if getattr(config, "SETUP_93_ENABLED", True) else "",
        s93_off="" if getattr(config, "SETUP_93_ENABLED", True) else "selected",
        mtf_on="selected" if getattr(config, "MTF_FILTER_ENABLED", True) else "",
        mtf_off="" if getattr(config, "MTF_FILTER_ENABLED", True) else "selected",
        rvol_on="selected" if getattr(config, "RVOL_FILTER_ENABLED", True) else "",
        rvol_off="" if getattr(config, "RVOL_FILTER_ENABLED", True) else "selected",
        rvol_threshold=getattr(config, "RVOL_THRESHOLD", 1.15),
        rvol_lookback=getattr(config, "RVOL_LOOKBACK", 20),
        max_risk_pct=config.MAX_RISK_PER_TRADE_PERCENT,
        abs_max_risk_pct=config.ABSOLUTE_MAX_TRADE_RISK_PERCENT,
        max_daily_loss_pct=config.MAX_DAILY_LOSS_PERCENT,
        max_spread=config.MAX_SPREAD_POINTS or 50,
        be_on="selected" if config.ENABLE_BREAKEVEN else "",
        be_off="" if config.ENABLE_BREAKEVEN else "selected",
        th_on="selected" if getattr(config, "TRADING_HOURS_ENABLED", True) else "",
        th_off="" if getattr(config, "TRADING_HOURS_ENABLED", True) else "selected",
        trading_start_time=getattr(config, "TRADING_START_TIME", "09:15"),
        trading_end_time=getattr(config, "TRADING_END_TIME", "16:45"),
        pe_on="selected" if config.PARTIAL_EXIT_ENABLED else "",
        pe_off="" if config.PARTIAL_EXIT_ENABLED else "selected",
        partial_pct=config.PARTIAL_EXIT_PERCENT,
        partial_target=config.PARTIAL_EXIT_TARGET,
        at_on="selected" if config.ADAPTIVE_TARGET_ENABLED else "",
        at_off="" if config.ADAPTIVE_TARGET_ENABLED else "selected",
        atr_threshold=config.ATR_HIGH_VOL_THRESHOLD,
        tick_offset=config.TICK_OFFSET,
        scan_interval=config.SCAN_INTERVAL_SECONDS,
        retry_interval=config.RETRY_INTERVAL_SECONDS,
        rates_count=config.RATES_COUNT,
    )
    html += _html_footer()
    return html


def _page_config_saved():
    """Pagina de confirmacao apos salvar."""
    html = _html_head("MT5Bot — Pronto!")
    html += """
<h1>MT5Bot</h1>
<p class="tagline">Lucros consistentes. Zero emocao.</p>
<div class="success-msg">
    Configuracao salva. Pode fechar esta janela.<br>
    O bot esta iniciando no terminal.
</div>
"""
    html += _html_footer()
    return html


def _page_report():
    """Pagina de relatorio de performance."""
    summary = tracker.get_performance_summary()
    trades = tracker.get_closed_trades()

    html = _html_head("MT5Bot — Relatorio de Performance")
    html += """
<h1>MT5Bot — Performance</h1>
<p class="tagline">Lucros consistentes. Zero emocao.</p>
<p class="subtitle">Historico completo de operacoes e metricas financeiras.</p>
"""
    html += _html_nav("report")

    # Stats grid
    pnl_color = "win" if summary["total_pnl_pips"] >= 0 else "loss"
    html += f"""
<div class="stat-grid">
    <div class="stat"><div class="stat-value">{summary['total_trades']}</div><div class="stat-label">Total Operacoes</div></div>
    <div class="stat"><div class="stat-value {pnl_color}">{summary['total_pnl_pips']:+.2f}</div><div class="stat-label">PnL Total (pips)</div></div>
    <div class="stat"><div class="stat-value">{summary['win_rate']}%</div><div class="stat-label">Win Rate</div></div>
    <div class="stat"><div class="stat-value">{summary['profit_factor']:.2f}</div><div class="stat-label">Profit Factor</div></div>
    <div class="stat"><div class="stat-value win">{summary['wins']}</div><div class="stat-label">Vitorias</div></div>
    <div class="stat"><div class="stat-value loss">{summary['losses']}</div><div class="stat-label">Derrotas</div></div>
    <div class="stat"><div class="stat-value">{summary['max_drawdown_pips']:.2f}</div><div class="stat-label">Max Drawdown (pips)</div></div>
    <div class="stat"><div class="stat-value">{summary['open_trades']}</div><div class="stat-label">Abertas Agora</div></div>
</div>
"""

    # Detalhes
    html += f"""
<div class="card">
<h2>Detalhes</h2>
<div class="row">
<div>
<table>
<tr><th>Metrica</th><th>Valor</th></tr>
<tr><td>Media Vitoria (pips)</td><td class="win">{summary['avg_win_pips']:.5f}</td></tr>
<tr><td>Media Derrota (pips)</td><td class="loss">{summary['avg_loss_pips']:.5f}</td></tr>
<tr><td>Maior Vitoria (pips)</td><td class="win">{summary['largest_win_pips']:.5f}</td></tr>
<tr><td>Maior Derrota (pips)</td><td class="loss">{summary['largest_loss_pips']:.5f}</td></tr>
<tr><td>Seq. Vitorias</td><td>{summary['consecutive_wins']}</td></tr>
<tr><td>Seq. Derrotas</td><td>{summary['consecutive_losses']}</td></tr>
</table>
</div>
<div>
<table>
<tr><th>Ativo</th><th>W/L</th><th>Win Rate</th><th>PnL</th></tr>
"""
    for sym, data in summary["by_symbol"].items():
        total = data["wins"] + data["losses"]
        wr = round((data["wins"] / total) * 100, 1) if total > 0 else 0
        pnl_cls = "win" if data["pnl_pips"] >= 0 else "loss"
        html += f'<tr><td>{sym}</td><td>{data["wins"]}/{data["losses"]}</td><td>{wr}%</td><td class="{pnl_cls}">{data["pnl_pips"]:+.2f}</td></tr>\n'

    if not summary["by_symbol"]:
        html += '<tr><td colspan="4" style="color:#707090">Nenhum dado ainda</td></tr>'

    html += """
</table>
<br>
<table>
<tr><th>Setup</th><th>W/L</th><th>Win Rate</th><th>PnL</th></tr>
"""
    for setup, data in summary["by_setup"].items():
        total = data["wins"] + data["losses"]
        wr = round((data["wins"] / total) * 100, 1) if total > 0 else 0
        pnl_cls = "win" if data["pnl_pips"] >= 0 else "loss"
        html += f'<tr><td>{setup}</td><td>{data["wins"]}/{data["losses"]}</td><td>{wr}%</td><td class="{pnl_cls}">{data["pnl_pips"]:+.2f}</td></tr>\n'

    if not summary["by_setup"]:
        html += '<tr><td colspan="4" style="color:#707090">Nenhum dado ainda</td></tr>'

    html += """
</table>
</div>
</div>
</div>
"""

    # Trade history
    html += """
<div class="card">
<h2>Historico de Operacoes</h2>
<table>
<tr><th>#</th><th>Data</th><th>Ativo</th><th>Lado</th><th>Setup</th><th>Entrada</th><th>Saida</th><th>PnL (pips)</th><th>Resultado</th></tr>
"""
    for t in reversed(trades[-50:]):
        entry = f"{t['entry_price']:.5f}" if t['entry_price'] else "—"
        exit_p = f"{t['exit_price']:.5f}" if t['exit_price'] else "—"
        pnl_val = t['pnl_pips'] if t['pnl_pips'] is not None else 0
        pnl_str = f"{pnl_val:+.5f}" if t['pnl_pips'] is not None else "—"
        pnl_cls = "win" if pnl_val > 0 else "loss" if pnl_val < 0 else ""
        result_str = t['result'].upper()
        entry_time = t.get('entry_time', '')[:16].replace('T', ' ') if t.get('entry_time') else '—'
        html += f'<tr><td>{t["id"]}</td><td>{entry_time}</td><td>{t["symbol"]}</td><td>{t["side"]}</td><td>{t.get("setup","9.1")}</td><td>{entry}</td><td>{exit_p}</td><td class="{pnl_cls}">{pnl_str}</td><td>{result_str}</td></tr>\n'

    if not trades:
        html += '<tr><td colspan="9" style="color:#707090;text-align:center">Nenhuma operacao registrada ainda. Inicie o bot para comecar a operar.</td></tr>'

    html += """
</table>
</div>
"""
    html += _html_footer()
    return html


class _DashboardHandler(http.server.BaseHTTPRequestHandler):
    """Handler HTTP para o dashboard."""

    def log_message(self, format, *args):
        pass  # Silenciar logs HTTP

    def do_GET(self):
        if self.path == "/" or self.path == "/config":
            self._respond(200, _page_config())
        elif self.path == "/report":
            self._respond(200, _page_report())
        elif self.path == "/api/summary":
            summary = tracker.get_performance_summary()
            self._respond_json(summary)
        else:
            self._respond(404, "<h1>404</h1>")

    def do_POST(self):
        if self.path == "/config/save":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            params = urllib.parse.parse_qs(body)

            # Extrair e aplicar configuracao com validacao
            global _configured_data
            try:
                _configured_data = {
                    "symbols": params.get("symbols", [""])[0],
                    "volume": max(0.01, float(params.get("volume", ["0.01"])[0])),
                    "ema_period": max(3, int(params.get("ema_period", ["9"])[0])),
                    "ema_filter": max(10, int(params.get("ema_filter", ["21"])[0])),
                    "setup_92": params.get("setup_92", ["1"])[0] == "1",
                    "setup_93": params.get("setup_93", ["1"])[0] == "1",
                    "mtf_filter": params.get("mtf_filter", ["1"])[0] == "1",
                    "rvol_filter": params.get("rvol_filter", ["1"])[0] == "1",
                    "rvol_threshold": max(1.0, float(params.get("rvol_threshold", ["1.15"])[0])),
                    "rvol_lookback": max(5, int(params.get("rvol_lookback", ["20"])[0])),
                    "flat_filter": params.get("flat_filter", ["1"])[0] == "1",
                    "flat_threshold": max(1, int(params.get("flat_threshold", ["5"])[0])),
                    "max_risk_pct": max(0.1, float(params.get("max_risk_pct", ["1.0"])[0])),
                    "abs_max_risk_pct": max(0.5, float(params.get("abs_max_risk_pct", ["1.5"])[0])),
                    "max_daily_loss_pct": max(0.5, float(params.get("max_daily_loss_pct", ["2.0"])[0])),
                    "max_spread": max(5, int(params.get("max_spread", ["50"])[0])),
                    "enable_breakeven": params.get("enable_breakeven", ["1"])[0] == "1",
                    "trading_hours_enabled": params.get("trading_hours_enabled", ["1"])[0] == "1",
                    "trading_start_time": params.get("trading_start_time", ["09:15"])[0],
                    "trading_end_time": params.get("trading_end_time", ["16:45"])[0],
                    "partial_exit": params.get("partial_exit", ["1"])[0] == "1",
                    "partial_pct": min(0.9, max(0.1, float(params.get("partial_pct", ["0.5"])[0]))),
                    "partial_target": max(0.3, float(params.get("partial_target", ["1.0"])[0])),
                    "adaptive_target": params.get("adaptive_target", ["1"])[0] == "1",
                    "atr_threshold": max(1.0, float(params.get("atr_threshold", ["1.5"])[0])),
                    "tick_offset": max(1, int(params.get("tick_offset", ["1"])[0])),
                    "scan_interval": max(5, int(params.get("scan_interval", ["10"])[0])),
                    "retry_interval": max(10, int(params.get("retry_interval", ["30"])[0])),
                    "rates_count": max(50, int(params.get("rates_count", ["100"])[0])),
                    "timeframe": params.get("timeframe", ["H1"])[0],
                }
            except (ValueError, TypeError):
                # Se dados do formulario forem invalidos, usar defaults
                _configured_data = {
                    "symbols": ", ".join(config.AVAILABLE_SYMBOLS),
                    "volume": 0.01, "ema_period": 9, "ema_filter": 21,
                    "setup_92": True, "setup_93": True, "mtf_filter": True,
                    "rvol_filter": True, "rvol_threshold": 1.15, "rvol_lookback": 20,
                    "flat_filter": True, "flat_threshold": 5,
                    "max_risk_pct": 1.0, "abs_max_risk_pct": 1.5, "max_daily_loss_pct": 2.0,
                    "max_spread": 50, "enable_breakeven": True, "trading_hours_enabled": True,
                    "trading_start_time": "09:15", "trading_end_time": "16:45",
                    "partial_exit": True, "partial_pct": 0.5, "partial_target": 1.0,
                    "adaptive_target": True, "atr_threshold": 1.5, "tick_offset": 1,
                    "scan_interval": 10, "retry_interval": 30, "rates_count": 100,
                    "timeframe": "H1",
                }

            # Aplicar ao config
            _apply_config(_configured_data)

            self._respond(200, _page_config_saved())
            _config_ready.set()
        else:
            self._respond(404, "<h1>404</h1>")

    def _respond(self, code, html):
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _respond_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))


def _apply_config(data):
    """Aplica dados do formulario web ao config."""
    symbols_raw = data.get("symbols", "")
    config.SYMBOLS = [s.strip() for s in symbols_raw.split(",") if s.strip()]
    config.VOLUME_INITIAL = data.get("volume", 0.01)
    config.EMA_PERIOD = data.get("ema_period", 9)
    config.EMA_FILTER_PERIOD = data.get("ema_filter", 21)
    config.SETUP_92_ENABLED = data.get("setup_92", True)
    config.SETUP_93_ENABLED = data.get("setup_93", True)
    config.MTF_FILTER_ENABLED = data.get("mtf_filter", True)
    config.RVOL_FILTER_ENABLED = data.get("rvol_filter", True)
    config.RVOL_THRESHOLD = data.get("rvol_threshold", 1.15)
    config.RVOL_LOOKBACK = data.get("rvol_lookback", 20)
    config.FLAT_FILTER_ENABLED = data.get("flat_filter", True)
    config.FLAT_THRESHOLD_TICKS = data.get("flat_threshold", 5)
    config.MAX_RISK_PER_TRADE_PERCENT = data.get("max_risk_pct", 1.0)
    config.ABSOLUTE_MAX_TRADE_RISK_PERCENT = data.get("abs_max_risk_pct", 1.5)
    config.MAX_DAILY_LOSS_PERCENT = data.get("max_daily_loss_pct", 2.0)
    config.MAX_SPREAD_POINTS = data.get("max_spread", 50)
    config.ENABLE_BREAKEVEN = data.get("enable_breakeven", True)
    config.TRADING_HOURS_ENABLED = data.get("trading_hours_enabled", True)
    config.TRADING_START_TIME = data.get("trading_start_time", "09:15")
    config.TRADING_END_TIME = data.get("trading_end_time", "16:45")
    config.PARTIAL_EXIT_ENABLED = data.get("partial_exit", True)
    config.PARTIAL_EXIT_PERCENT = data.get("partial_pct", 0.5)
    config.PARTIAL_EXIT_TARGET = data.get("partial_target", 1.0)
    config.ADAPTIVE_TARGET_ENABLED = data.get("adaptive_target", True)
    config.ATR_HIGH_VOL_THRESHOLD = data.get("atr_threshold", 1.5)
    config.TICK_OFFSET = data.get("tick_offset", 1)
    config.SCAN_INTERVAL_SECONDS = data.get("scan_interval", 10)
    config.RETRY_INTERVAL_SECONDS = data.get("retry_interval", 30)
    config.RATES_COUNT = data.get("rates_count", 100)

    # Timeframe — valida contra lista de timeframes disponiveis
    tf_name = data.get("timeframe", "H1")
    if tf_name in config.AVAILABLE_TIMEFRAMES:
        config.TIMEFRAME = config.AVAILABLE_TIMEFRAMES[tf_name]
        config.TIMEFRAME_NAME = tf_name


def open_config():
    """Abre dashboard de configuracao no navegador.
    Bloqueia ate o usuario salvar a configuracao.
    Retorna True se configuracao foi salva, False se timeout/cancelado.
    """
    global _server, _config_ready, _PORT
    _config_ready.clear()

    _PORT = _find_free_port()
    _server = http.server.HTTPServer(("127.0.0.1", _PORT), _DashboardHandler)
    thread = threading.Thread(target=_server.serve_forever, daemon=True)
    thread.start()

    url = f"http://localhost:{_PORT}/config"
    print(f"\n  Dashboard aberto em: {url}")
    print(f"  Aguardando configuracao no navegador...\n")
    webbrowser.open(url)

    # Aguardar ate o usuario salvar ou timeout de 5 minutos
    configured = _config_ready.wait(timeout=300)

    _server.shutdown()
    return configured


def open_report():
    """Abre pagina de relatorio no navegador."""
    global _server, _PORT

    _PORT = _find_free_port()
    _server = http.server.HTTPServer(("127.0.0.1", _PORT), _DashboardHandler)
    thread = threading.Thread(target=_server.serve_forever, daemon=True)
    thread.start()

    url = f"http://localhost:{_PORT}/report"
    print(f"\n  Relatorio aberto em: {url}")
    print(f"  Pressione Enter para fechar o relatorio...\n")
    webbrowser.open(url)

    input()
    _server.shutdown()