# Maestro TUI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesenhar a interface Bubble Tea do maestro (grid 4 regiões, paleta Tokyo Night + âmbar, badges de status, painel de performance modo-consciente) sem tocar na lógica de trading.

**Architecture:** Todos os hex saem para `style.go` (design tokens). Dados de performance lidos em Go direto dos JSONs do tracker (`trades.json` real / `virtual_trades.json` simulador). `badges.go` isola o mapeamento `state_text` → badge e a detecção de modo/MT5. `worker.go` só muda formatação visual de log + paleta. `main.go` reorganiza layout.

**Tech Stack:** Go 1.25, Bubble Tea v1.3.10, Bubbles v1.0.0, Lipgloss v1.1.0, stdlib (`encoding/json`, `os`, `path/filepath`, `math`, `strings`).

## Global Constraints

- Módulo `maestro`, Go `1.25.3`. Comandos sempre em `C:\Users\Gamer\mt5_bot-main\maestro\`: `go build ./...`, `go vet ./...`, `go test ./...`.
- **Nenhuma** dependência Go nova (apenas stdlib + charmbracelet já presentes em `go.mod`).
- **Nenhuma** alteração em arquivos Python (`mt5bot/`, `interfaces/`) nem na lógica de trading.
- Versão exibida no título: `MAESTRO v2.4` (constante de UI, independente do `--version`).
- Convenção de caminho de dados: `%APPDATA%/mt5bot/trades.json` e `%APPDATA%/mt5bot/virtual_trades.json` (mesma de `lang.go`).
- Fase pré-requisito: `go test ./...` hoje FALHA por `go vet` (worker.go:219 `log.Printf` com string não-constante). Task 1 corrige e estabelece baseline verde.
- Commits: usar mensagens `feat(maestro): ...` seguindo o histórico do repo (ex. `chore:`, `fix(engine):`).

---

### Task 1: Corrigir `go vet` e estabelecer baseline verde

**Files:**
- Modify: `maestro/worker.go:219`
- Test: (nenhum novo — verificação via vet + suite existente)

**Interfaces:**
- Consumes: nada.
- Produces: baseline `go test ./...` e `go vet ./...` passando; pré-requisito para todas as tasks seguintes.

- [ ] **Step 1: Confirmar a falha atual**

Run: `go vet ./...`
Expected: FAIL — `.\worker.go:219:16: non-constant format string in call to log.Printf`

- [ ] **Step 2: Aplicar correção**

```go
// worker.go, dentro da goroutine que lê stderr (linha ~219)
// ANTES:
formattedLine := prefixStyle.Render(fmt.Sprintf("[%s|%s] %s", w.Symbol, w.Timeframe, text))
log.Printf(formattedLine)
// DEPOIS:
formattedLine := prefixStyle.Render(fmt.Sprintf("[%s|%s] %s", w.Symbol, w.Timeframe, text))
log.Print(formattedLine)
```

- [ ] **Step 3: Verificar baseline verde**

Run: `go vet ./...; go test ./...`
Expected: vet limpo; todos os testes existentes PASS (TestParseCommand*, TestNormalizeLang, TestRecordFailure*, etc.)

- [ ] **Step 4: Commit**

```bash
git add maestro/worker.go
git commit -m "fix(maestro): use log.Print for dynamic format string (vet)"
```

---

### Task 2: `style.go` — design tokens centralizados

**Files:**
- Create: `maestro/style.go`
- Test: `maestro/style_test.go`

**Interfaces:**
- Consumes: nada.
- Produces: variáveis `ColorBg`, `ColorBorder`, `ColorText`, `ColorDim`, `ColorAmber`, `ColorGreen`, `ColorRed`, `ColorBlue`, `ColorPurple`, `ColorCyan` (tipo `lipgloss.Color`) e slice `symbolColors []lipgloss.Color`. Todas as tasks seguintes usam estes nomes — não repetem hex.

- [ ] **Step 1: Escrever o teste que falha**

```go
// style_test.go
package main

import "testing"

func TestColorTokensDefinidos(t *testing.T) {
	tokens := []lipgloss.Color{ColorBg, ColorBorder, ColorText, ColorDim, ColorAmber, ColorGreen, ColorRed, ColorBlue, ColorPurple, ColorCyan}
	for _, c := range tokens {
		if c == "" {
			t.Fatalf("token de cor vazio: %q", c)
		}
	}
}

func TestSymbolColorsSeisUnicos(t *testing.T) {
	if len(symbolColors) != 6 {
		t.Fatalf("symbolColors deve ter 6 cores, tem %d", len(symbolColors))
	}
	seen := map[lipgloss.Color]bool{}
	for _, c := range symbolColors {
		if seen[c] {
			t.Fatalf("cor duplicada na paleta de símbolos: %q", c)
		}
		seen[c] = true
	}
}
```

(Adicionar import `"github.com/charmbracelet/lipgloss"` no topo do teste.)

- [ ] **Step 2: Rodar para confirmar que falha**

Run: `go test ./... -run TestColorTokensDefinidos -v`
Expected: FAIL — `undefined: ColorBg`

- [ ] **Step 3: Implementar `style.go`**

```go
// style.go
package main

import "github.com/charmbracelet/lipgloss"

// Design tokens — paleta Tokyo Night + âmbar (spec 2026-08-14).
var (
	ColorBg     = lipgloss.Color("#1A1B26")
	ColorBorder = lipgloss.Color("#414868")
	ColorText   = lipgloss.Color("#C0CAF5")
	ColorDim    = lipgloss.Color("#8A91B0")
	ColorAmber  = lipgloss.Color("#E0AF68")
	ColorGreen  = lipgloss.Color("#9ECE6A")
	ColorRed    = lipgloss.Color("#F7768E")
	ColorBlue   = lipgloss.Color("#7AA2F7")
	ColorPurple = lipgloss.Color("#BB9AF7")
	ColorCyan   = lipgloss.Color("#7DCFFF")
)

// symbolColors é a paleta curada por símbolo (assinatura da UI).
// Atribuição determinística por ordem de criação do worker.
var symbolColors = []lipgloss.Color{
	ColorBlue, ColorGreen, ColorAmber, ColorRed, ColorPurple, ColorCyan,
}
```

- [ ] **Step 4: Rodar para confirmar que passa**

Run: `go test ./... -run "TestColorTokensDefinidos|TestSymbolColorsSeisUnicos" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add maestro/style.go maestro/style_test.go
git commit -m "feat(maestro): centralize design tokens in style.go"
```

---

### Task 3: `metrics.go` — leitura de trades e summary

**Files:**
- Create: `maestro/metrics.go`
- Test: `maestro/metrics_test.go`

**Interfaces:**
- Consumes: nada.
- Produces:
  - `type Trade struct { Result string; PnLMoney *float64 }` (tags JSON `result`, `pnl_money`)
  - `type Summary struct { PnL float64; WinRate float64; Trades int; HasData bool }`
  - `func tradesFilePath(virtual bool) string`
  - `func readTradesFile(path string) ([]Trade, error)`
  - `func computeSummary(trades []Trade) Summary`
  - Task 6 consome `tradesFilePath`, `readTradesFile`, `computeSummary`, `Summary`.

- [ ] **Step 1: Escrever os testes que falham**

```go
// metrics_test.go
package main

import (
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
	if s.PnL != -3.26 {
		t.Fatalf("PnL=%.2f, esperado -3.26", s.PnL)
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
```

- [ ] **Step 2: Rodar para confirmar que falham**

Run: `go test ./... -run "TestTradesFilePath|TestReadTradesFile|TestComputeSummary" -v`
Expected: FAIL — `undefined: tradesFilePath` / `undefined: Trade`

- [ ] **Step 3: Implementar `metrics.go`**

```go
// metrics.go
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
```

- [ ] **Step 4: Rodar para confirmar que passam**

Run: `go test ./... -run "TestTradesFilePath|TestReadTradesFile|TestComputeSummary" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add maestro/metrics.go maestro/metrics_test.go
git commit -m "feat(maestro): read trades and compute performance summary"
```

---

### Task 4: `badges.go` — mapeamento de status, modo e MT5

**Files:**
- Create: `maestro/badges.go`
- Test: `maestro/badges_test.go`

**Interfaces:**
- Consumes: `ColorBlue`, `ColorAmber`, `ColorGreen`, `ColorRed`, `ColorDim` (Task 2); `PythonWorker` (worker.go).
- Produces:
  - `type StatusBadge struct { Label string; Color lipgloss.Color }`
  - `func statusBadge(stateText string) StatusBadge`
  - `func renderBadge(b StatusBadge, width int) string`
  - `func detectMode(workers []*PythonWorker) string` → `"SIMULATOR"` | `"LIVE"`
  - `func detectMT5(workers []*PythonWorker) string` → `"ON"` | `"OFF"`
  - Task 6 consome todos.

- [ ] **Step 1: Escrever os testes que falham**

```go
// badges_test.go
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
	// "POS" (5 chars) precisa de padding; "SCAN" já tem 6 chars e não testa o alinhamento.
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
```

- [ ] **Step 2: Rodar para confirmar que falham**

Run: `go test ./... -run "TestStatusBadge|TestRenderBadge|TestDetectMode|TestDetectMT5" -v`
Expected: FAIL — `undefined: statusBadge`

- [ ] **Step 3: Implementar `badges.go`**

```go
// badges.go
package main

import (
	"strings"

	"github.com/charmbracelet/lipgloss"
)

// StatusBadge é o rótulo visual de estado de um worker.
type StatusBadge struct {
	Label string
	Color lipgloss.Color
}

// statusBadge mapeia o state_text do Python (ex.: "🔵 SCANNING") para um badge limpo.
func statusBadge(stateText string) StatusBadge {
	upper := strings.ToUpper(stateText)
	switch {
	case strings.Contains(upper, "SCANNING"),
		strings.Contains(upper, "WAIT_DATA"):
		return StatusBadge{Label: "SCAN", Color: ColorBlue}
	case strings.Contains(upper, "PENDING"),
		strings.Contains(upper, "EXTERNAL"):
		return StatusBadge{Label: "WAIT", Color: ColorAmber}
	case strings.Contains(upper, "IN_POSITION"),
		strings.Contains(upper, "PAPER_TRADE"):
		return StatusBadge{Label: "POS", Color: ColorGreen}
	case strings.Contains(upper, "ERRO"),
		strings.Contains(upper, "ERROR"):
		return StatusBadge{Label: "ERRO", Color: ColorRed}
	default:
		return StatusBadge{Label: "INIT", Color: ColorDim}
	}
}

// renderBadge renderiza "[LABEL]" com largura fixa, alinhado à direita.
func renderBadge(b StatusBadge, width int) string {
	label := "[" + b.Label + "]"
	if len(label) < width {
		label = strings.Repeat(" ", width-len(label)) + label
	}
	return lipgloss.NewStyle().Foreground(b.Color).Bold(true).Render(label)
}

// detectMode retorna SIMULATOR se algum worker está em study mode, senão LIVE.
func detectMode(workers []*PythonWorker) string {
	for _, w := range workers {
		if w.IsStudyMode {
			return "SIMULATOR"
		}
	}
	return "LIVE"
}

// detectMT5 é uma inferência: ON se ≥1 worker vivo e nenhum reportou erro.
func detectMT5(workers []*PythonWorker) string {
	if len(workers) == 0 {
		return "OFF"
	}
	for _, w := range workers {
		if strings.Contains(strings.ToUpper(w.StatusText), "ERRO") {
			return "OFF"
		}
	}
	return "ON"
}
```

- [ ] **Step 4: Rodar para confirmar que passam**

Run: `go test ./... -run "TestStatusBadge|TestRenderBadge|TestDetectMode|TestDetectMT5" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add maestro/badges.go maestro/badges_test.go
git commit -m "feat(maestro): map worker state to badges and detect mode/MT5"
```

---

### Task 5: `worker.go` — paleta curada + formatação de log (tag colorida, erro vermelho)

**Files:**
- Modify: `maestro/worker.go:55-56` (paleta no `Add`), `maestro/worker.go:204-222` (remover `prefixStyle` + usar `formatLogLine`)
- Test: `maestro/worker_format_test.go`

**Interfaces:**
- Consumes: `symbolColors` (Task 2), `ColorText`, `ColorRed` (Task 2).
- Produces: `func formatLogLine(symbol, timeframe, colorHex, text string) string` — Task 6 não consome diretamente, mas é o formato visível no EVENT LOG.

- [ ] **Step 1: Escrever os testes que falham**

```go
// worker_format_test.go
package main

import (
	"os"
	"regexp"
	"strings"
	"testing"

	"github.com/charmbracelet/lipgloss"
	"github.com/muesli/termenv"
)

// TestMain força perfil de cor TrueColor: fora de um TTY o lipgloss usa o
// perfil "ascii" e suprime códigos ANSI, o que impediria testar as cores.
func TestMain(m *testing.M) {
	lipgloss.SetColorProfile(termenv.TrueColor)
	os.Exit(m.Run())
}

var ansiRe = regexp.MustCompile(`\x1b\[[0-9;]*m`)

// stripAnsi remove sequências de escape ANSI (texto visível puro).
func stripAnsi(s string) string { return ansiRe.ReplaceAllString(s, "") }

func TestFormatLogLineTagColoridoMensagemNeutra(t *testing.T) {
	out := formatLogLine("EURUSD", "M5", "#7AA2F7", "mensagem normal")
	if !strings.Contains(stripAnsi(out), "[EURUSD|M5]") {
		t.Fatalf("tag ausente: %q", out)
	}
	if !strings.Contains(stripAnsi(out), "mensagem normal") {
		t.Fatalf("mensagem ausente: %q", out)
	}
}

func TestFormatLogLineErroVermelho(t *testing.T) {
	out := formatLogLine("HK50", "M5", "#7AA2F7", "ERRO: MT5 desconectado")
	if !strings.Contains(stripAnsi(out), "ERRO: MT5 desconectado") {
		t.Fatalf("mensagem de erro ausente: %q", out)
	}
	// Compara contra o render de referência do próprio lipgloss: as cores no
	// ANSI truecolor vêm em RGB decimal e podem sofrer arredondamento de 1,
	// então asserção por sequência exata é frágil.
	refRed := lipgloss.NewStyle().Foreground(ColorRed).Render("ERRO: MT5 desconectado")
	if !strings.Contains(out, refRed) {
		t.Fatalf("erro deveria ser colorido com ColorRed: %q", out)
	}
}
```

- [ ] **Step 2: Rodar para confirmar que falham**

Run: `go test ./... -run "TestFormatLogLine" -v`
Expected: FAIL — `undefined: formatLogLine`

- [ ] **Step 3: Implementar `formatLogLine` e aplicar paleta curada**

Adicionar ao final de `worker.go`:

```go
// formatLogLine monta a linha de log: tag [ATIVO|TF] colorida pelo símbolo,
// mensagem em texto neutro, erros em vermelho (hierarquia de severidade).
func formatLogLine(symbol, timeframe, colorHex, text string) string {
	tag := fmt.Sprintf("[%s|%s]", symbol, timeframe)
	coloredTag := lipgloss.NewStyle().
		Foreground(lipgloss.Color(colorHex)).
		Bold(true).
		Render(tag)

	upper := strings.ToUpper(text)
	msgStyle := lipgloss.NewStyle().Foreground(ColorText)
	if strings.Contains(upper, "ERRO") || strings.Contains(upper, "ERROR") ||
		strings.Contains(upper, "FALHA") || strings.Contains(upper, "CRASH") {
		msgStyle = lipgloss.NewStyle().Foreground(ColorRed)
	}
	return coloredTag + " " + msgStyle.Render(text)
}
```

Adicionar import de `"strings"` ao bloco de imports de `worker.go`.

Substituir a paleta em `Add` (worker.go:55-56):

```go
// ANTES:
colors := []string{"#00FFFF", "#00FF00", "#FF00FF", "#FFFF00", "#FFA500", "#FFC0CB", "#8A2BE2", "#00BFFF"}
w.ColorHex = colors[len(m.workers)%len(colors)]

// DEPOIS:
w.ColorHex = string(symbolColors[len(m.workers)%len(symbolColors)])
```

Substituir o bloco `prefixStyle` + corpo da goroutine de stderr (worker.go:204-222) pelo uso de `formatLogLine`:

```go
go func() {
	scanner := bufio.NewScanner(stderr)
	for scanner.Scan() {
		text := scanner.Text()
		if text != "" && text != "\n" {
			log.Print(formatLogLine(w.Symbol, w.Timeframe, w.ColorHex, text))
		}
	}
}()
```

> Importante: remover junto o bloco morto `colorHex`/`prefixStyle` (worker.go:204-209). Sem o uso na goroutine, `prefixStyle` vira variável declarada e não usada (erro de compilação). O fallback de cor vazia deixa de ser necessário: `Add` (linha 56) sempre preenche `w.ColorHex` com a paleta curada. Imports: `fmt`, `log`, `lipgloss` já existem em worker.go; adicionar apenas `"strings"`.

- [ ] **Step 4: Rodar para confirmar que passam**

Run: `go test ./... -run "TestFormatLogLine" -v; go vet ./...`
Expected: PASS; vet limpo

- [ ] **Step 5: Commit**

```bash
git add maestro/worker.go maestro/worker_format_test.go
git commit -m "feat(maestro): curated symbol palette and severity-aware log format"
```

---

### Task 6: `main.go` — layout em grid, top bar, painel de performance

**Files:**
- Modify: `maestro/main.go` (model struct, `initialModel`, `Update` WindowSizeMsg, `updateStatus`, `View`; estilos `titleStyle`/`inputStyle`)
- Test: `maestro/main_ui_test.go`

**Interfaces:**
- Consumes: tokens (Task 2), `Summary`/`tradesFilePath`/`readTradesFile`/`computeSummary` (Task 3), `statusBadge`/`renderBadge`/`detectMode`/`detectMT5`/`StatusBadge` (Task 4).
- Produces: layout final exibido ao usuário.

- [ ] **Step 1: Escrever os testes que falham**

```go
// main_ui_test.go
package main

import (
	"strings"
	"testing"

	"github.com/charmbracelet/bubbles/viewport"
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
	if !strings.Contains(out, "Sem dados") {
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
		"MAESTRO v2.4",
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

func TestViewSimulador(t *testing.T) {
	m := initialModel()
	m.ready = true
	m.width, m.height = 120, 40
	m.viewport = viewport.New(60, 10)
	// O modo é derivado dos workers (detectMode); setar m.mode à mão não sobrevive
	// ao updateStatus. Para SIMULATOR é preciso um worker em study mode.
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
```

- [ ] **Step 2: Rodar para confirmar que falham**

Run: `go test ./... -run "TestRenderPerformance|TestViewRenderizaPainéis|TestViewSimulador" -v`
Expected: FAIL — `undefined: renderPerformance`

- [ ] **Step 3: Implementar**

**(a) Estilos (main.go:37-44) — derivar dos tokens:**

```go
var (
	titleStyle = lipgloss.NewStyle().
			Foreground(ColorAmber).
			Bold(true)

	inputStyle = lipgloss.NewStyle().
			Foreground(ColorText)

	dimStyle = lipgloss.NewStyle().
			Foreground(ColorDim)
)
```

**(b) Model struct (main.go:79-89) — adicionar campos:**

```go
type model struct {
	viewport    viewport.Model
	textInput   textinput.Model
	spin        spinner.Model
	manager     *WorkerManager
	logs        []string
	ready       bool
	dashboard   string
	perfContent string
	mode        string
	mt5Status   string
	leftWidth   int
	rightWidth  int
	width       int
	height      int
}
```

**(c) Remover `getASCIIArt` e adicionar helper de top bar + performance:**

```go
const uiVersion = "2.4"

// topBar monta a linha superior: título à esquerda, badges à direita.
func (m model) topBar() string {
	title := " " + titleStyle.Render("MAESTRO v"+uiVersion)

	modeColor := ColorBlue
	if m.mode == "SIMULATOR" {
		modeColor = ColorAmber
	}
	modeBadge := lipgloss.NewStyle().
		Foreground(modeColor).
		Bold(true).
		Render("[ MODE: " + m.mode + " ]")

	mt5Color := ColorGreen
	if m.mt5Status == "OFF" {
		mt5Color = ColorRed
	}
	mt5Badge := lipgloss.NewStyle().
		Foreground(mt5Color).
		Bold(true).
		Render("[ MT5: " + m.mt5Status + " ]")

	badges := "  " + modeBadge + "  " + mt5Badge + " "
	fill := m.width - lipgloss.Width(title) - lipgloss.Width(badges)
	if fill < 2 {
		fill = 2
	}
	return title + lipgloss.NewStyle().Foreground(ColorBorder).Render(strings.Repeat("─", fill)) + badges
}

// loadSummary lê o JSON de trades conforme o modo ativo.
func (m *model) loadSummary() Summary {
	virtual := m.mode == "SIMULATOR"
	trades, err := readTradesFile(tradesFilePath(virtual))
	if err != nil {
		return Summary{}
	}
	return computeSummary(trades)
}

// renderPerformance formata a linha única de métricas do painel inferior.
func renderPerformance(s Summary) string {
	if !s.HasData {
		return dimStyle.Render("Sem dados ainda. Inicie /study ou /add.")
	}
	sign := "+"
	pnlColor := ColorGreen
	if s.PnL < 0 {
		sign = "-"
		pnlColor = ColorRed
	}
	pnl := lipgloss.NewStyle().
		Foreground(pnlColor).
		Bold(true).
		Render(fmt.Sprintf("%s$%.2f", sign, math.Abs(s.PnL)))
	return fmt.Sprintf("PnL Total: %s  |  Win Rate: %.1f%%  |  Trades: %d", pnl, s.WinRate, s.Trades)
}
```

Adicionar `"math"` ao bloco de imports de `main.go`.

**(d) `updateStatus` (main.go:236-267) — reescrever:**

```go
func (m *model) updateStatus() {
	workers := m.manager.List()

	m.mode = detectMode(workers)
	m.mt5Status = detectMT5(workers)

	var b strings.Builder
	if len(workers) == 0 {
		b.WriteString(dimStyle.Render("Nenhum robô ativo. Digite /study <ATIVO> [TIMEFRAME]"))
	} else {
		b.WriteString(titleStyle.Render("ATIVOS EM EXECUÇÃO"))
		b.WriteString("\n")
		b.WriteString(dimStyle.Render("ATIVO    TF  STATUS"))
		b.WriteString("\n")
		b.WriteString(dimStyle.Render(strings.Repeat("─", 28)))
		b.WriteString("\n")
		for _, w := range workers {
			badge := renderBadge(statusBadge(w.StatusText), 6)
			uptime := time.Since(w.StartTime).Round(time.Second)
			b.WriteString(fmt.Sprintf("%-8s %-5s %s  %s\n", w.Symbol, w.Timeframe, badge, dimStyle.Render(uptime.String())))
		}
	}
	m.dashboard = b.String()

	m.perfContent = renderPerformance(m.loadSummary())

	// Dimensões do grid: esquerda ~33%, direita o restante.
	m.leftWidth = m.width * 33 / 100
	if m.leftWidth < 20 {
		m.leftWidth = 20
	}
	m.rightWidth = m.width - m.leftWidth - 3
	if m.rightWidth < 30 {
		m.rightWidth = 30
	}

	// Alturas: top bar (1) + rodapé (1) + painel performance (5) + chrome do log (4).
	// vpHeight = m.height - 11 mantém o rodapé do log alinhado com o do painel esquerdo.
	const topBarHeight, footerHeight, perfPanelHeight, logChrome = 1, 1, 5, 4
	panelsHeight := m.height - topBarHeight - footerHeight
	vpHeight := panelsHeight - perfPanelHeight - logChrome
	if vpHeight < 0 {
		vpHeight = 0
	}
	m.viewport.Width = m.rightWidth - 2
	m.viewport.Height = vpHeight
}
```

**(e) `View` (main.go:404-431) — reescrever com grid:**

```go
func (m model) View() string {
	if !m.ready {
		return "\n  Iniciando Maestro..."
	}

	header := m.topBar()

	leftPanel := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(ColorBorder).
		Width(m.leftWidth).
		Height(m.height - 2).
		Render(m.dashboard)

	logTitle := "EVENT LOG (Live)"
	if m.mode == "SIMULATOR" {
		logTitle = "EVENT LOG (Simulador)"
	}

	logPanel := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(ColorBorder).
		Width(m.rightWidth).
		Render(lipgloss.JoinVertical(lipgloss.Left,
			lipgloss.NewStyle().Bold(true).Foreground(ColorText).Render(logTitle),
			dimStyle.Render(strings.Repeat("─", m.rightWidth-2)),
			m.viewport.View(),
		))

	perfPanel := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(ColorBorder).
		Width(m.rightWidth).
		Render(lipgloss.JoinVertical(lipgloss.Left,
			lipgloss.NewStyle().Bold(true).Foreground(ColorText).Render("PERFORMANCE RESUMO (Sessão Atual)"),
			dimStyle.Render(strings.Repeat("─", m.rightWidth-2)),
			m.perfContent,
		))

	rightColumn := lipgloss.JoinVertical(lipgloss.Top, logPanel, perfPanel)
	middle := lipgloss.JoinHorizontal(lipgloss.Top, leftPanel, rightColumn)

	return fmt.Sprintf("%s\n%s\n %s%s", header, middle, m.spin.View(), m.textInput.View())
}
```

> Nota: `m.leftWidth`/`m.rightWidth` e `m.viewport.Width/Height` já foram calculados em `updateStatus` (que roda a cada tick e resize). `View` não recalcula dimensões — só monta o grid. O rodapé inferior da coluna direita (`logPanel` + `perfPanel`) fica alinhado com o do painel esquerdo porque `vpHeight = m.height - 11` garante que `logPanel(vpHeight+4) + perfPanel(5) = m.height - 2 = leftPanel.Height`.

**(f) Ajustar `WindowSizeMsg` (main.go:161-191):** remover o cálculo antigo de `getASCIIArt`/`vpWidth`/`vpHeight`; criar o viewport antes de `updateStatus` para que as dimensões do grid já cheguem corretas:

```go
case tea.WindowSizeMsg:
	m.width = msg.Width
	m.height = msg.Height
	if !m.ready {
		m.viewport = viewport.New(60, 10)
		m.ready = true
	}
	m.updateStatus()
	m.viewport.SetContent(wrapLogs(m.logs, m.viewport.Width))
	m.viewport.GotoBottom()
```

Adicionar helper para embrulhar logs sem depender de estilo global:

```go
func wrapLogs(logs []string, width int) string {
	if width < 10 {
		width = 10
	}
	return lipgloss.NewStyle().Width(width).Render(strings.Join(logs, "\n"))
}
```

Atualizar os demais usos de `wrapStyle`/`SetContent` no `Update` (KeyEnter e LogMsg) para chamar `wrapLogs(m.logs, m.viewport.Width)` (mesma lógica, sem duplicar o estilo).

- [ ] **Step 4: Rodar para confirmar que passam**

Run: `go test ./... -run "TestRenderPerformance|TestViewRenderizaPainéis|TestViewSimulador" -v`
Expected: PASS

- [ ] **Step 5: Rodar build + vet + suite completa**

Run: `go build ./...; go vet ./...; go test ./...`
Expected: build OK; vet limpo; todos os testes PASS.

- [ ] **Step 6: Commit**

```bash
git add maestro/main.go maestro/main_ui_test.go
git commit -m "feat(maestro): grid layout, top bar and mode-aware performance panel"
```

---

## Self-Review

**1. Cobertura do spec:**
- Tokens centralizados → Task 2 (style.go) ✓
- Paleta de símbolos curada → Task 5 ✓
- Grid 4 regiões + top bar + badges → Task 6 ✓
- Badge MODE/MT5 → Task 4 + 6 ✓
- Painel performance modo-consciente (trades.json vs virtual_trades.json) → Task 3 + 6 ✓
- Badges sem emoji, largura fixa, alinhados à direita → Task 4 ✓
- Terminologia de modo dinâmica (EVENT LOG Live/Simulador) → Task 6 ✓
- Hierarquia de severidade (tag colorida, mensagem neutra, erro vermelho) → Task 5 ✓
- Correção `go vet` → Task 1 ✓
- Sem mudança em Python → nenhuma task toca `mt5bot/`/`interfaces/` ✓
- PnL com sinal, WR 1 casa decimal, números alinhados → Task 6 `renderPerformance` ✓

**2. Placeholders:** nenhum TBD/TODO; todos os passos têm código concreto. ✓

**3. Consistência de tipos:** nomes cruzados conferidos — `symbolColors` (T2)→T5; `ColorText`/`ColorRed` (T2)→T5/T6; `Summary`/`tradesFilePath`/`readTradesFile`/`computeSummary` (T3)→T6; `statusBadge`/`renderBadge`/`detectMode`/`detectMT5`/`StatusBadge` (T4)→T6. `renderPerformance` definido na T6 e usado na própria T6. ✓