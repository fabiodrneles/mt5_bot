package main

import (
	"testing"
	"time"
)

func TestParseCommandAdd(t *testing.T) {
	cases := []struct {
		name  string
		line  string
		symbol string
		tf    string
	}{
		{"com timeframe", "/add WIN M5", "WIN", "M5"},
		{"sem timeframe usa H1", "/add WIN", "WIN", "H1"},
		{"simbolo em minusculo", "/add win m15", "WIN", "M15"},
		{"espacos extras", "  /add   hk50   H4  ", "HK50", "H4"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			cmd := parseCommand(tc.line)
			if cmd.Name != "add" {
				t.Fatalf("Name=%q, esperado add", cmd.Name)
			}
			if cmd.Symbol != tc.symbol {
				t.Fatalf("Symbol=%q, esperado %q", cmd.Symbol, tc.symbol)
			}
			if cmd.Timeframe != tc.tf {
				t.Fatalf("Timeframe=%q, esperado %q", cmd.Timeframe, tc.tf)
			}
		})
	}
}

func TestParseCommandStop(t *testing.T) {
	cases := []struct {
		name  string
		line  string
		symbol string
	}{
		{"stop", "/stop WIN", "WIN"},
		{"remove alias", "/remove hk50", "HK50"},
		{"sem simbolo", "/stop", ""},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			cmd := parseCommand(tc.line)
			if cmd.Name != "stop" {
				t.Fatalf("Name=%q, esperado stop", cmd.Name)
			}
			if cmd.Symbol != tc.symbol {
				t.Fatalf("Symbol=%q, esperado %q", cmd.Symbol, tc.symbol)
			}
		})
	}
}

func TestParseCommandList(t *testing.T) {
	cmd := parseCommand("/list")
	if cmd.Name != "list" {
		t.Fatalf("Name=%q, esperado list", cmd.Name)
	}
}

func TestParseCommandQuitActions(t *testing.T) {
	cases := []struct {
		line   string
		action string
	}{
		{"/quit", ""},
		{"/quit cancel-open", "cancel-open"},
		{"/quit wait-flat", "wait-flat"},
		{"/quit close-all", "close-all"},
		{"/quit  WAIT-FLAT  ", "wait-flat"},
	}
	for _, tc := range cases {
		cmd := parseCommand(tc.line)
		if cmd.Name != "quit" {
			t.Fatalf("%q: Name=%q, esperado quit", tc.line, cmd.Name)
		}
		if cmd.Action != tc.action {
			t.Fatalf("%q: Action=%q, esperado %q", tc.line, cmd.Action, tc.action)
		}
	}
}

func TestParseCommandExitAlias(t *testing.T) {
	for _, line := range []string{"/exit", "exit"} {
		if cmd := parseCommand(line); cmd.Name != "quit" {
			t.Fatalf("%q: Name=%q, esperado quit", line, cmd.Name)
		}
	}
}

func TestParseCommandVazioIgnorado(t *testing.T) {
	for _, line := range []string{"", "   ", "\t"} {
		if cmd := parseCommand(line); cmd.Name != "" {
			t.Fatalf("linha vazia deveria retornar Name=\"\", obteve %q", cmd.Name)
		}
	}
}

func TestParseCommandDesconhecido(t *testing.T) {
	if cmd := parseCommand("/nada"); cmd.Name != "unknown" {
		t.Fatalf("Name=%q, esperado unknown", cmd.Name)
	}
}

func TestRecordFailureLimiteDeTres(t *testing.T) {
	w := &PythonWorker{Symbol: "WIN"}
	base := time.Now()
	// 3 falhas dentro de 2 minutos
	if w.recordFailure(base) {
		t.Fatal("1a falha nao deveria disparar crash loop")
	}
	if w.recordFailure(base.Add(30 * time.Second)) {
		t.Fatal("2a falha nao deveria disparar crash loop")
	}
	if !w.recordFailure(base.Add(60 * time.Second)) {
		t.Fatal("3a falha dentro da janela deveria disparar crash loop")
	}
	if !w.disabled {
		t.Fatal("worker deveria estar desligado apos crash loop")
	}
}

func TestRecordFailureJanelaExpiradaReinicia(t *testing.T) {
	w := &PythonWorker{Symbol: "HK50"}
	base := time.Now()
	w.recordFailure(base)
	// 2a falha apos mais de 2 minutos: conta como nova janela, nao dispara
	if w.recordFailure(base.Add(3 * time.Minute)) {
		t.Fatal("falha apos janela expirada deveria reiniciar contagem, nao disparar")
	}
	if w.crashCount != 1 {
		t.Fatalf("crashCount=%d, esperado 1 (janela reiniciada a partir da 2a falha)", w.crashCount)
	}
}

func TestRecordFailureDisablePersistente(t *testing.T) {
	w := &PythonWorker{Symbol: "WIN"}
	base := time.Now()
	for i := 0; i < 3; i++ {
		w.recordFailure(base.Add(time.Duration(i) * time.Second))
	}
	if !w.disabled {
		t.Fatal("apos 3 falhas rapidas, worker deveria estar disabled")
	}
	// mesmo se mais falhas chegarem, permanece desligado (short-circuit true)
	if !w.recordFailure(base.Add(5 * time.Second)) {
		t.Fatal("falha adicional apos disable deveria permanecer sinalizando crash loop")
	}
	if !w.disabled {
		t.Fatal("disabled deveria persistir")
	}
}