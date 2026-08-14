package main

import (
	"encoding/json"
	"os"
	"path/filepath"
)

// Trade espelha o JSON gravado pelo tracker Python (mt5bot/data/tracker.py e paper_tracker.py).
type Trade struct {
	Result   string   `json:"result"`
	PnLMoney *float64 `json:"pnl_money"`
}

// Summary é o resumo de performance dos trades fechados.
type Summary struct {
	PnL     float64
	WinRate float64 // 0-100
	Trades  int
	HasData bool
}

// tradesFilePath retorna o caminho do arquivo de trades.
// virtual=true → paper/simulador (virtual_trades.json); false → real (trades.json).
func tradesFilePath(virtual bool) string {
	appdata := os.Getenv("APPDATA")
	if appdata == "" {
		appdata = os.Getenv("LOCALAPPDATA")
	}
	name := "trades.json"
	if virtual {
		name = "virtual_trades.json"
	}
	if appdata != "" {
		return filepath.Join(appdata, "mt5bot", name)
	}
	home, err := os.UserHomeDir()
	if err != nil {
		home = "."
	}
	return filepath.Join(home, ".mt5bot", name)
}

func readTradesFile(path string) ([]Trade, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var trades []Trade
	if err := json.Unmarshal(data, &trades); err != nil {
		return nil, err
	}
	return trades, nil
}

// computeSummary considera apenas trades fechados (result "win"/"loss").
func computeSummary(trades []Trade) Summary {
	var s Summary
	wins, losses := 0, 0
	for _, t := range trades {
		if t.Result != "win" && t.Result != "loss" {
			continue
		}
		if t.PnLMoney != nil {
			s.PnL += *t.PnLMoney
		}
		if t.Result == "win" {
			wins++
		} else {
			losses++
		}
	}
	s.Trades = wins + losses
	s.HasData = s.Trades > 0
	if s.HasData {
		s.WinRate = float64(wins) / float64(s.Trades) * 100
	}
	return s
}