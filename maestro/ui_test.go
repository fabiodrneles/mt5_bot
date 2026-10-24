package main

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/charmbracelet/bubbles/viewport"
	tea "github.com/charmbracelet/bubbletea"
)

func f64(v float64) *float64 { return &v }

func TestStatusBadgeEstadosQuant(t *testing.T) {
	cases := map[string]string{
		"🟢 EM POSIÇÃO (PULLB BUY)":      "POS",
		"🟢 SAIDA RSI2MR":               "POS",
		"⏳ AGUARDANDO MERCADO":          "WAIT",
		"🔵 AGUARDANDO PRÓXIMO CANDLE":   "WAIT",
		"🔵 SINAL EXPIRADO":              "WAIT",
		"🟡 SEM MARGEM":                  "LOCK",
		"🔴 ML VETO":                     "WAIT",
		"🔴 SEM TICK":                    "ERRO",
	}
	for state, want := range cases {
		if got := statusBadge(state).Label; got != want {
			t.Fatalf("statusBadge(%q)=%q, esperado %q", state, got, want)
		}
	}
}

func TestHandleResponseGuardaTelemetria(t *testing.T) {
	w := NewPythonWorker("HK50", "H4")
	w.handleResponse(`{"symbol":"HK50","state_text":"🔵 SCANNING","telemetry":{"account":{"login":1,"real":true,"balance":16.26,"equity":16.1,"margin_free":14.35},"positions":[{"side":"BUY","volume":0.01,"open":23050,"sl":22850,"tp":23450,"profit":0.12,"setup":"PULLB"}],"next_close":"em 1h 05m","quant":{"setup":"PULLB","risk":0.21,"limit":0.33}}}`)
	status, tel, at := w.Snapshot()
	if status != "🔵 SCANNING" || at.IsZero() {
		t.Fatalf("status/at nao atualizados: %q %v", status, at)
	}
	if tel.Account == nil || tel.Account.Balance != 16.26 || !tel.Account.Real {
		t.Fatalf("conta nao parseada: %+v", tel.Account)
	}
	if tel.Quant == nil || *tel.Quant.Risk != 0.21 || len(tel.Positions) != 1 || tel.NextClose != "em 1h 05m" {
		t.Fatalf("telemetria incompleta: %+v", tel)
	}
}

func TestRobotCardsMostraQuantRiscoEPosicao(t *testing.T) {
	ok := NewPythonWorker("HK50", "H4")
	ok.ColorHex = string(ColorBlue)
	ok.StatusText = "🟢 EM POSIÇÃO (PULLB BUY)"
	ok.SetTelemetry(Telemetry{NextClose: "em 1h 05m", Quant: &QuantInfo{Setup: "PULLB", Risk: f64(0.21), Limit: 0.33},
		Positions: []Position{{Side: "BUY", Volume: 0.01, Open: 23050, Profit: 0.12}}})
	locked := NewPythonWorker("US500", "D1")
	locked.ColorHex = string(ColorGreen)
	locked.StatusText = "🔵 SCANNING"
	locked.SetTelemetry(Telemetry{Quant: &QuantInfo{Setup: "RSI2MR", Risk: f64(1.62), Limit: 0.33}})

	out := stripAnsi(robotCards([]*PythonWorker{ok, locked}, 44))
	for _, want := range []string{"ROBÔS", "● HK50", "[POS]", "EM POSIÇÃO (PULLB BUY)", "★ QUANT PULLB",
		"candle em 1h 05m", "✓ risco $0.21 / limite $0.33", "▲ BUY 0.01 @ 23050.00  +$0.12",
		"● US500", "🔒 risco $1.62 > limite $0.33"} {
		if !strings.Contains(out, want) {
			t.Fatalf("cartoes sem %q:\n%s", want, out)
		}
	}
}

func TestRobotCardsVazioEnsinaComoComecar(t *testing.T) {
	out := stripAnsi(robotCards(nil, 40))
	if !strings.Contains(out, "/add HK50 H4") || !strings.Contains(out, "/study HK50 H1") {
		t.Fatalf("estado vazio deveria guiar o usuario:\n%s", out)
	}
}

func TestHeaderMostraContaRealSaldoEFlutuante(t *testing.T) {
	m := buildState(140, 30)
	w := m.manager.List()[0]
	w.SetTelemetry(Telemetry{Account: &Account{Real: true, Balance: 16.26, Equity: 16.38, MarginFree: 14.2},
		Positions: []Position{{Side: "BUY", Profit: 0.12}}})
	out := stripAnsi(m.headerView())
	for _, want := range []string{"MT5BOT MAESTRO v", "CONTA REAL", "Saldo $16.26", "Patrimônio $16.38",
		"Margem livre $14.20", "Flutuante +$0.12", "Posições do robô 1"} {
		if !strings.Contains(out, want) {
			t.Fatalf("cabecalho sem %q:\n%s", want, out)
		}
	}
}

func TestEscLimpaLinhaSemSair(t *testing.T) {
	m := initialModel()
	m.ready = true
	m.viewport = viewport.New(60, 10)
	m.textInput.SetValue("/add HK")
	next, cmd := m.Update(tea.KeyMsg{Type: tea.KeyEsc})
	if cmd != nil {
		if _, quit := cmd().(tea.QuitMsg); quit {
			t.Fatal("Esc nao deve encerrar o Maestro")
		}
	}
	if v := next.(model).textInput.Value(); v != "" {
		t.Fatalf("Esc deveria limpar a linha, ficou %q", v)
	}
}

func TestSugestoesIncluemRotasQuant(t *testing.T) {
	joined := strings.Join(commandSuggestions, "|")
	for _, want := range []string{"/add HK50 H4", "/add US500 D1", "/quit close-all"} {
		if !strings.Contains(joined, want) {
			t.Fatalf("sugestoes sem %q", want)
		}
	}
}

func TestReportLinesEmDolarPorSetup(t *testing.T) {
	p := func(v float64) *float64 { return &v }
	trades := []Trade{{Result: "win", PnLMoney: p(0.4), Setup: "PULLB"}, {Result: "loss", PnLMoney: p(-0.2), Setup: "PULLB"},
		{Result: "loss", PnLMoney: p(-1.6), Setup: "RSI2MR"}, {Result: "open", Setup: "PULLB"}}
	out := stripAnsi(strings.Join(reportLines(trades), "\n"))
	for _, want := range []string{"Total: 3 trades", "-$1.40", "PULLB", "+$0.20", "RSI2MR", "-$1.60"} {
		if !strings.Contains(out, want) {
			t.Fatalf("relatorio sem %q:\n%s", want, out)
		}
	}
}

func TestReadTradesFileUsaCacheAteArquivoMudar(t *testing.T) {
	path := filepath.Join(t.TempDir(), "trades.json")
	os.WriteFile(path, []byte(`[{"result":"win","pnl_money":1,"symbol":"HK50"}]`), 0o644)
	a, _ := readTradesFile(path)
	b, _ := readTradesFile(path)
	if len(a) != 1 || &a[0] != &b[0] {
		t.Fatal("segunda leitura deveria vir do cache")
	}
	later := time.Now().Add(2 * time.Second)
	os.WriteFile(path, []byte(`[{"result":"win","pnl_money":1},{"result":"loss","pnl_money":-1}]`), 0o644)
	os.Chtimes(path, later, later)
	c, _ := readTradesFile(path)
	if len(c) != 2 {
		t.Fatalf("arquivo mudou e o cache nao invalidou: %d trades", len(c))
	}
}

func TestClipLinesLimitaAltura(t *testing.T) {
	out := clipLines("a\nb\nc\nd\ne", 3)
	if lines := strings.Split(out, "\n"); len(lines) != 3 || !strings.Contains(stripAnsi(lines[2]), "mais robôs") {
		t.Fatalf("clipLines inesperado: %q", out)
	}
}

func TestCartaoMostraValidadaOuExperimental(t *testing.T) {
	quant := NewPythonWorker("HK50", "H4")
	quant.ColorHex = string(ColorBlue)
	quant.SetTelemetry(Telemetry{Validated: true, LiveAllowed: true, Quant: &QuantInfo{Setup: "PULLB"}})
	classic := NewPythonWorker("EURUSD", "H1")
	classic.ColorHex = string(ColorGreen)
	classic.StatusText = "🔒 SÓ SIMULAÇÃO"
	classic.SetTelemetry(Telemetry{Validated: false, LiveAllowed: false})

	out := stripAnsi(robotCards([]*PythonWorker{quant, classic}, 60))
	for _, want := range []string{"★ QUANT PULLB", "experimental · só simulação (/study)", "[LOCK]"} {
		if !strings.Contains(out, want) {
			t.Fatalf("cartoes sem %q:\n%s", want, out)
		}
	}
}

func TestSeloContaRealNaoConfirmada(t *testing.T) {
	if got := statusBadge("🔒 CONFIRME A CONTA REAL (bot.bat setup)").Label; got != "LOCK" {
		t.Fatalf("conta REAL nao confirmada deveria ser LOCK, veio %q", got)
	}
}
