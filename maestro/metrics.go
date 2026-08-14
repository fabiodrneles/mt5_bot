package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"time"
)

// Trade espelha o JSON gravado pelo tracker Python (mt5bot/data/tracker.py e paper_tracker.py).
type Trade struct {
	Result    string   `json:"result"`
	PnLMoney  *float64 `json:"pnl_money"`
	Symbol    string   `json:"symbol"`
	EntryTime string   `json:"entry_time"`
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
	return summarizeTrades(trades, "", time.Time{}, false)
}

// summarizeTrades agrega trades fechados com filtros opcionais:
//   - symbol != ""  → só trades daquele ativo
//   - since != zero → só trades com entry_time >= since (sessão atual)
//   - useSince      → habilita o filtro temporal (exige entry_time parseável)
func summarizeTrades(trades []Trade, symbol string, since time.Time, useSince bool) Summary {
	var s Summary
	wins, losses := 0, 0
	for _, t := range trades {
		if t.Result != "win" && t.Result != "loss" {
			continue
		}
		if symbol != "" && t.Symbol != symbol {
			continue
		}
		if useSince {
			et, ok := parseEntryTime(t.EntryTime)
			if !ok || et.Before(since) {
				continue
			}
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

// workerSummary agrega as métricas de um worker: filtra pelo símbolo e, no
// modo SIMULATOR, apenas pela sessão atual (entry_time >= StartTime). Isso
// evita exibir todo o histórico acumulado do virtual_trades.json.
func workerSummary(w *PythonWorker, mode string) Summary {
	virtual := mode == "SIMULATOR"
	trades, err := readTradesFile(tradesFilePath(virtual))
	if err != nil {
		return Summary{}
	}
	useSince := virtual && !w.StartTime.IsZero()
	return summarizeTrades(trades, w.Symbol, w.StartTime, useSince)
}

// assetMinLot espelha config.ASSET_MIN_LOTS para exibição do lote por ativo:
// HK50/HKG50 operam com 0.10; os demais com 0.01.
func assetMinLot(symbol string) float64 {
	switch symbol {
	case "HK50", "HKG50":
		return 0.10
	default:
		return 0.01
	}
}

// parseEntryTime aceita RFC3339Nano ("...+00:00") e o formato sem fuso
// gravado pelo tracker ("2006-01-02T15:04:05.999999"). Sem fuso assume UTC.
func parseEntryTime(s string) (time.Time, bool) {
	layouts := []string{
		time.RFC3339Nano,
		"2006-01-02T15:04:05.999999",
		"2006-01-02T15:04:05",
	}
	for _, l := range layouts {
		if t, err := time.Parse(l, s); err == nil {
			return t, true
		}
	}
	return time.Time{}, false
}