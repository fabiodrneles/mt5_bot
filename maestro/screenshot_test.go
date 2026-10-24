package main

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/charmbracelet/bubbles/viewport"
	"github.com/charmbracelet/lipgloss"
	"github.com/muesli/termenv"
)

// TestManualScreenshot grava a tela do Maestro (com cores ANSI) para as figuras
// do manual (tools/manual_screenshots.py). So roda com MT5BOT_SCREENSHOT=<arquivo>.
// Os dados sao de demonstracao: nenhuma conta real.
func TestManualScreenshot(t *testing.T) {
	out := os.Getenv("MT5BOT_SCREENSHOT")
	if out == "" {
		t.Skip("defina MT5BOT_SCREENSHOT para gerar a figura do manual")
	}
	lipgloss.SetColorProfile(termenv.TrueColor)
	// Historico de demonstracao numa pasta temporaria, nunca o trades.json do usuario.
	data := t.TempDir()
	t.Setenv("APPDATA", data)
	demo := `[{"result":"win","pnl_money":0.42,"symbol":"HK50","setup":"PULLB"},
{"result":"loss","pnl_money":-0.21,"symbol":"HK50","setup":"PULLB"},
{"result":"win","pnl_money":0.43,"symbol":"HK50","setup":"PULLB"},
{"result":"loss","pnl_money":-0.20,"symbol":"HK50","setup":"PULLB"},
{"result":"loss","pnl_money":-0.21,"symbol":"HK50","setup":"PULLB"}]`
	if err := os.MkdirAll(filepath.Join(data, "mt5bot"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(data, "mt5bot", "trades.json"), []byte(demo), 0o644); err != nil {
		t.Fatal(err)
	}

	m := initialModel()
	m.width, m.height = 120, 32
	m.ready = true
	m.viewport = viewport.New(m.width, m.height)

	risk := func(v float64) *float64 { return &v }
	acct := &Account{Login: 12345678, Real: false, Balance: 16.26, Equity: 16.48, MarginFree: 12.90}
	hk := NewPythonWorker("HK50", "H4")
	hk.StatusText = "🟢 IN_POSITION (PULLB BUY)"
	hk.SetTelemetry(Telemetry{Account: acct, Validated: true, LiveAllowed: true, NextClose: "1h12m",
		Quant:     &QuantInfo{Setup: "PULLB", Risk: risk(0.21), Limit: 0.33},
		Positions: []Position{{Side: "BUY", Volume: 0.01, Open: 25840, SL: 25610, TP: 26300, Profit: 0.22, Setup: "PULLB"}}})
	us := NewPythonWorker("US500", "D1")
	us.StatusText = "🔵 AGUARDANDO SINAL (RSI2MR)"
	us.SetTelemetry(Telemetry{Account: acct, Validated: true, LiveAllowed: true, NextClose: "9h40m",
		Quant: &QuantInfo{Setup: "RSI2MR", Risk: risk(1.62), Limit: 1.95}})
	for _, w := range []*PythonWorker{hk, us} {
		_ = m.manager.Add(w)
	}
	m.updateStatus()
	m.logs = []string{
		"[MAESTRO] Robô HK50 H4 iniciado (Python embutido)",
		"[MAESTRO] Robô US500 D1 iniciado (Python embutido)",
		"[HK50] PULLB BUY: toque na EMA20 com fechamento acima; SL 1 ATR, TP 2 ATR",
		"[HK50] Risco no lote mínimo $0.21 <= limite $0.33; margem livre ok (3x)",
		"[HK50] Enviando ordem a MERCADO 0.01 com SL 25610 e TP 26300",
		"[US500] RSI(2)=41.7: sem sinal; próximo candle D1 em 9h40m",
	}
	m.viewport.SetContent(wrapLogs(m.logs, m.viewport.Width))
	m.viewport.GotoBottom()

	if err := os.WriteFile(out, []byte(m.View()), 0o644); err != nil {
		t.Fatal(err)
	}
}
