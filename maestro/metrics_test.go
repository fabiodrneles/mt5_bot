package main

import (
	"math"
	"os"
	"path/filepath"
	"testing"
	"time"
)

func f(v float64) *float64 { return &v }

func TestTradesFilePath(t *testing.T) {
	dir := t.TempDir()
	t.Setenv("APPDATA", dir)
	t.Setenv("LOCALAPPDATA", "")

	if got := tradesFilePath(false); got != filepath.Join(dir, "mt5bot", "trades.json") {
		t.Fatalf("tradesFilePath(false)=%q", got)
	}
	if got := tradesFilePath(true); got != filepath.Join(dir, "mt5bot", "virtual_trades.json") {
		t.Fatalf("tradesFilePath(true)=%q", got)
	}
}

func TestReadTradesFile(t *testing.T) {
	path := filepath.Join(t.TempDir(), "trades.json")
	content := `[{"result":"win","pnl_money":22.66},{"result":"loss","pnl_money":-20.92},{"result":"open"}]`
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
	trades, err := readTradesFile(path)
	if err != nil {
		t.Fatalf("readTradesFile erro: %v", err)
	}
	if len(trades) != 3 {
		t.Fatalf("len=%d, esperado 3", len(trades))
	}
	if trades[0].Result != "win" || *trades[0].PnLMoney != 22.66 {
		t.Fatalf("trade[0]=%+v", trades[0])
	}
	if trades[2].PnLMoney != nil {
		t.Fatal("trade 'open' deveria ter PnLMoney nil")
	}
}

func TestReadTradesFileInexistente(t *testing.T) {
	_, err := readTradesFile(filepath.Join(t.TempDir(), "nope.json"))
	if err == nil {
		t.Fatal("arquivo inexistente deveria retornar erro")
	}
}

func TestComputeSummary(t *testing.T) {
	trades := []Trade{
		{Result: "win", PnLMoney: f(22.66)},
		{Result: "win", PnLMoney: f(5.0)},
		{Result: "loss", PnLMoney: f(-20.92)},
		{Result: "loss", PnLMoney: f(-10.0)},
		{Result: "open", PnLMoney: nil}, // aberto não conta
	}
	s := computeSummary(trades)
	if !s.HasData {
		t.Fatal("HasData deveria ser true")
	}
	if s.Trades != 4 {
		t.Fatalf("Trades=%d, esperado 4", s.Trades)
	}
	if math.Abs(s.PnL-(-3.26)) > 1e-9 {
		t.Fatalf("PnL=%.4f, esperado -3.26", s.PnL)
	}
	if s.WinRate != 50.0 {
		t.Fatalf("WinRate=%.2f, esperado 50.0", s.WinRate)
	}
}

func TestComputeSummaryVazio(t *testing.T) {
	s := computeSummary(nil)
	if s.HasData {
		t.Fatal("sem trades fechados HasData deveria ser false")
	}
	if s.Trades != 0 || s.PnL != 0 {
		t.Fatalf("summary vazio=%+v", s)
	}
}

func TestSummarizeTradesFiltroPorSimbolo(t *testing.T) {
	trades := []Trade{
		{Result: "win", PnLMoney: f(22.66), Symbol: "EURUSD"},
		{Result: "loss", PnLMoney: f(-20.92), Symbol: "EURUSD"},
		{Result: "win", PnLMoney: f(5.0), Symbol: "HK50"},
		{Result: "open", PnLMoney: nil, Symbol: "EURUSD"}, // aberto não conta
	}
	s := summarizeTrades(trades, "EURUSD", time.Time{}, false)
	if s.Trades != 2 {
		t.Fatalf("EURUSD Trades=%d, esperado 2", s.Trades)
	}
	if math.Abs(s.PnL-1.74) > 1e-9 {
		t.Fatalf("EURUSD PnL=%.4f, esperado 1.74", s.PnL)
	}
	h := summarizeTrades(trades, "HK50", time.Time{}, false)
	if h.Trades != 1 || h.WinRate != 100.0 {
		t.Fatalf("HK50 summary=%+v", h)
	}
}

func TestSummarizeTradesSessaoAtual(t *testing.T) {
	// entry_time sem fuso → assume UTC; com fuso → RFC3339Nano.
	trades := []Trade{
		{Result: "win", PnLMoney: f(22.66), Symbol: "EURUSD", EntryTime: "2026-08-10T02:08:03.863263"},
		{Result: "win", PnLMoney: f(5.0), Symbol: "EURUSD", EntryTime: "2026-08-14T01:29:56.476321+00:00"},
	}
	since := time.Date(2026, 8, 12, 0, 0, 0, 0, time.UTC)
	s := summarizeTrades(trades, "EURUSD", since, true)
	if s.Trades != 1 {
		t.Fatalf("sessão Trades=%d, esperado 1 (só o posterior ao since)", s.Trades)
	}
	if math.Abs(s.PnL-5.0) > 1e-9 {
		t.Fatalf("sessão PnL=%.4f, esperado 5.0", s.PnL)
	}
}

func TestAssetMinLot(t *testing.T) {
	cases := []struct{ symbol string; want float64 }{
		{"HK50", 0.01},
		{"HKG50", 0.01},
		{"EURUSD", 0.01},
		{"USDJPY", 0.01},
		{"", 0.01},
	}
	for _, c := range cases {
		if got := assetMinLot(c.symbol); got != c.want {
			t.Fatalf("assetMinLot(%q)=%.2f, esperado %.2f", c.symbol, got, c.want)
		}
	}
}

func TestParseEntryTime(t *testing.T) {
	cases := []struct {
		in   string
		want time.Time
		ok   bool
	}{
		{"2026-08-10T02:08:03.863263", time.Date(2026, 8, 10, 2, 8, 3, 863263000, time.UTC), true},
		{"2026-08-14T01:29:56.476321+00:00", time.Date(2026, 8, 14, 1, 29, 56, 476321000, time.UTC), true},
		{"2026-08-14T01:29:56", time.Date(2026, 8, 14, 1, 29, 56, 0, time.UTC), true},
		{"nada", time.Time{}, false},
		{"", time.Time{}, false},
	}
	for _, c := range cases {
		got, ok := parseEntryTime(c.in)
		if ok != c.ok {
			t.Fatalf("parseEntryTime(%q) ok=%v, esperado %v", c.in, ok, c.ok)
		}
		if ok && !got.Equal(c.want) {
			t.Fatalf("parseEntryTime(%q)=%v, esperado %v", c.in, got, c.want)
		}
	}
}

func TestWorkerSummaryFiltraSimbolo(t *testing.T) {
	dir := t.TempDir()
	t.Setenv("APPDATA", dir)
	t.Setenv("LOCALAPPDATA", "")
	os.MkdirAll(filepath.Join(dir, "mt5bot"), 0o755)
	content := `[
		{"result":"win","pnl_money":22.66,"symbol":"EURUSD","entry_time":"2026-08-10T02:08:03.863263"},
		{"result":"loss","pnl_money":-20.92,"symbol":"EURUSD","entry_time":"2026-08-10T03:08:03.863263"},
		{"result":"loss","pnl_money":-7551.44,"symbol":"HK50","entry_time":"2026-08-10T04:08:03.863263"}
	]`
	if err := os.WriteFile(filepath.Join(dir, "mt5bot", "trades.json"), []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
	w := NewPythonWorker("EURUSD", "H1")
	s := workerSummary(w, "LIVE")
	if s.Trades != 2 {
		t.Fatalf("LIVE EURUSD Trades=%d, esperado 2 (sem filtro de sessão)", s.Trades)
	}
	if math.Abs(s.PnL-1.74) > 1e-9 {
		t.Fatalf("LIVE EURUSD PnL=%.4f, esperado 1.74", s.PnL)
	}
}

func TestWorkerSummarySessaoAtual(t *testing.T) {
	dir := t.TempDir()
	t.Setenv("APPDATA", dir)
	t.Setenv("LOCALAPPDATA", "")
	os.MkdirAll(filepath.Join(dir, "mt5bot"), 0o755)
	content := `[
		{"result":"win","pnl_money":22.66,"symbol":"EURUSD","entry_time":"2026-08-10T02:08:03.863263"},
		{"result":"loss","pnl_money":-20.92,"symbol":"EURUSD","entry_time":"2026-08-14T01:29:56.476321+00:00"},
		{"result":"loss","pnl_money":-7551.44,"symbol":"HK50","entry_time":"2026-08-14T01:29:56.476321+00:00"}
	]`
	if err := os.WriteFile(filepath.Join(dir, "mt5bot", "virtual_trades.json"), []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
	w := NewPythonWorker("EURUSD", "H1")
	w.IsStudyMode = true
	w.StartTime = time.Date(2026, 8, 14, 1, 0, 0, 0, time.UTC)
	s := workerSummary(w, "SIMULATOR")
	if s.Trades != 1 {
		t.Fatalf("SIMULATOR EURUSD Trades=%d, esperado 1 (só sessão atual)", s.Trades)
	}
	if s.PnL != -20.92 {
		t.Fatalf("SIMULATOR EURUSD PnL=%.4f, esperado -20.92", s.PnL)
	}
}