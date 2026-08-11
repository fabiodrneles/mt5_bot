"""
Web dashboard for configuration and performance report.
Python stdlib only (no external dependencies).
Opens in the browser for visual configuration and shows results.
Multi-language UI: pt (default), en, es — selectable in the top bar.

Identity: institutional Maestro-orange terminal (ANSI 208 = #ff8700).
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

DEFAULT_LANG = "pt"
SUPPORTED_LANGS = ("pt", "en", "es")


def _lang_name(lang):
    return {"pt": "Português", "en": "English", "es": "Español"}.get(lang, lang)


def _build_l10n():
    """UI strings for pt/en/es. Keys are shared across the three languages."""

    def m(pt, en, es):
        return {"pt": pt, "en": en, "es": es}

    return {
        "pages": {
            "config_title": m("MT5Bot — Configuração", "MT5Bot — Configuration", "MT5Bot — Configuración"),
            "config_h1": m("CONFIGURAÇÃO DO TERMINAL", "TERMINAL CONFIGURATION", "CONFIGURACIÓN DEL TERMINAL"),
            "config_sub": m(
                'Configure os parâmetros abaixo e clique em "Salvar e Iniciar".',
                'Set the parameters below and click "Save and Start".',
                'Configure los parámetros abajo y haga clic en "Guardar e Iniciar".',
            ),
            "ready_title": m("MT5Bot — Pronto!", "MT5Bot — Ready!", "MT5Bot — ¡Listo!"),
            "ready_h1": m("CONFIGURAÇÃO APLICADA", "CONFIGURATION APPLIED", "CONFIGURACIÓN APLICADA"),
            "ready_msg": m(
                "O bot está iniciando no terminal.<br>Pode fechar esta janela.",
                "The bot is starting in the terminal.<br>You can close this window.",
                "El bot está iniciando en el terminal.<br>Puede cerrar esta ventana.",
            ),
            "report_title": m("MT5Bot — Relatório de Performance", "MT5Bot — Performance Report", "MT5Bot — Informe de Rendimiento"),
            "report_h1": m("RELATÓRIO DE PERFORMANCE", "PERFORMANCE REPORT", "INFORME DE RENDIMIENTO"),
            "report_sub": m(
                "Histórico completo de operações e métricas financeiras.",
                "Full trade history and financial metrics.",
                "Historial completo de operaciones y métricas financieras.",
            ),
        },
        "nav": {
            "label": m("Seções", "Sections", "Secciones"),
            "config": m("Configuração", "Configuration", "Configuración"),
            "report": m("Relatório", "Report", "Informe"),
        },
        "footer": m(
            "MT5BOT MAESTRO — RISCO POR TRADE ≤ 1% · HARD STOP NA CORRETORA · STATELESS",
            "MT5BOT MAESTRO — RISK PER TRADE ≤ 1% · HARD STOP AT BROKER · STATELESS",
            "MT5BOT MAESTRO — RIESGO POR TRADE ≤ 1% · HARD STOP EN EL BRÓKER · STATELESS",
        ),
        "general": {
            "enabled": m("Ativado", "Enabled", "Activado"),
            "disabled": m("Desativado", "Disabled", "Desactivado"),
            "cancel": m("Cancelar", "Cancel", "Cancelar"),
            "save_start": m("Salvar e Iniciar", "Save and Start", "Guardar e Iniciar"),
        },
        "config": {
            "assets_market": m("Ativos & Mercado", "Assets & Market", "Activos & Mercado"),
            "symbols": m("Ativos (separados por vírgula)", "Assets (comma-separated)", "Activos (separados por coma)"),
            "timeframe": m("Timeframe", "Timeframe", "Timeframe"),
            "volume": m("Volume por operação (lotes)", "Volume per trade (lots)", "Volumen por operación (lotes)"),
            "strategy": m("Estratégia", "Strategy", "Estrategia"),
            "ema_fast": m("EMA Rápida (período)", "Fast EMA (period)", "EMA Rápida (período)"),
            "ema_filter": m("EMA Filtro (período)", "EMA Filter (period)", "Filtro EMA (período)"),
            "setup_92": m("Setup 9.2", "Setup 9.2", "Setup 9.2"),
            "setup_93": m("Setup 9.3 (Larry Williams)", "Setup 9.3 (Larry Williams)", "Setup 9.3 (Larry Williams)"),
            "flat": m("Filtro Flat", "Flat Filter", "Filtro Flat"),
            "flat_ticks": m("Ticks de Flat (limiar)", "Flat Ticks (threshold)", "Ticks de Flat (umbral)"),
            "mtf": m("Filtro MTF (Timeframe Maior)", "MTF Filter (Higher Timeframe)", "Filtro MTF (Marco Temporal Superior)"),
            "rvol": m("Filtro de Volume (RVOL)", "Volume Filter (RVOL)", "Filtro de Volumen (RVOL)"),
            "rvol_th": m("RVOL limiar mínimo (ex.: 1.15 = +15%)", "RVOL min threshold (e.g., 1.15 = +15%)", "Umbral mínimo RVOL (ej.: 1.15 = +15%)"),
            "rvol_lb": m("RVOL períodos (lookback)", "RVOL periods (lookback)", "Períodos RVOL (lookback)"),
            "risk": m("Proteção de Capital & Escudo de Risco", "Capital Protection & Risk Shield", "Protección de Capital & Escudo de Riesgo"),
            "risk_trade": m("Risco por trade (% saldo)", "Risk per trade (% balance)", "Riesgo por trade (% saldo)"),
            "abs_cap": m("Corte absoluto (% saldo)", "Absolute cap (% balance)", "Tope absoluto (% saldo)"),
            "daily_loss": m("Perda diária máx. (% saldo)", "Max daily loss (% balance)", "Pérdida diaria máx. (% saldo)"),
            "spread": m("Spread máximo (pontos)", "Max spread (points)", "Spread máximo (puntos)"),
            "breakeven": m("Breakeven automático", "Automatic breakeven", "Breakeven automático"),
            "hours": m("Filtro de horário", "Trading hours filter", "Filtro de horario"),
            "start_time": m("Horário de início (HH:MM)", "Start time (HH:MM)", "Hora de inicio (HH:MM)"),
            "end_time": m("Horário de fim (HH:MM)", "End time (HH:MM)", "Hora de fin (HH:MM)"),
            "position": m("Gestão de Posição", "Position Management", "Gestión de Posición"),
            "partial_exit": m("Saída parcial", "Partial exit", "Salida parcial"),
            "partial_pct": m("% volume parcial", "Partial volume %", "% volumen parcial"),
            "partial_target": m("Alvo parcial (× amplitude)", "Partial target (× amplitude)", "Objetivo parcial (× amplitud)"),
            "adaptive": m("Alvo adaptativo", "Adaptive target", "Objetivo adaptativo"),
            "atr_th": m("ATR threshold (volatilidade)", "ATR threshold (volatility)", "Umbral ATR (volatilidad)"),
            "tick_offset": m("Tick offset (SL/entrada)", "Tick offset (SL/entry)", "Offset de ticks (SL/entrada)"),
            "intervals": m("Intervalos", "Intervals", "Intervalos"),
            "scan": m("Scan (segundos)", "Scan (seconds)", "Scan (segundos)"),
            "retry": m("Retry em erro (segundos)", "Retry on error (seconds)", "Reintento en error (segundos)"),
            "rates": m("Candles históricos", "Historical candles", "Velas históricas"),
        },
        "report": {
            "trades": m("Operações", "Trades", "Operaciones"),
            "pnl_total": m("PnL Total (pips)", "Total PnL (pips)", "PnL Total (pips)"),
            "win_rate": m("Win Rate", "Win Rate", "Win Rate"),
            "profit_factor": m("Profit Factor", "Profit Factor", "Profit Factor"),
            "wins": m("Vitórias", "Wins", "Victorias"),
            "losses": m("Derrotas", "Losses", "Derrotas"),
            "max_dd": m("Max Drawdown (pips)", "Max Drawdown (pips)", "Max Drawdown (pips)"),
            "open_now": m("Abertas Agora", "Open Now", "Abiertas Ahora"),
            "per_trade": m("Métricas por Operação", "Per-Trade Metrics", "Métricas por Operación"),
            "metric": m("Métrica", "Metric", "Métrica"),
            "value": m("Valor", "Value", "Valor"),
            "avg_win": m("Média Vitória (pips)", "Avg Win (pips)", "Media Victoria (pips)"),
            "avg_loss": m("Média Derrota (pips)", "Avg Loss (pips)", "Media Derrota (pips)"),
            "big_win": m("Maior Vitória (pips)", "Largest Win (pips)", "Mayor Victoria (pips)"),
            "big_loss": m("Maior Derrota (pips)", "Largest Loss (pips)", "Mayor Derrota (pips)"),
            "win_streak": m("Seq. Vitórias", "Win Streak", "Racha Victorias"),
            "loss_streak": m("Seq. Derrotas", "Loss Streak", "Racha Derrotas"),
            "asset": m("Ativo", "Asset", "Activo"),
            "wl": m("W/L", "W/L", "W/L"),
            "pnl": m("PnL", "PnL", "PnL"),
            "no_data": m("Nenhum dado ainda", "No data yet", "Aún sin datos"),
            "setup": m("Setup", "Setup", "Setup"),
            "history": m("Histórico de Operações", "Trade History", "Historial de Operaciones"),
            "h_date": m("Data", "Date", "Fecha"),
            "h_side": m("Lado", "Side", "Lado"),
            "h_entry": m("Entrada", "Entry", "Entrada"),
            "h_exit": m("Saída", "Exit", "Salida"),
            "h_pnl": m("PnL (pips)", "PnL (pips)", "PnL (pips)"),
            "h_result": m("Resultado", "Result", "Resultado"),
            "no_trades": m(
                "Nenhuma operação registrada ainda. Inicie o bot para começar a operar.",
                "No trades recorded yet. Start the bot to begin trading.",
                "Aún no hay operaciones registradas. Inicie el bot para comenzar a operar.",
            ),
        },
    }


_L10N = _build_l10n()


def _t(scope, key, lang):
    return _L10N[scope][key][lang]


def _clean_lang(lang):
    return lang if lang in SUPPORTED_LANGS else DEFAULT_LANG


def _find_free_port(start=5555, attempts=10):
    """Find a free port starting at start."""
    import socket
    for port in range(start, start + attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    return start  # fallback


def _html_head(title, lang=DEFAULT_LANG):
    lang_btns = ""
    for code in SUPPORTED_LANGS:
        active = " active" if code == lang else ""
        lang_btns += (
            f'<button type="button" class="lang-btn{active}" '
            f'data-lang="{code}">{code.upper()}</button>'
        )
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
:root {{
  --bg: #0a0e14;
  --surface: #121821;
  --surface-2: #0f151e;
  --border: #263044;
  --accent: #ff8700;
  --accent-soft: rgba(255,135,0,0.14);
  --win: #2ecc71;
  --loss: #ff5252;
  --text: #e6e9ef;
  --muted: #8fa0b8;
  --mono: "Cascadia Mono","JetBrains Mono",Consolas,"SF Mono",Menlo,monospace;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html {{ -webkit-text-size-adjust: 100%; }}
body {{ background: var(--bg); color: var(--text); font-family: var(--mono);
       line-height: 1.55; padding: 1.4rem; }}
.container {{ max-width: 1020px; margin: 0 auto; }}

/* --- Top bar --- */
.topbar {{ display: flex; align-items: baseline; justify-content: space-between;
          gap: 1rem; flex-wrap: wrap; padding-bottom: 1.1rem;
          border-bottom: 1px solid var(--border); margin-bottom: 1.6rem; }}
.brand {{ display: flex; align-items: center; gap: 0.75rem; font-size: 0.95rem;
         letter-spacing: 0.18em; font-weight: 700; }}
.brand-mark {{ color: var(--accent); }}
.live-dot {{ width: 10px; height: 10px; border-radius: 50%; background: var(--win);
            box-shadow: 0 0 0 0 rgba(46,204,113,0.6); animation: pulse 2.2s infinite; }}
@keyframes pulse {{
  0% {{ box-shadow: 0 0 0 0 rgba(46,204,113,0.55); }}
  70% {{ box-shadow: 0 0 0 9px rgba(46,204,113,0); }}
  100% {{ box-shadow: 0 0 0 0 rgba(46,204,113,0); }}
}}
.lang-switch {{ display: flex; align-items: center; gap: 0.3rem; }}
.lang-btn {{ padding: 0.3rem 0.7rem; background: var(--surface-2); color: var(--muted);
            border: 1px solid var(--border); border-radius: 3px; font-size: 0.68rem;
            font-weight: 700; letter-spacing: 0.06em; cursor: pointer; transition: all 0.15s; }}
.lang-btn:hover {{ color: var(--text); border-color: var(--accent); }}
.lang-btn.active {{ color: var(--accent); background: var(--accent-soft);
                   border-color: var(--accent); }}
.tagline {{ color: var(--muted); font-size: 0.72rem; letter-spacing: 0.05em;
           flex-basis: 100%; margin-top: 0.4rem; }}

/* --- Nav --- */
.nav {{ display: flex; gap: 0.35rem; margin-bottom: 1.6rem; }}
.nav a {{ color: var(--muted); text-decoration: none; padding: 0.5rem 1.1rem;
         border: 1px solid var(--border); border-radius: 4px;
         font-size: 0.8rem; letter-spacing: 0.06em; transition: all 0.15s; }}
.nav a:hover {{ color: var(--text); border-color: var(--accent); }}
.nav a.active {{ color: var(--accent); background: var(--accent-soft);
                border-color: var(--accent); font-weight: 700; }}

/* --- Layout --- */
h1 {{ font-size: 1.35rem; letter-spacing: 0.1em; margin-bottom: 0.4rem; }}
.subtitle {{ color: var(--muted); font-size: 0.82rem; margin-bottom: 1.8rem; }}

.panel {{ background: var(--surface); border: 1px solid var(--border);
         border-radius: 6px; padding: 1.4rem 1.6rem; margin-bottom: 1.4rem; }}
.eyebrow {{ display: flex; align-items: center; gap: 0.6rem; font-size: 0.7rem;
           letter-spacing: 0.2em; color: var(--accent); font-weight: 700;
           text-transform: uppercase; margin-bottom: 1.2rem; }}
.eyebrow::before {{ content: ""; width: 22px; height: 2px; background: var(--accent); }}

.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
        gap: 1rem 1.4rem; }}
label {{ display: block; color: var(--muted); font-size: 0.72rem;
        letter-spacing: 0.04em; margin-bottom: 0.35rem; }}
input, select {{ width: 100%; padding: 0.55rem 0.7rem; border-radius: 4px;
                border: 1px solid var(--border); background: var(--surface-2);
                color: var(--text); font-family: var(--mono); font-size: 0.85rem;
                transition: border-color 0.15s; }}
input:focus, select:focus {{ outline: none; border-color: var(--accent);
                            box-shadow: 0 0 0 2px var(--accent-soft); }}
input::placeholder {{ color: #56647a; }}

.actions {{ display: flex; justify-content: flex-end; gap: 0.9rem; margin-top: 1.8rem; }}
button {{ padding: 0.7rem 1.8rem; border-radius: 4px; border: none; cursor: pointer;
         font-family: var(--mono); font-size: 0.82rem; font-weight: 700;
         letter-spacing: 0.06em; transition: all 0.15s; }}
.btn-primary {{ background: var(--accent); color: #0a0e14; }}
.btn-primary:hover, .btn-primary:focus-visible {{ background: #ff9a2e; }}
.btn-secondary {{ background: var(--surface-2); color: var(--muted);
                 border: 1px solid var(--border); }}
.btn-secondary:hover {{ color: var(--text); border-color: var(--muted); }}

/* --- Report --- */
.stat-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
             gap: 1rem; margin-bottom: 1.6rem; }}
.stat {{ background: var(--surface); border: 1px solid var(--border); border-radius: 6px;
        padding: 1rem 0.6rem; text-align: center; }}
.stat-value {{ font-size: 1.35rem; font-weight: 700; letter-spacing: 0.02em; }}
.stat-label {{ font-size: 0.62rem; color: var(--muted); letter-spacing: 0.12em;
              text-transform: uppercase; margin-top: 0.35rem; }}
.win {{ color: var(--win); }}
.loss {{ color: var(--loss); }}

table {{ width: 100%; border-collapse: collapse; font-size: 0.78rem; }}
th {{ text-align: left; padding: 0.55rem 0.5rem; color: var(--muted);
     border-bottom: 1px solid var(--border); font-weight: 600;
     letter-spacing: 0.04em; white-space: nowrap; }}
td {{ padding: 0.5rem; border-bottom: 1px solid #1a2332; }}
tr:last-child td {{ border-bottom: none; }}
tr:hover td {{ background: rgba(255,135,0,0.04); }}
.empty {{ color: var(--muted); text-align: center; padding: 1.2rem 0; }}

/* --- Feedback --- */
.success-msg {{ background: #12301f; border: 1px solid var(--win); color: var(--win);
               padding: 1.4rem; border-radius: 6px; text-align: center;
               margin: 2rem auto; max-width: 560px; font-size: 0.9rem; }}
.footer {{ margin-top: 2.4rem; padding-top: 1.1rem; border-top: 1px solid var(--border);
          color: var(--muted); font-size: 0.68rem; letter-spacing: 0.08em;
          text-align: center; }}

@media (prefers-reduced-motion: reduce) {{
  .live-dot {{ animation: none; }}
  * {{ transition: none !important; }}
}}
</style>
<script>
function setLang(lang) {{
  document.cookie = "lang=" + lang + "; path=/; max-age=31536000";
  location.reload();
}}
document.addEventListener("DOMContentLoaded", function () {{
  document.querySelectorAll(".lang-btn").forEach(function (btn) {{
    btn.addEventListener("click", function () {{
      setLang(btn.dataset.lang);
    }});
  }});
}});
</script>
</head>
<body>
<div class="container">
<div class="topbar">
  <div class="brand"><span class="live-dot" aria-hidden="true"></span>
    <span><span class="brand-mark">MT5BOT</span> MAESTRO</span></div>
  <div class="lang-switch">{lang_btns}</div>
  <div class="tagline">MEASURED, DISCIPLINED EXECUTION</div>
</div>
"""


def _html_nav(active="config", lang=DEFAULT_LANG):
    config_cls = "active" if active == "config" else ""
    report_cls = "active" if active == "report" else ""
    return f"""
<div class="nav" role="navigation" aria-label="{_t('nav', 'label', lang)}">
    <a href="/config" class="{config_cls}">{_t('nav', 'config', lang)}</a>
    <a href="/report" class="{report_cls}">{_t('nav', 'report', lang)}</a>
</div>
"""


def _html_footer(lang=DEFAULT_LANG):
    return f"""
<div class="footer">{_L10N['footer'][lang]}</div>
</div>
</body>
</html>"""


def _build_timeframe_options():
    """Generate the HTML <option> for the timeframe selector."""
    options = []
    for tf_name, tf_value in config.AVAILABLE_TIMEFRAMES.items():
        selected = "selected" if tf_name == config.TIMEFRAME_NAME else ""
        options.append(f'<option value="{tf_name}" {selected}>{tf_name}</option>')
    return "\n".join(options)


def _page_config(lang=DEFAULT_LANG):
    """Render the configuration page in the given language."""
    t = {k: _t("config", k, lang) for k in _L10N["config"]}
    g = {k: _t("general", k, lang) for k in _L10N["general"]}
    p = _L10N["pages"]
    html = _html_head(p["config_title"][lang], lang)
    html += f"""
<h1>{p['config_h1'][lang]}</h1>
<p class="subtitle">{p['config_sub'][lang]}</p>
"""
    html += _html_nav("config", lang)
    html += f"""
<form method="POST" action="/config/save">

<div class="panel">
<div class="eyebrow">{t['assets_market']}</div>
<div class="grid">
<div>
<label for="symbols">{t['symbols']}</label>
<input type="text" id="symbols" name="symbols" value="{{symbols}}" placeholder="HK50, EURUSD, US500">
</div>
<div>
<label for="timeframe">{t['timeframe']}</label>
<select id="timeframe" name="timeframe">
{{timeframe_options}}
</select>
</div>
<div>
<label for="volume">{t['volume']}</label>
<input type="number" id="volume" name="volume" value="{{volume}}" step="0.01" min="0.01">
</div>
</div>
</div>

<div class="panel">
<div class="eyebrow">{t['strategy']}</div>
<div class="grid">
<div>
<label for="ema_period">{t['ema_fast']}</label>
<input type="number" id="ema_period" name="ema_period" value="{{ema_period}}" min="3" max="50">
</div>
<div>
<label for="ema_filter">{t['ema_filter']}</label>
<input type="number" id="ema_filter" name="ema_filter" value="{{ema_filter}}" min="10" max="200">
</div>
<div>
<label for="setup_92">{t['setup_92']}</label>
<select id="setup_92" name="setup_92">
<option value="1" {{s92_on}}>{g['enabled']}</option>
<option value="0" {{s92_off}}>{g['disabled']}</option>
</select>
</div>
<div>
<label for="setup_93">{t['setup_93']}</label>
<select id="setup_93" name="setup_93">
<option value="1" {{s93_on}}>{g['enabled']}</option>
<option value="0" {{s93_off}}>{g['disabled']}</option>
</select>
</div>
<div>
<label for="flat_filter">{t['flat']}</label>
<select id="flat_filter" name="flat_filter">
<option value="1" {{flat_on}}>{g['enabled']}</option>
<option value="0" {{flat_off}}>{g['disabled']}</option>
</select>
</div>
<div>
<label for="flat_threshold">{t['flat_ticks']}</label>
<input type="number" id="flat_threshold" name="flat_threshold" value="{{flat_threshold}}" min="1" max="50">
</div>
<div>
<label for="mtf_filter">{t['mtf']}</label>
<select id="mtf_filter" name="mtf_filter">
<option value="1" {{mtf_on}}>{g['enabled']}</option>
<option value="0" {{mtf_off}}>{g['disabled']}</option>
</select>
</div>
<div>
<label for="rvol_filter">{t['rvol']}</label>
<select id="rvol_filter" name="rvol_filter">
<option value="1" {{rvol_on}}>{g['enabled']}</option>
<option value="0" {{rvol_off}}>{g['disabled']}</option>
</select>
</div>
<div>
<label for="rvol_threshold">{t['rvol_th']}</label>
<input type="number" id="rvol_threshold" name="rvol_threshold" value="{{rvol_threshold}}" step="0.05" min="1.0" max="3.0">
</div>
<div>
<label for="rvol_lookback">{t['rvol_lb']}</label>
<input type="number" id="rvol_lookback" name="rvol_lookback" value="{{rvol_lookback}}" min="5" max="50">
</div>
</div>
</div>

<div class="panel">
<div class="eyebrow">{t['risk']}</div>
<div class="grid">
<div>
<label for="max_risk_pct">{t['risk_trade']}</label>
<input type="number" id="max_risk_pct" name="max_risk_pct" value="{{max_risk_pct}}" step="0.1" min="0.1" max="5.0">
</div>
<div>
<label for="abs_max_risk_pct">{t['abs_cap']}</label>
<input type="number" id="abs_max_risk_pct" name="abs_max_risk_pct" value="{{abs_max_risk_pct}}" step="0.1" min="0.5" max="10.0">
</div>
<div>
<label for="max_daily_loss_pct">{t['daily_loss']}</label>
<input type="number" id="max_daily_loss_pct" name="max_daily_loss_pct" value="{{max_daily_loss_pct}}" step="0.1" min="0.5" max="20.0">
</div>
<div>
<label for="max_spread">{t['spread']}</label>
<input type="number" id="max_spread" name="max_spread" value="{{max_spread}}" min="5" max="500">
</div>
<div>
<label for="enable_breakeven">{t['breakeven']}</label>
<select id="enable_breakeven" name="enable_breakeven">
<option value="1" {{be_on}}>{g['enabled']}</option>
<option value="0" {{be_off}}>{g['disabled']}</option>
</select>
</div>
<div>
<label for="trading_hours_enabled">{t['hours']}</label>
<select id="trading_hours_enabled" name="trading_hours_enabled">
<option value="1" {{th_on}}>{g['enabled']}</option>
<option value="0" {{th_off}}>{g['disabled']}</option>
</select>
</div>
<div>
<label for="trading_start_time">{t['start_time']}</label>
<input type="text" id="trading_start_time" name="trading_start_time" value="{{trading_start_time}}" placeholder="09:15">
</div>
<div>
<label for="trading_end_time">{t['end_time']}</label>
<input type="text" id="trading_end_time" name="trading_end_time" value="{{trading_end_time}}" placeholder="16:45">
</div>
</div>
</div>

<div class="panel">
<div class="eyebrow">{t['position']}</div>
<div class="grid">
<div>
<label for="partial_exit">{t['partial_exit']}</label>
<select id="partial_exit" name="partial_exit">
<option value="1" {{pe_on}}>{g['enabled']}</option>
<option value="0" {{pe_off}}>{g['disabled']}</option>
</select>
</div>
<div>
<label for="partial_pct">{t['partial_pct']}</label>
<input type="number" id="partial_pct" name="partial_pct" value="{{partial_pct}}" step="0.1" min="0.1" max="0.9">
</div>
<div>
<label for="partial_target">{t['partial_target']}</label>
<input type="number" id="partial_target" name="partial_target" value="{{partial_target}}" step="0.1" min="0.5" max="3.0">
</div>
<div>
<label for="adaptive_target">{t['adaptive']}</label>
<select id="adaptive_target" name="adaptive_target">
<option value="1" {{at_on}}>{g['enabled']}</option>
<option value="0" {{at_off}}>{g['disabled']}</option>
</select>
</div>
<div>
<label for="atr_threshold">{t['atr_th']}</label>
<input type="number" id="atr_threshold" name="atr_threshold" value="{{atr_threshold}}" step="0.1" min="1.0" max="3.0">
</div>
<div>
<label for="tick_offset">{t['tick_offset']}</label>
<input type="number" id="tick_offset" name="tick_offset" value="{{tick_offset}}" min="1" max="5">
</div>
</div>
</div>

<div class="panel">
<div class="eyebrow">{t['intervals']}</div>
<div class="grid">
<div>
<label for="scan_interval">{t['scan']}</label>
<input type="number" id="scan_interval" name="scan_interval" value="{{scan_interval}}" min="5" max="60">
</div>
<div>
<label for="retry_interval">{t['retry']}</label>
<input type="number" id="retry_interval" name="retry_interval" value="{{retry_interval}}" min="10" max="120">
</div>
<div>
<label for="rates_count">{t['rates']}</label>
<input type="number" id="rates_count" name="rates_count" value="{{rates_count}}" min="50" max="500">
</div>
</div>
</div>

<div class="actions">
<button type="button" class="btn-secondary" onclick="window.close()">{g['cancel']}</button>
<button type="submit" class="btn-primary">{g['save_start']}</button>
</div>
</form>
""".format(
        symbols=", ".join(config.AVAILABLE_SYMBOLS),
        volume=config.VOLUME_INITIAL,
        timeframe_options=_build_timeframe_options(),
        ema_period=config.EMA_PERIOD,
        ema_filter=config.EMA_FILTER_PERIOD,
        s92_on="selected" if config.SETUP_92_ENABLED else "",
        s92_off="" if config.SETUP_92_ENABLED else "selected",
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
    html += _html_footer(lang)
    return html


def _page_config_saved(lang=DEFAULT_LANG):
    """Confirmation page after saving."""
    p = _L10N["pages"]
    html = _html_head(p["ready_title"][lang], lang)
    html += f"""
<div class="success-msg">
    <h1>{p['ready_h1'][lang]}</h1>
    <p style="margin-top:0.8rem">{p['ready_msg'][lang]}</p>
</div>
"""
    html += _html_footer(lang)
    return html


def _page_report(lang=DEFAULT_LANG):
    """Performance report page."""
    summary = tracker.get_performance_summary()
    trades = tracker.get_closed_trades()
    t = {k: _t("report", k, lang) for k in _L10N["report"]}
    p = _L10N["pages"]

    html = _html_head(p["report_title"][lang], lang)
    html += f"""
<h1>{p['report_h1'][lang]}</h1>
<p class="subtitle">{p['report_sub'][lang]}</p>
"""
    html += _html_nav("report", lang)

    # Stats grid
    pnl_color = "win" if summary["total_pnl_pips"] >= 0 else "loss"
    html += f"""
<div class="stat-grid">
    <div class="stat"><div class="stat-value">{summary['total_trades']}</div><div class="stat-label">{t['trades']}</div></div>
    <div class="stat"><div class="stat-value {pnl_color}">{summary['total_pnl_pips']:+.2f}</div><div class="stat-label">{t['pnl_total']}</div></div>
    <div class="stat"><div class="stat-value">{summary['win_rate']}%</div><div class="stat-label">{t['win_rate']}</div></div>
    <div class="stat"><div class="stat-value">{summary['profit_factor']:.2f}</div><div class="stat-label">{t['profit_factor']}</div></div>
    <div class="stat"><div class="stat-value win">{summary['wins']}</div><div class="stat-label">{t['wins']}</div></div>
    <div class="stat"><div class="stat-value loss">{summary['losses']}</div><div class="stat-label">{t['losses']}</div></div>
    <div class="stat"><div class="stat-value">{summary['max_drawdown_pips']:.2f}</div><div class="stat-label">{t['max_dd']}</div></div>
    <div class="stat"><div class="stat-value">{summary['open_trades']}</div><div class="stat-label">{t['open_now']}</div></div>
</div>
"""

    # Details
    html += f"""
<div class="panel">
<div class="eyebrow">{t['per_trade']}</div>
<div class="grid">
<div>
<table>
<tr><th>{t['metric']}</th><th>{t['value']}</th></tr>
<tr><td>{t['avg_win']}</td><td class="win">{summary['avg_win_pips']:.5f}</td></tr>
<tr><td>{t['avg_loss']}</td><td class="loss">{summary['avg_loss_pips']:.5f}</td></tr>
<tr><td>{t['big_win']}</td><td class="win">{summary['largest_win_pips']:.5f}</td></tr>
<tr><td>{t['big_loss']}</td><td class="loss">{summary['largest_loss_pips']:.5f}</td></tr>
<tr><td>{t['win_streak']}</td><td>{summary['consecutive_wins']}</td></tr>
<tr><td>{t['loss_streak']}</td><td>{summary['consecutive_losses']}</td></tr>
</table>
</div>
<div>
<table>
<tr><th>{t['asset']}</th><th>{t['wl']}</th><th>{t['win_rate']}</th><th>{t['pnl']}</th></tr>
"""
    for sym, data in summary["by_symbol"].items():
        total = data["wins"] + data["losses"]
        wr = round((data["wins"] / total) * 100, 1) if total > 0 else 0
        pnl_cls = "win" if data["pnl_pips"] >= 0 else "loss"
        html += f'<tr><td>{sym}</td><td>{data["wins"]}/{data["losses"]}</td><td>{wr}%</td><td class="{pnl_cls}">{data["pnl_pips"]:+.2f}</td></tr>\n'

    if not summary["by_symbol"]:
        html += f'<tr><td colspan="4" class="empty">{t["no_data"]}</td></tr>'

    html += f"""
</table>
<br>
<table>
<tr><th>{t['setup']}</th><th>{t['wl']}</th><th>{t['win_rate']}</th><th>{t['pnl']}</th></tr>
"""
    for setup, data in summary["by_setup"].items():
        total = data["wins"] + data["losses"]
        wr = round((data["wins"] / total) * 100, 1) if total > 0 else 0
        pnl_cls = "win" if data["pnl_pips"] >= 0 else "loss"
        html += f'<tr><td>{setup}</td><td>{data["wins"]}/{data["losses"]}</td><td>{wr}%</td><td class="{pnl_cls}">{data["pnl_pips"]:+.2f}</td></tr>\n'

    if not summary["by_setup"]:
        html += f'<tr><td colspan="4" class="empty">{t["no_data"]}</td></tr>'

    html += f"""
</table>
</div>
</div>
</div>
"""

    # Trade history
    html += f"""
<div class="panel">
<div class="eyebrow">{t['history']}</div>
<table>
<tr><th>#</th><th>{t['h_date']}</th><th>{t['asset']}</th><th>{t['h_side']}</th><th>{t['setup']}</th><th>{t['h_entry']}</th><th>{t['h_exit']}</th><th>{t['h_pnl']}</th><th>{t['h_result']}</th></tr>
"""
    for trade in reversed(trades[-50:]):
        entry = f"{trade['entry_price']:.5f}" if trade['entry_price'] else "—"
        exit_p = f"{trade['exit_price']:.5f}" if trade['exit_price'] else "—"
        pnl_val = trade['pnl_pips'] if trade['pnl_pips'] is not None else 0
        pnl_str = f"{pnl_val:+.5f}" if trade['pnl_pips'] is not None else "—"
        pnl_cls = "win" if pnl_val > 0 else "loss" if pnl_val < 0 else ""
        result_str = trade['result'].upper()
        entry_time = trade.get('entry_time', '')[:16].replace('T', ' ') if trade.get('entry_time') else '—'
        html += f'<tr><td>{trade["id"]}</td><td>{entry_time}</td><td>{trade["symbol"]}</td><td>{trade["side"]}</td><td>{trade.get("setup","9.1")}</td><td>{entry}</td><td>{exit_p}</td><td class="{pnl_cls}">{pnl_str}</td><td>{result_str}</td></tr>\n'

    if not trades:
        html += f'<tr><td colspan="9" class="empty">{t["no_trades"]}</td></tr>'

    html += f"""
</table>
</div>
"""
    html += _html_footer(lang)
    return html


class _DashboardHandler(http.server.BaseHTTPRequestHandler):
    """HTTP handler for the dashboard."""

    def log_message(self, format, *args):
        pass  # Silence HTTP logs

    def _lang_from_cookie(self):
        raw = self.headers.get("Cookie", "")
        for part in raw.split(";"):
            part = part.strip()
            if part.startswith("lang="):
                return _clean_lang(part[len("lang="):].strip())
        return DEFAULT_LANG

    def do_GET(self):
        lang = self._lang_from_cookie()
        if self.path == "/" or self.path == "/config":
            self._respond(200, _page_config(lang))
        elif self.path == "/report":
            self._respond(200, _page_report(lang))
        elif self.path == "/api/summary":
            summary = tracker.get_performance_summary()
            self._respond_json(summary)
        else:
            self._respond(404, "<h1>404</h1>")

    def do_POST(self):
        if self.path == "/config/save":
            lang = self._lang_from_cookie()
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            params = urllib.parse.parse_qs(body)

            # Extract and apply config with validation
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
                _configured_data = {}

            _apply_config(_configured_data)

            self._respond(200, _page_config_saved(lang))

            _config_ready.set()
        else:
            self._respond(404, "<h1>404</h1>")

    def _respond(self, code, html_body):
        body = html_body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _respond_json(self, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _apply_config(data):
    """Apply web form data to config."""
    global _configured_data
    _configured_data = data

    if "symbols" in data:
        config.SYMBOLS = [s.strip() for s in data["symbols"].split(",") if s.strip()]
    if "volume" in data:
        config.VOLUME_INITIAL = data["volume"]
    if "ema_period" in data:
        config.EMA_PERIOD = data["ema_period"]
    if "ema_filter" in data:
        config.EMA_FILTER_PERIOD = data["ema_filter"]
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

    # Timeframe — validate against list of available timeframes
    tf_name = data.get("timeframe", "H1")
    if tf_name in config.AVAILABLE_TIMEFRAMES:
        config.TIMEFRAME = config.AVAILABLE_TIMEFRAMES[tf_name]
        config.TIMEFRAME_NAME = tf_name


def open_config():
    """Open configuration dashboard in the browser.
    Blocks until the user saves the configuration.
    Returns True if configuration was saved, False on timeout/cancel.
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

    # Wait until the user saves or 5-minute timeout
    configured = _config_ready.wait(timeout=300)

    _server.shutdown()
    return configured


def open_report():
    """Open report page in the browser."""
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