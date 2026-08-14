package main

import (
	"strings"
	"testing"
)

func TestStatusBadge(t *testing.T) {
	cases := []struct {
		state string
		want  string
	}{
		{"🔵 SCANNING", "SCAN"},
		{"🔵 STUDY_SCANNING", "SCAN"},
		{"🔴 WAIT_DATA", "SCAN"},
		{"🟡 PENDING (BUY)", "WAIT"},
		{"🟢 EXTERNAL_POS", "WAIT"},
		{"🟢 IN_POSITION (9.1 BUY)", "POS"},
		{"🟣 PAPER_TRADE (9.2 SELL)", "POS"},
		{"ERRO: Ativo inválido", "ERRO"},
		{"", "INIT"},
	}
	for _, tc := range cases {
		if got := statusBadge(tc.state).Label; got != tc.want {
			t.Fatalf("statusBadge(%q).Label=%q, esperado %q", tc.state, got, tc.want)
		}
	}
}

func TestRenderBadgeLarguraFixaAlinhadaDireita(t *testing.T) {
	out := stripAnsi(renderBadge(StatusBadge{Label: "POS", Color: ColorGreen}, 6))
	if !strings.HasPrefix(out, " ") {
		t.Fatalf("badge curto deveria ter padding à esquerda: %q", out)
	}
	outWide := stripAnsi(renderBadge(StatusBadge{Label: "ERRO", Color: ColorRed}, 6))
	if len(outWide) != len(out) {
		t.Fatalf("badges de larguras diferentes (%d vs %d) — largura fixa quebrada", len(outWide), len(out))
	}
}

func TestDetectMode(t *testing.T) {
	if got := detectMode(nil); got != "LIVE" {
		t.Fatalf("sem workers → %q, esperado LIVE", got)
	}
	real := &PythonWorker{Symbol: "WIN"}
	if got := detectMode([]*PythonWorker{real}); got != "LIVE" {
		t.Fatalf("só add → %q, esperado LIVE", got)
	}
	study := &PythonWorker{Symbol: "HK50", IsStudyMode: true}
	if got := detectMode([]*PythonWorker{real, study}); got != "SIMULATOR" {
		t.Fatalf("com study → %q, esperado SIMULATOR", got)
	}
}

func TestDetectMT5(t *testing.T) {
	if got := detectMT5(nil); got != "OFF" {
		t.Fatalf("sem workers → %q, esperado OFF", got)
	}
	ok := &PythonWorker{Symbol: "WIN", StatusText: "🔵 SCANNING"}
	if got := detectMT5([]*PythonWorker{ok}); got != "ON" {
		t.Fatalf("worker saudável → %q, esperado ON", got)
	}
	bad := &PythonWorker{Symbol: "WIN", StatusText: "ERRO: MT5 falhou"}
	if got := detectMT5([]*PythonWorker{bad}); got != "OFF" {
		t.Fatalf("worker com erro → %q, esperado OFF", got)
	}
}