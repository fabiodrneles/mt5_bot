package main

import (
	"math"
	"os"
	"path/filepath"
	"testing"
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