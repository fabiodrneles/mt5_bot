package main

import (
	"strings"
	"testing"

	"github.com/charmbracelet/bubbles/viewport"
	"github.com/charmbracelet/lipgloss"
)

func TestRenderPerformanceLucroVerdePrejuizoVermelho(t *testing.T) {
	pos := renderPerformance(Summary{PnL: 158.40, WinRate: 42.0, Trades: 12, HasData: true})
	if !strings.Contains(stripAnsi(pos), "+$158.40") || !strings.Contains(stripAnsi(pos), "42.0%") || !strings.Contains(stripAnsi(pos), "Trades: 12") {
		t.Fatalf("resumo positivo inválido: %q", pos)
	}
	refGreen := lipgloss.NewStyle().Foreground(ColorGreen).Bold(true).Render("+$158.40")
	if !strings.Contains(pos, refGreen) {
		t.Fatalf("PnL positivo deveria usar ColorGreen: %q", pos)
	}

	neg := renderPerformance(Summary{PnL: -158.40, WinRate: 42.0, Trades: 12, HasData: true})
	if !strings.Contains(stripAnsi(neg), "-$158.40") {
		t.Fatalf("resumo negativo inválido: %q", neg)
	}
	refRed := lipgloss.NewStyle().Foreground(ColorRed).Bold(true).Render("-$158.40")
	if !strings.Contains(neg, refRed) {
		t.Fatalf("PnL negativo deveria usar ColorRed: %q", neg)
	}
}

func TestRenderPerformanceSemDados(t *testing.T) {
	out := renderPerformance(Summary{})
	if !strings.Contains(stripAnsi(out), "Sem dados") {
		t.Fatalf("sem dados deveria mostrar convite à ação: %q", out)
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