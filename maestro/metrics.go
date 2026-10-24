package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"sync"
	"time"
)

// tradesCache evita reler/parsear o JSON de trades a cada segundo por robo:
// so rele quando o arquivo muda (mtime ou tamanho).
var tradesCache = struct {
	sync.Mutex
	entries map[string]cachedTrades
}{entries: map[string]cachedTrades{}}

type cachedTrades struct {
	mod    time.Time
	size   int64
	trades []Trade
}

// Trade espelha o JSON gravado pelo tracker Python (mt5bot/data/tracker.py e paper_tracker.py).
type Trade struct {
	Result    string   `json:"result"`
	PnLMoney  *float64 `json:"pnl_money"`
	Symbol    string   `json:"symbol"`
	Setup     string   `json:"setup"`
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
	info, err := os.Stat(path)
	if err != nil {
		return nil, err
	}
	tradesCache.Lock()
	defer tradesCache.Unlock()
	if c, ok := tradesCache.entries[path]; ok && c.mod.Equal(info.ModTime()) && c.size == info.Size() {
		return c.trades, nil
	}
	trades, err := parseTradesFile(path)
	if err == nil {
		tradesCache.entries[path] = cachedTrades{mod: info.ModTime(), size: info.Size(), trades: trades}
	}
	return trades, err
}

func parseTradesFile(path string) ([]Trade, error) {
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
// HK50 agora retorna 0.01 porque o Python risk_calculator é quem gerencia lotes maiores.
func assetMinLot(symbol string) float64 {
	switch symbol {
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