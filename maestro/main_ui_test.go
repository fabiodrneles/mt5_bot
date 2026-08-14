package main

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/charmbracelet/bubbles/viewport"
	"github.com/charmbracelet/lipgloss"
)

func TestRenderPerformanceLucroVerdePrejuizoVermelho(t *testing.T) {
	pos := renderPerformance(Summary{PnL: 158.40, WinRate: 42.0, Trades: 12, HasData: true}, 60)
	if !strings.Contains(stripAnsi(pos), "+$158.40") || !strings.Contains(stripAnsi(pos), "42.0%") || !strings.Contains(stripAnsi(pos), "Trades: 12") {
		t.Fatalf("resumo positivo inválido: %q", pos)
	}
	refGreen := lipgloss.NewStyle().Foreground(ColorGreen).Bold(true).Render("+$158.40")
	if !strings.Contains(pos, refGreen) {
		t.Fatalf("PnL positivo deveria usar ColorGreen: %q", pos)
	}

	neg := renderPerformance(Summary{PnL: -158.40, WinRate: 42.0, Trades: 12, HasData: true}, 60)
	if !strings.Contains(stripAnsi(neg), "-$158.40") {
		t.Fatalf("resumo negativo inválido: %q", neg)
	}
	refRed := lipgloss.NewStyle().Foreground(ColorRed).Bold(true).Render("-$158.40")
	if !strings.Contains(neg, refRed) {
		t.Fatalf("PnL negativo deveria usar ColorRed: %q", neg)
	}
}

func TestRenderPerformanceSemDados(t *testing.T) {
	out := renderPerformance(Summary{}, 60)
	if !strings.Contains(stripAnsi(out), "Sem dados") {
		t.Fatalf("sem dados deveria mostrar convite à ação: %q", out)
	}
}

func TestRenderPerformanceTruncaParaCaberc(t *testing.T) {
	out := renderPerformance(Summary{PnL: -158.40, WinRate: 42.0, Trades: 12, HasData: true}, 30)
	if n := len([]rune(stripAnsi(out))); n > 30 {
		t.Fatalf("renderPerformance deveria truncar para <=30, veio %d: %q", n, out)
	}
	if !strings.Contains(stripAnsi(out), "…") {
		t.Fatalf("esperava reticências ao truncar: %q", out)
	}
}

func TestRenderWorkerLineComDados(t *testing.T) {
	w := NewPythonWorker("EURUSD", "H1")
	w.ColorHex = string(symbolColors[0])
	line := renderWorkerLine(w, Summary{PnL: 158.40, WinRate: 42.0, Trades: 12, HasData: true}, 60)
	plain := stripAnsi(line)
	for _, want := range []string{"[EURUSD|H1]", "LOTE 0.01", "+$158.40", "42.0%", "12T"} {
		if !strings.Contains(plain, want) {
			t.Fatalf("linha de worker sem %q: %q", want, plain)
		}
	}
	refTag := lipgloss.NewStyle().
		Foreground(lipgloss.Color(w.ColorHex)).
		Bold(true).
		Render("[EURUSD|H1]")
	if !strings.Contains(line, refTag) {
		t.Fatalf("tag do worker deveria usar ColorHex %s: %q", w.ColorHex, line)
	}
	refPnl := lipgloss.NewStyle().Foreground(ColorGreen).Bold(true).Render("+$158.40")
	if !strings.Contains(line, refPnl) {
		t.Fatalf("PnL positivo deveria usar ColorGreen: %q", line)
	}
}

func TestRenderWorkerLinePrejuizoVermelho(t *testing.T) {
	w := NewPythonWorker("HK50", "M5")
	line := renderWorkerLine(w, Summary{PnL: -7551.44, WinRate: 0.0, Trades: 1, HasData: true}, 60)
	refRed := lipgloss.NewStyle().Foreground(ColorRed).Bold(true).Render("-$7551.44")
	if !strings.Contains(line, refRed) {
		t.Fatalf("PnL negativo deveria usar ColorRed: %q", line)
	}
	if !strings.Contains(stripAnsi(line), "LOTE 0.10") {
		t.Fatalf("HK50 deveria exibir LOTE 0.10: %q", stripAnsi(line))
	}
}

func TestRenderWorkerLineSemDados(t *testing.T) {
	w := NewPythonWorker("EURUSD", "H1")
	line := renderWorkerLine(w, Summary{}, 60)
	if !strings.Contains(stripAnsi(line), "sem dados") {
		t.Fatalf("sem dados deveria indicar: %q", line)
	}
}

func TestPerfPanelContentMultiWorker(t *testing.T) {
	dir := t.TempDir()
	t.Setenv("APPDATA", dir)
	t.Setenv("LOCALAPPDATA", "")
	os.MkdirAll(filepath.Join(dir, "mt5bot"), 0o755)
	content := `[
		{"result":"win","pnl_money":22.66,"symbol":"EURUSD","entry_time":"2026-08-14T01:00:00+00:00"},
		{"result":"loss","pnl_money":-7551.44,"symbol":"HK50","entry_time":"2026-08-14T01:00:00+00:00"}
	]`
	if err := os.WriteFile(filepath.Join(dir, "mt5bot", "virtual_trades.json"), []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}

	e := NewPythonWorker("EURUSD", "H1")
	e.IsStudyMode = true
	e.StartTime = time.Date(2026, 8, 14, 0, 0, 0, 0, time.UTC)
	h := NewPythonWorker("HK50", "M5")
	h.IsStudyMode = true
	h.StartTime = time.Date(2026, 8, 14, 0, 0, 0, 0, time.UTC)

	panel := perfPanelContent([]*PythonWorker{e, h}, "SIMULATOR", 60)
	lines := strings.Split(stripAnsi(panel), "\n")
	if len(lines) != 2 {
		t.Fatalf("painel deveria ter 2 linhas, veio %d: %q", len(lines), panel)
	}
	if !strings.Contains(lines[0], "EURUSD") || !strings.Contains(lines[0], "+$22.66") {
		t.Fatalf("linha EURUSD inválida: %q", lines[0])
	}
	if !strings.Contains(lines[1], "HK50") || !strings.Contains(lines[1], "-$7551.44") {
		t.Fatalf("linha HK50 inválida: %q", lines[1])
	}
}

func TestViewPerfTituloPorAtivoESessao(t *testing.T) {
	m := initialModel()
	m.ready = true
	m.width, m.height = 120, 40
	m.viewport = viewport.New(60, 10)
	if err := m.manager.Add(NewPythonWorker("EURUSD", "H1")); err != nil {
		t.Fatal(err)
	}
	m.mode = "LIVE"
	m.updateStatus()
	if !strings.Contains(m.View(), "PERFORMANCE RESUMO (Por Ativo)") {
		t.Fatalf("LIVE deveria usar título 'Por Ativo':\n%s", m.View())
	}

	study := NewPythonWorker("EURUSD", "M5")
	study.IsStudyMode = true
	if err := m.manager.Add(study); err != nil {
		t.Fatal(err)
	}
	m.updateStatus()
	if !strings.Contains(m.View(), "PERFORMANCE RESUMO (Sessão Atual)") {
		t.Fatalf("SIMULATOR deveria usar título 'Sessão Atual':\n%s", m.View())
	}
}

func TestViewRenderizaPainéis(t *testing.T) {
	m := initialModel()
	m.ready = true
	m.width, m.height = 120, 40
	m.viewport = viewport.New(60, 10)
	if err := m.manager.Add(NewPythonWorker("EURUSD", "H1")); err != nil {
		t.Fatal(err)
	}
	m.mode = "LIVE"
	m.mt5Status = "ON"
	m.updateStatus()

	out := m.View()
	for _, want := range []string{
		"MAESTRO v" + botVersion(),
		"[ MODE: LIVE ]",
		"[ MT5: ON ]",
		"ATIVOS EM EXECUÇÃO",
		"EVENT LOG",
		"PERFORMANCE RESUMO",
	} {
		if !strings.Contains(out, want) {
			t.Fatalf("View sem %q:\n%s", want, out)
		}
	}
}

func TestParseProjectVersion(t *testing.T) {
	content := "name = \"mt5bot\"\nversion = \"2.3.2\"\n[tool.something]\n"
	if got := parseProjectVersion(content); got != "2.3.2" {
		t.Fatalf("parseProjectVersion=%q, esperado 2.3.2", got)
	}
	if got := parseProjectVersion("sem versao aqui"); got != "" {
		t.Fatalf("sem version deveria retornar vazio, veio %q", got)
	}
}

func TestBotVersionNuncaVazia(t *testing.T) {
	if v := botVersion(); v == "" {
		t.Fatal("botVersion deveria ter fallback")
	}
}

func TestViewSimulador(t *testing.T) {
	m := initialModel()
	m.ready = true
	m.width, m.height = 120, 40
	m.viewport = viewport.New(60, 10)
	study := NewPythonWorker("HK50", "H1")
	study.IsStudyMode = true
	if err := m.manager.Add(study); err != nil {
		t.Fatal(err)
	}
	m.updateStatus()

	out := m.View()
	if !strings.Contains(out, "[ MODE: SIMULATOR ]") {
		t.Fatalf("View sem badge SIMULATOR:\n%s", out)
	}
	if !strings.Contains(out, "EVENT LOG (Simulador)") {
		t.Fatalf("View sem título Simulador:\n%s", out)
	}
}

// buildState replica o fluxo real de render com resize + worker + log longo.
func buildState(width, height int) model {
	m := initialModel()
	m.width, m.height = width, height
	m.ready = true
	m.viewport = viewport.New(width, height)
	study := NewPythonWorker("HK50", "M5")
	study.IsStudyMode = true
	_ = m.manager.Add(study)
	m.updateStatus()
	m.logs = []string{"LINHA NORMAL DE LOG", strings.Repeat("X", 200)}
	m.viewport.SetContent(wrapLogs(m.logs, m.viewport.Width))
	m.viewport.GotoBottom()
	return m
}

// Regressão do bug de layout: lipgloss v1.1.0 soma a borda ao Width/Height,
// então o grid renderizava m.width+1 colunas e m.height+2 linhas — borda e
// cantos direitos cortados no terminal.
func TestLayoutNaoEstouraTerminal(t *testing.T) {
	for _, tc := range []struct{ w, h int }{{120, 30}, {100, 25}, {80, 24}, {150, 40}, {60, 20}} {
		m := buildState(tc.w, tc.h)
		out := stripAnsi(m.View())
		lines := strings.Split(out, "\n")
		overflow := false
		for i, line := range lines {
			if len([]rune(line)) > tc.w {
				t.Logf("[%dx%d] linha %d: %d cols > %d", tc.w, tc.h, i, len([]rune(line)), tc.w)
				overflow = true
			}
		}
		if overflow {
			t.Errorf("overflow horizontal em %dx%d", tc.w, tc.h)
		}
		if len(lines) > tc.h {
			t.Errorf("[%dx%d] View com %d linhas > altura %d (corte vertical)", tc.w, tc.h, len(lines), tc.h)
		}
	}
}

func TestLayoutAdaptaAoResize(t *testing.T) {
	m := buildState(120, 30)
	before := stripAnsi(m.View())
	m.width, m.height = 80, 24
	m.updateStatus()
	m.viewport.SetContent(wrapLogs(m.logs, m.viewport.Width))
	after := stripAnsi(m.View())
	if before == after {
		t.Fatal("resize não alterou a View")
	}
	for _, line := range strings.Split(after, "\n") {
		if len([]rune(line)) > 80 {
			t.Fatalf("após resize 80x24, linha com %d cols", len([]rune(line)))
		}
	}
}