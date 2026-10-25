"""Dashboard web ao vivo do MT5Bot (v2.12).

Uso:  python -m interfaces.dashboard        (ou: bot.bat dashboard / /dashboard no Maestro)

So biblioteca padrao (http.server) e leve para i3/4GB. Abre no navegador:
  /         visao ao vivo: conta, rotas quant (risco x limite, proximo candle),
            posicoes do robo com P/L, curva de patrimonio e historico em US$.
            Atualiza sozinho a cada 5 s via /api/live.
  /config   configuracao atual (somente leitura) e onde muda-la.
Idiomas: pt (padrao), en, es — botao no topo (cookie).
"""
import html
import http.server
import json
import os
import sys
import threading
import time
import webbrowser

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import MetaTrader5 as mt5
import pandas as pd

from mt5bot.core import config, telemetry
from mt5bot.core import terminal
from mt5bot.data import tracker

DEFAULT_LANG = "pt"
SUPPORTED_LANGS = ("pt", "en", "es")
REFRESH_SECONDS = 5

_L10N = {
    "pt": {
        "live": "Ao vivo", "config": "Configuração", "balance": "Saldo", "equity": "Patrimônio",
        "free": "Margem livre", "today": "Hoje", "floating": "Flutuante do robô", "h_lot": "Lote", "account": "Conta",
        "routes": "Rotas quant", "risk": "Risco por trade", "limit": "limite", "next": "Próx. candle",
        "positions": "Posições do robô", "none_pos": "Nenhuma posição do robô — aguardando sinal.",
        "curve": "Curva de patrimônio (trades fechados)", "no_curve": "A curva aparece depois do primeiro trade fechado.",
        "perf": "Desempenho", "trades": "Trades", "win_rate": "Acerto", "net": "Resultado", "pf": "Fator de lucro",
        "max_dd": "Queda máxima", "by_setup": "Por estratégia", "history": "Últimos trades",
        "h_date": "Data", "h_symbol": "Ativo", "h_side": "Lado", "h_setup": "Setup", "h_result": "Resultado",
        "no_trades": "Nenhum trade fechado ainda.", "mt5_off": "MT5 desconectado — abra o terminal e faça login.",
        "updated": "atualizado", "real": "REAL", "demo": "DEMO", "locked": "travado", "ok": "ok",
        "cfg_sub": "Configuração atual (somente leitura). Para mudar, rode bot.bat config --edit (abre o config.toml) e reinicie o robô.",
        "cfg_quant": "Rotas quant (bot.bat quant)", "cfg_risk": "Proteção de capital", "cfg_classic": "Setups clássicos por ativo (Maestro)",
        "cfg_default_risk": "Perda máx. no SL (padrão)", "cfg_reserve": "Reserva de margem", "cfg_daily": "Perda diária máx.",
        "cfg_trade_risk": "Risco por trade (Maestro)", "cfg_spread": "Spread máx. (pontos)", "cfg_ml": "Filtro XGBoost",
        "cfg_own": "limite próprio", "footer": "MT5BOT · lote mínimo · SL/TP na corretora · stateless",
    },
    "en": {
        "live": "Live", "config": "Configuration", "balance": "Balance", "equity": "Equity",
        "free": "Free margin", "today": "Today", "floating": "Bot floating", "h_lot": "Lot", "account": "Account",
        "routes": "Quant routes", "risk": "Risk per trade", "limit": "limit", "next": "Next candle",
        "positions": "Bot positions", "none_pos": "No bot positions — waiting for a signal.",
        "curve": "Equity curve (closed trades)", "no_curve": "The curve appears after the first closed trade.",
        "perf": "Performance", "trades": "Trades", "win_rate": "Win rate", "net": "Net result", "pf": "Profit factor",
        "max_dd": "Max drawdown", "by_setup": "By strategy", "history": "Latest trades",
        "h_date": "Date", "h_symbol": "Symbol", "h_side": "Side", "h_setup": "Setup", "h_result": "Result",
        "no_trades": "No closed trades yet.", "mt5_off": "MT5 disconnected — open the terminal and log in.",
        "updated": "updated", "real": "LIVE", "demo": "DEMO", "locked": "locked", "ok": "ok",
        "cfg_sub": "Current configuration (read-only). To change it, run bot.bat config --edit (opens config.toml) and restart the bot.",
        "cfg_quant": "Quant routes (bot.bat quant)", "cfg_risk": "Capital protection", "cfg_classic": "Classic setups per symbol (Maestro)",
        "cfg_default_risk": "Max loss at SL (default)", "cfg_reserve": "Margin reserve", "cfg_daily": "Max daily loss",
        "cfg_trade_risk": "Risk per trade (Maestro)", "cfg_spread": "Max spread (points)", "cfg_ml": "XGBoost filter",
        "cfg_own": "own limit", "footer": "MT5BOT · minimum lot · SL/TP at the broker · stateless",
    },
    "es": {
        "live": "En vivo", "config": "Configuración", "balance": "Saldo", "equity": "Patrimonio",
        "free": "Margen libre", "today": "Hoy", "floating": "Flotante del robot", "h_lot": "Lote", "account": "Cuenta",
        "routes": "Rutas quant", "risk": "Riesgo por trade", "limit": "límite", "next": "Próx. vela",
        "positions": "Posiciones del robot", "none_pos": "Sin posiciones del robot — esperando señal.",
        "curve": "Curva de patrimonio (trades cerrados)", "no_curve": "La curva aparece después del primer trade cerrado.",
        "perf": "Rendimiento", "trades": "Trades", "win_rate": "Acierto", "net": "Resultado", "pf": "Factor de beneficio",
        "max_dd": "Caída máxima", "by_setup": "Por estrategia", "history": "Últimos trades",
        "h_date": "Fecha", "h_symbol": "Activo", "h_side": "Lado", "h_setup": "Setup", "h_result": "Resultado",
        "no_trades": "Aún no hay trades cerrados.", "mt5_off": "MT5 desconectado — abra el terminal e inicie sesión.",
        "updated": "actualizado", "real": "REAL", "demo": "DEMO", "locked": "bloqueado", "ok": "ok",
        "cfg_sub": "Configuración actual (solo lectura). Para cambiarla, ejecute bot.bat config --edit (abre el config.toml) y reinicie el robot.",
        "cfg_quant": "Rutas quant (bot.bat quant)", "cfg_risk": "Protección de capital", "cfg_classic": "Setups clásicos por activo (Maestro)",
        "cfg_default_risk": "Pérdida máx. en SL (por defecto)", "cfg_reserve": "Reserva de margen", "cfg_daily": "Pérdida diaria máx.",
        "cfg_trade_risk": "Riesgo por trade (Maestro)", "cfg_spread": "Spread máx. (puntos)", "cfg_ml": "Filtro XGBoost",
        "cfg_own": "límite propio", "footer": "MT5BOT · lote mínimo · SL/TP en el bróker · stateless",
    },
}


def _clean_lang(lang):
    return lang if lang in SUPPORTED_LANGS else DEFAULT_LANG


def _find_free_port(start=5555, attempts=10):
    import socket
    for port in range(start, start + attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    return start


# --- dados ---------------------------------------------------------------------

_TF = {"M15": mt5.TIMEFRAME_M15, "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4, "D1": mt5.TIMEFRAME_D1}
_mt5_ready = False


def _ensure_mt5():
    global _mt5_ready
    if not _mt5_ready:
        _mt5_ready = bool(terminal.initialize())
    return _mt5_ready


def _route_rows(balance):
    rows = []
    now = telemetry.server_now()
    for key, route in (getattr(config, "QUANT_ROUTES", {}) or {}).items():
        symbol = route.get("symbol", key)
        tf = route["timeframe"]
        row = {"symbol": key, "tf": tf, "setup": route["setup"], "risk": None, "limit": None, "next_close": "—",
               "study": str(route.get("mode", "live")).lower() == "study"}
        rates = mt5.copy_rates_from_pos(symbol, _TF.get(tf, mt5.TIMEFRAME_H1), 0, 201)
        if rates is not None and len(rates) > 2:
            df = pd.DataFrame(rates[:-1])
            row["risk"], row["limit"] = telemetry.route_risk(symbol, route, df, balance)
            tick = mt5.symbol_info_tick(symbol)
            row["next_close"] = telemetry.next_close_text(int(rates[-1]["time"]), telemetry.TF_SECONDS[tf],
                                                          int(getattr(tick, "time", 0) or 0), now)
        rows.append(row)
    return rows


def live_snapshot():
    """Tudo que a pagina /: conta, rotas, posicoes, estatisticas e historico."""
    trades = tracker.get_all_trades()
    closed = [t for t in trades if t.get("result") in ("win", "loss", "breakeven")]
    # Ordem cronologica de saida (o arquivo guarda na ordem de gravacao).
    closed.sort(key=lambda t: t.get("exit_time") or t.get("entry_time") or "")
    stats = telemetry.trade_stats(closed)
    snap = {"mt5_ok": _ensure_mt5(), "generated_at": time.strftime("%H:%M:%S"),
            "account": None, "today": round(float(tracker.get_daily_pnl() or 0.0), 2),
            "routes": [], "positions": [], "stats": stats,
            "by_setup": telemetry.group_stats(closed, "setup"),
            "history": [{"time": (t.get("exit_time") or t.get("entry_time") or "")[:16].replace("T", " "),
                         "symbol": t.get("symbol"), "side": t.get("side"), "setup": t.get("setup"),
                         "pnl": round(float(t.get("pnl_money") or 0.0), 2), "result": t.get("result")}
                        for t in reversed(closed[-30:])]}
    if snap["mt5_ok"]:
        snap["account"] = telemetry.account_snapshot()
        snap["positions"] = telemetry.bot_positions()
        snap["routes"] = _route_rows((snap["account"] or {}).get("balance", 0.0))
    return snap


# --- paginas -------------------------------------------------------------------

_CSS = """
:root{--bg:#0b0f17;--surface:#121826;--surface2:#0e1420;--border:#232c3f;--accent:#ff8700;--accent-soft:rgba(255,135,0,.13);
--win:#3ddc84;--loss:#ff5c6c;--warn:#f5c04e;--blue:#6ea8ff;--purple:#b48cff;--text:#e7ebf3;--muted:#8d9ab2;
--mono:"Cascadia Mono","JetBrains Mono",Consolas,"SF Mono",Menlo,monospace;--sans:"Segoe UI",Inter,system-ui,-apple-system,sans-serif}
*{margin:0;padding:0;box-sizing:border-box}
body{background:radial-gradient(1200px 600px at 10% -10%,#1a2236 0,transparent 60%),var(--bg);color:var(--text);
font-family:var(--sans);line-height:1.5;padding:1.25rem;min-height:100vh}
.wrap{max-width:1180px;margin:0 auto}
.top{display:flex;align-items:center;gap:.9rem;flex-wrap:wrap;margin-bottom:1.25rem}
.brand{display:flex;align-items:center;gap:.6rem;font-family:var(--mono);font-weight:800;letter-spacing:.14em}
.brand b{color:var(--accent)}
.dot{width:9px;height:9px;border-radius:50%;background:var(--win);box-shadow:0 0 0 0 rgba(61,220,132,.6);animation:pulse 2s infinite}
.dot.off{background:var(--loss);animation:none}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(61,220,132,.55)}70%{box-shadow:0 0 0 8px rgba(61,220,132,0)}100%{box-shadow:0 0 0 0 rgba(61,220,132,0)}}
.nav{display:flex;gap:.3rem;margin-left:auto}
.nav a,.lang button{color:var(--muted);text-decoration:none;font-size:.8rem;padding:.4rem .85rem;border:1px solid var(--border);
border-radius:999px;background:transparent;cursor:pointer;font-family:var(--sans)}
.nav a.on,.lang button.on{color:var(--accent);border-color:var(--accent);background:var(--accent-soft);font-weight:700}
.nav a:hover,.lang button:hover{color:var(--text);border-color:var(--muted)}
.lang{display:flex;gap:.25rem}
.pill{font-family:var(--mono);font-size:.7rem;font-weight:800;letter-spacing:.08em;padding:.2rem .55rem;border-radius:999px}
.pill.real{background:#b4233c;color:#fff}.pill.demo{background:#1f8a4c;color:#fff}
.banner{background:rgba(255,92,108,.12);border:1px solid var(--loss);color:var(--loss);padding:.8rem 1rem;border-radius:10px;margin-bottom:1rem}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:.8rem;margin-bottom:1rem}
.kpi{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:.9rem 1rem}
.kpi .l{font-size:.7rem;color:var(--muted);letter-spacing:.1em;text-transform:uppercase}
.kpi .v{font-family:var(--mono);font-size:1.45rem;font-weight:800;margin-top:.15rem}
.grid2{display:grid;grid-template-columns:1.25fr 1fr;gap:1rem}
@media(max-width:860px){.grid2{grid-template-columns:1fr}}
.card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:1rem 1.1rem;margin-bottom:1rem}
.card h2{font-size:.72rem;letter-spacing:.18em;text-transform:uppercase;color:var(--accent);margin-bottom:.8rem;display:flex;gap:.5rem;align-items:center}
.card h2::before{content:"";width:18px;height:2px;background:var(--accent)}
.route{display:grid;grid-template-columns:1fr auto;gap:.2rem .8rem;padding:.7rem 0;border-bottom:1px solid var(--border)}
.route:last-child{border-bottom:none}
.route .sym{font-family:var(--mono);font-weight:800;font-size:1.05rem}
.route .meta{color:var(--muted);font-size:.8rem}
.route .risk{font-family:var(--mono);font-size:.85rem;text-align:right}
.tag{font-family:var(--mono);font-size:.68rem;font-weight:800;color:var(--purple);border:1px solid rgba(180,140,255,.4);border-radius:6px;padding:.05rem .4rem;margin-left:.4rem}
table{width:100%;border-collapse:collapse;font-size:.82rem}
th{text-align:left;color:var(--muted);font-weight:600;padding:.45rem .4rem;border-bottom:1px solid var(--border);font-size:.72rem;letter-spacing:.06em;text-transform:uppercase}
td{padding:.5rem .4rem;border-bottom:1px solid rgba(35,44,63,.6);font-family:var(--mono)}
tr:last-child td{border-bottom:none}
.win{color:var(--win)}.loss{color:var(--loss)}.warn{color:var(--warn)}.muted{color:var(--muted)}
.empty{color:var(--muted);padding:1rem 0;text-align:center;font-size:.85rem}
svg{width:100%;height:190px;display:block}
.foot{color:var(--muted);font-size:.72rem;text-align:center;margin-top:1.4rem;letter-spacing:.08em}
.upd{color:var(--muted);font-size:.75rem;font-family:var(--mono)}
dl{display:grid;grid-template-columns:auto 1fr;gap:.45rem 1rem;font-size:.86rem}dt{color:var(--muted)}dd{font-family:var(--mono)}
@media(prefers-reduced-motion:reduce){.dot{animation:none}}
"""


def _head(title, lang, active):
    L = _L10N[lang]
    langs = "".join(f'<button type="button" data-lang="{c}" class="{"on" if c == lang else ""}">{c.upper()}</button>'
                    for c in SUPPORTED_LANGS)
    return f"""<!DOCTYPE html><html lang="{lang}"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><style>{_CSS}</style></head>
<body><div class="wrap"><div class="top">
<div class="brand"><span class="dot" id="dot"></span><span><b>MT5BOT</b> MAESTRO</span></div>
<span id="acct"></span><span class="upd" id="upd"></span>
<nav class="nav"><a href="/" class="{"on" if active == "live" else ""}">{L["live"]}</a>
<a href="/config" class="{"on" if active == "config" else ""}">{L["config"]}</a></nav>
<div class="lang">{langs}</div></div>"""


_LANG_JS = """document.querySelectorAll('.lang button').forEach(b=>b.addEventListener('click',()=>{
document.cookie='lang='+b.dataset.lang+'; path=/; max-age=31536000';location.reload();}));"""


def _foot(lang):
    return f'<div class="foot">{_L10N[lang]["footer"]}</div></div><script>{_LANG_JS}</script></body></html>'


def page_live(lang=DEFAULT_LANG):
    L = _L10N[lang]
    body = f"""
<div id="banner"></div>
<div class="kpis">
 <div class="kpi"><div class="l">{L["balance"]}</div><div class="v" id="k-bal">—</div></div>
 <div class="kpi"><div class="l">{L["equity"]}</div><div class="v" id="k-eq">—</div></div>
 <div class="kpi"><div class="l">{L["free"]}</div><div class="v" id="k-free">—</div></div>
 <div class="kpi"><div class="l">{L["today"]}</div><div class="v" id="k-today">—</div></div>
 <div class="kpi"><div class="l">{L["floating"]}</div><div class="v" id="k-float">—</div></div>
</div>
<div class="grid2">
 <div>
  <div class="card"><h2>{L["routes"]}</h2><div id="routes"></div></div>
  <div class="card"><h2>{L["positions"]}</h2><div id="positions"></div></div>
 </div>
 <div>
  <div class="card"><h2>{L["curve"]}</h2><div id="curve"></div></div>
  <div class="card"><h2>{L["perf"]}</h2><div id="perf"></div></div>
 </div>
</div>
<div class="card"><h2>{L["history"]}</h2><div id="history"></div></div>
<script>
const L={json.dumps(L, ensure_ascii=False)};const REFRESH={REFRESH_SECONDS * 1000};
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
const money=v=>{{v=+v||0;const c=v>0?'win':v<0?'loss':'';return `<span class="${{c}}">${{v>0?'+':v<0?'-':''}}$${{Math.abs(v).toFixed(2)}}</span>`;}};
function curve(points){{
 if(!points.length) return `<div class="empty">${{L.no_curve}}</div>`;
 const ys=[0,...points.map(p=>p.equity)],min=Math.min(...ys),max=Math.max(...ys),span=(max-min)||1,W=600,H=180,n=ys.length;
 const xy=ys.map((y,i)=>[i*(W/(n-1||1)),H-10-((y-min)/span)*(H-20)]);
 const line=xy.map(p=>p.join(',')).join(' '),zero=H-10-((0-min)/span)*(H-20),last=ys[ys.length-1],col=last>=0?'var(--win)':'var(--loss)';
 return `<svg viewBox="0 0 ${{W}} ${{H}}" preserveAspectRatio="none" role="img" aria-label="${{L.curve}}">
  <line x1="0" x2="${{W}}" y1="${{zero}}" y2="${{zero}}" stroke="var(--border)" stroke-dasharray="4 4"/>
  <polygon points="0,${{zero}} ${{line}} ${{W}},${{zero}}" fill="${{col}}" opacity=".12"/>
  <polyline points="${{line}}" fill="none" stroke="${{col}}" stroke-width="2.5" vector-effect="non-scaling-stroke"/></svg>
  <div class="upd" style="text-align:right">${{money(last)}}</div>`;
}}
function render(d){{
 $('dot').className='dot'+(d.mt5_ok?'':' off');$('upd').textContent=L.updated+' '+d.generated_at;
 $('banner').innerHTML=d.mt5_ok?'':`<div class="banner">${{L.mt5_off}}</div>`;
 const a=d.account;$('acct').innerHTML=a?`<span class="pill ${{a.real?'real':'demo'}}">${{a.real?L.real:L.demo}}</span>`:'';
 const fl=d.positions.reduce((s,p)=>s+p.profit,0);
 $('k-bal').textContent=a?'$'+a.balance.toFixed(2):'—';$('k-eq').textContent=a?'$'+a.equity.toFixed(2):'—';
 $('k-free').textContent=a?'$'+a.margin_free.toFixed(2):'—';$('k-today').innerHTML=money(d.today);$('k-float').innerHTML=money(fl);
 $('routes').innerHTML=d.routes.length?d.routes.map(r=>{{
  const ok=r.risk!=null&&r.risk<=r.limit;
  const risk=r.study?'<span class="muted">📘 estudo</span>':r.risk==null?'<span class="muted">—</span>':ok?`<span class="win">✓ $${{r.risk.toFixed(2)}}</span> <span class="muted">/ ${{L.limit}} $${{r.limit.toFixed(2)}}</span>`
   :`<span class="warn">🔒 $${{r.risk.toFixed(2)}} &gt; ${{L.limit}} $${{r.limit.toFixed(2)}}</span>`;
  return `<div class="route"><div><span class="sym">${{esc(r.symbol)}}</span><span class="tag">${{esc(r.tf)}} · ${{esc(r.setup)}}</span>
   <div class="meta">${{L.next}}: ${{esc(r.next_close)}}</div></div><div class="risk">${{L.risk}}<br>${{risk}}</div></div>`;}}).join('')
  :`<div class="empty">—</div>`;
 $('positions').innerHTML=d.positions.length?`<table><tr><th>${{L.h_symbol}}</th><th>${{L.h_side}}</th><th>${{L.h_lot}}</th><th>@</th><th>SL</th><th>TP</th><th>P/L</th></tr>`+
  d.positions.map(p=>`<tr><td>${{esc(p.symbol)}}</td><td class="${{p.side=='BUY'?'win':'loss'}}">${{p.side=='BUY'?'▲ BUY':'▼ SELL'}}</td><td>${{p.volume}}</td>
  <td>${{p.open.toFixed(2)}}</td><td>${{p.sl.toFixed(2)}}</td><td>${{p.tp?p.tp.toFixed(2):'—'}}</td><td>${{money(p.profit)}}</td></tr>`).join('')+'</table>'
  :`<div class="empty">${{L.none_pos}}</div>`;
 $('curve').innerHTML=curve(d.stats.curve);
 const s=d.stats;
 $('perf').innerHTML=`<dl><dt>${{L.trades}}</dt><dd>${{s.trades}} (${{s.wins}}/${{s.losses}})</dd><dt>${{L.win_rate}}</dt><dd>${{s.win_rate}}%</dd>
  <dt>${{L.net}}</dt><dd>${{money(s.net)}}</dd><dt>${{L.pf}}</dt><dd>${{s.profit_factor??'—'}}</dd><dt>${{L.max_dd}}</dt><dd class="loss">$${{s.max_drawdown.toFixed(2)}}</dd></dl>`+
  (Object.keys(d.by_setup).length?`<table style="margin-top:.8rem"><tr><th>${{L.by_setup}}</th><th>${{L.trades}}</th><th>${{L.win_rate}}</th><th>${{L.net}}</th></tr>`+
  Object.entries(d.by_setup).map(([k,v])=>`<tr><td>${{esc(k)}}</td><td>${{v.trades}}</td><td>${{v.win_rate}}%</td><td>${{money(v.net)}}</td></tr>`).join('')+'</table>':'');
 $('history').innerHTML=d.history.length?`<table><tr><th>${{L.h_date}}</th><th>${{L.h_symbol}}</th><th>${{L.h_side}}</th><th>${{L.h_setup}}</th><th>${{L.h_result}}</th></tr>`+
  d.history.map(t=>`<tr><td>${{esc(t.time)}}</td><td>${{esc(t.symbol)}}</td><td>${{esc(t.side)}}</td><td>${{esc(t.setup)}}</td><td>${{money(t.pnl)}}</td></tr>`).join('')+'</table>'
  :`<div class="empty">${{L.no_trades}}</div>`;
}}
async function tick(){{try{{const r=await fetch('/api/live',{{cache:'no-store'}});render(await r.json());}}catch(e){{$('dot').className='dot off';}}}}
tick();setInterval(tick,REFRESH);
</script>"""
    return _head("MT5Bot — " + L["live"], lang, "live") + body + _foot(lang)


def page_config(lang=DEFAULT_LANG):
    L = _L10N[lang]
    e = lambda v: html.escape(str(v))
    routes = ""
    for sym, r in (getattr(config, "QUANT_ROUTES", {}) or {}).items():
        params = ", ".join(f"{k}={v}" for k, v in (r.get("params") or {}).items())
        own = f' <span class="warn">· {L["cfg_own"]} {e(r["max_risk_pct"])}%</span>' if r.get("max_risk_pct") is not None else ""
        if f"QUANT_ROUTES.{sym}.max_risk_pct" in getattr(config, "CONFIG_SOURCES", {}):
            own += ' <span class="pill demo">config.toml</span>'
        routes += (f'<tr><td><b>{e(sym)}</b></td><td>{e(r.get("timeframe"))}</td><td>{e(r.get("setup"))}</td>'
                   f'<td class="muted">{e(params)}{own}</td></tr>')
    classic = "".join(f"<tr><td><b>{e(a)}</b></td><td class='muted'>{e(', '.join(s))}</td></tr>"
                      for a, s in (getattr(config, "ASSET_SETUPS", {}) or {}).items())
    body = f"""
<p class="muted" style="margin-bottom:1rem">{L["cfg_sub"]}<br>config.toml: <code>{e(getattr(config, "USER_CONFIG_FILE", ""))}</code></p>
<div class="grid2">
 <div class="card"><h2>{L["cfg_quant"]}</h2><table><tr><th>{L["h_symbol"]}</th><th>TF</th><th>Setup</th><th></th></tr>{routes}</table></div>
 <div class="card"><h2>{L["cfg_risk"]}</h2><dl>
  <dt>{L["cfg_default_risk"]}</dt><dd>{e(getattr(config, "QUANT_MAX_RISK_PCT", 2.0))}%</dd>
  <dt>{L["cfg_reserve"]}</dt><dd>{e(getattr(config, "QUANT_MARGIN_RESERVE_MULT", 3.0))}×</dd>
  <dt>{L["cfg_daily"]}</dt><dd>{e(config.MAX_DAILY_LOSS_PERCENT)}%</dd>
  <dt>{L["cfg_trade_risk"]}</dt><dd>{e(config.MAX_RISK_PER_TRADE_PERCENT)}%</dd>
  <dt>{L["cfg_spread"]}</dt><dd>{e(config.MAX_SPREAD_POINTS)}</dd>
  <dt>{L["cfg_ml"]}</dt><dd>{"ON" if getattr(config, "ML_FILTER_ENABLED", False) else "OFF"} · {e(getattr(config, "ML_MIN_WIN_PROB", 0.4))}</dd>
  <dt>MAGIC</dt><dd>{e(config.MAGIC)}</dd></dl></div>
</div>
<div class="card"><h2>{L["cfg_classic"]}</h2><table>{classic}</table></div>"""
    return _head("MT5Bot — " + L["config"], lang, "config") + body + _foot(lang)


class DashboardHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # sem log HTTP no console

    def _lang(self):
        for part in self.headers.get("Cookie", "").split(";"):
            part = part.strip()
            if part.startswith("lang="):
                return _clean_lang(part[5:].strip())
        return DEFAULT_LANG

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/live"):
            self._send(200, page_live(self._lang()), "text/html")
        elif path == "/config":
            self._send(200, page_config(self._lang()), "text/html")
        elif path == "/api/live":
            try:
                self._send(200, json.dumps(live_snapshot(), ensure_ascii=False, default=str), "application/json")
            except Exception as ex:
                self._send(500, json.dumps({"error": str(ex)}), "application/json")
        else:
            self._send(404, "<h1>404</h1>", "text/html")

    def _send(self, code, text, ctype):
        body = text.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", f"{ctype}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def serve(open_browser=True, port=None):
    port = port or _find_free_port()
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), DashboardHandler)
    url = f"http://localhost:{port}/"
    print(f"\n  MT5Bot dashboard: {url}\n  Ctrl+C para fechar.\n")
    if open_browser:
        threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    return server, url


def main():
    server, _ = serve()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
