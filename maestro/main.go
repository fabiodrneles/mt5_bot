package main

import (
	"fmt"
	"log"
	"math"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"github.com/charmbracelet/bubbles/spinner"
	"github.com/charmbracelet/bubbles/textinput"
	"github.com/charmbracelet/bubbles/viewport"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

// Global program reference
var p *tea.Program

// Messages
type LogMsg string
type tickMsg time.Time

// logWriter implements io.Writer and sends logs to the tea program
type logWriter struct{}

func (l logWriter) Write(data []byte) (n int, err error) {
	if p != nil {
		str := string(data)
		p.Send(LogMsg(str))
	}
	return len(data), nil
}

// Styling (Lipgloss) — derivado dos design tokens de style.go
var (
	titleStyle = lipgloss.NewStyle().
			Foreground(ColorAmber).
			Bold(true)

	inputStyle = lipgloss.NewStyle().
			Foreground(ColorText)

	dimStyle = lipgloss.NewStyle().
			Foreground(ColorDim)
)

const uiVersionFallback = "2.3.2"

// maxPerfPanelHeight limita o painel de performance: título(1) + divisor(1) +
// borda(2) + até 6 linhas de workers, deixando espaço para o event log.
const maxPerfPanelHeight = 10

// maxPerfLines = linhas de conteúdo do painel de performance.
const maxPerfLines = maxPerfPanelHeight - 4

var cachedVersion string

// botVersion retorna a versão real do projeto lida do ../pyproject.toml —
// a mesma fonte única que o launcher usa no `mt5bot -v`. Cacheada após a
// primeira leitura; fallback para uiVersionFallback se o arquivo não existir.
func botVersion() string {
	if cachedVersion != "" {
		return cachedVersion
	}
	cachedVersion = readProjectVersion()
	if cachedVersion == "" {
		cachedVersion = uiVersionFallback
	}
	return cachedVersion
}

func readProjectVersion() string {
	data, err := os.ReadFile(filepath.Join("..", "pyproject.toml"))
	if err != nil {
		return ""
	}
	return parseProjectVersion(string(data))
}

func parseProjectVersion(content string) string {
	for _, line := range strings.Split(content, "\n") {
		line = strings.TrimSpace(line)
		if strings.HasPrefix(line, "version =") {
			parts := strings.SplitN(line, "=", 2)
			if len(parts) == 2 {
				return strings.Trim(strings.TrimSpace(parts[1]), `"`)
			}
		}
	}
	return ""
}

// topBar monta a linha superior: título à esquerda, badges à direita.
func (m model) topBar() string {
	title := " " + titleStyle.Render("MAESTRO v"+botVersion())

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

// perfPanelContent gera as linhas do painel de performance, uma por worker
// ativo. Em SIMULATOR cada linha reflete a sessão atual (entry_time >=
// StartTime do worker); em LIVE reflete todo o histórico real do ativo.
// Se houver mais workers que maxPerfLines, mostra os primeiros e indica o
// restante, para o painel nunca ultrapassar a altura reservada.
func perfPanelContent(workers []*PythonWorker, mode string, width int) string {
	if len(workers) == 0 {
		return dimStyle.Render(truncate("Sem dados ainda. Inicie /study ou /add.", width))
	}
	limit := len(workers)
	if limit > maxPerfLines {
		limit = maxPerfLines
	}
	lines := make([]string, 0, limit+1)
	for _, w := range workers[:limit] {
		lines = append(lines, renderWorkerLine(w, workerSummary(w, mode), width))
	}
	if extra := len(workers) - limit; extra > 0 {
		lines = append(lines, dimStyle.Render(fmt.Sprintf("+%d ativo(s) no painel esquerdo", extra)))
	}
	return strings.Join(lines, "\n")
}

// renderWorkerLine formata uma linha de performance de um worker:
// [SYMBOL|TF] LOTE 0.10  PnL +$x.xx  WR xx.x%  N trades.
// width garante que o resultado não wrape dentro do painel.
func renderWorkerLine(w *PythonWorker, s Summary, width int) string {
	if width < 30 {
		width = 30
	}
	tagPlain := fmt.Sprintf("[%s|%s]", w.Symbol, w.Timeframe)
	lotPlain := fmt.Sprintf("LOTE %.2f", assetMinLot(w.Symbol))
	tag := lipgloss.NewStyle().
		Foreground(lipgloss.Color(w.ColorHex)).
		Bold(true).
		Render(tagPlain)
	lot := dimStyle.Render(lotPlain)
	if !s.HasData {
		plain := truncate(fmt.Sprintf("%s %s  %s", tagPlain, lotPlain, "sem dados"), width)
		plain = strings.Replace(plain, tagPlain, tag, 1)
		return strings.Replace(plain, lotPlain, lot, 1)
	}
	sign := "+"
	pnlColor := ColorGreen
	if s.PnL < 0 {
		sign = "-"
		pnlColor = ColorRed
	}
	pnlPlain := fmt.Sprintf("%s$%.2f", sign, math.Abs(s.PnL))
	plain := truncate(fmt.Sprintf("%s %s  %s  WR %.1f%%  %dT", tagPlain, lotPlain, pnlPlain, s.WinRate, s.Trades), width)
	plain = strings.Replace(plain, tagPlain, tag, 1)
	plain = strings.Replace(plain, lotPlain, lot, 1)
	styledPnl := lipgloss.NewStyle().
		Foreground(pnlColor).
		Bold(true).
		Render(pnlPlain)
	plain = strings.Replace(plain, pnlPlain, styledPnl, 1)
	return plain
}

// truncate limita o texto a width colunas visíveis, com reticências.
func truncate(s string, width int) string {
	if width < 0 {
		return ""
	}
	r := []rune(s)
	if len(r) <= width {
		return s
	}
	if width <= 1 {
		return "…"
	}
	return string(r[:width-1]) + "…"
}

// renderPerformance formata a linha única de métricas do painel inferior.
// width garante que o resultado não wrape dentro do painel (lipgloss Width
// wrapparia, quebrando a altura do grid).
func renderPerformance(s Summary, width int) string {
	if width < 20 {
		width = 20
	}
	if !s.HasData {
		return dimStyle.Render(truncate("Sem dados ainda. Inicie /study ou /add.", width))
	}
	sign := "+"
	pnlColor := ColorGreen
	if s.PnL < 0 {
		sign = "-"
		pnlColor = ColorRed
	}
	pnlPlain := fmt.Sprintf("%s$%.2f", sign, math.Abs(s.PnL))
	plain := truncate(fmt.Sprintf("PnL Total: %s  |  Win Rate: %.1f%%  |  Trades: %d", pnlPlain, s.WinRate, s.Trades), width)
	styled := lipgloss.NewStyle().
		Foreground(pnlColor).
		Bold(true).
		Render(pnlPlain)
	if strings.Contains(plain, pnlPlain) {
		return strings.Replace(plain, pnlPlain, styled, 1)
	}
	return plain
}

// wrapLogs embrulha os logs na largura do viewport.
func wrapLogs(logs []string, width int) string {
	if width < 10 {
		width = 10
	}
	return lipgloss.NewStyle().Width(width).Render(strings.Join(logs, "\n"))
}

type model struct {
	viewport    viewport.Model
	textInput   textinput.Model
	spin        spinner.Model
	manager     *WorkerManager
	logs        []string
	ready       bool
	dashboard        string
	perfContent      string
	perfPanelHeight  int
	mode             string
	mt5Status   string
	leftWidth   int
	rightWidth  int
	width       int
	height      int
}

func initialModel() model {
	ti := textinput.New()
	ti.Placeholder = "Digite /help para listar comandos..."
	ti.Prompt = " mt5bot ❯ "
	ti.PromptStyle = titleStyle
	ti.TextStyle = inputStyle
	ti.Focus()
	ti.CharLimit = 156
	ti.Width = 100

	s := spinner.New()
	s.Spinner = spinner.Line
	s.Style = lipgloss.NewStyle().Foreground(lipgloss.Color("#00FF00"))

	m := model{
		textInput: ti,
		spin:      s,
		manager:   NewWorkerManager(),
		logs:      []string{},
	}
	return m
}

func (m model) Init() tea.Cmd {
	return tea.Batch(
		textinput.Blink,
		m.spin.Tick,
		tickCmd(),
	)
}

func tickCmd() tea.Cmd {
	return tea.Tick(time.Second*1, func(t time.Time) tea.Msg {
		return tickMsg(t)
	})
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	var (
		tiCmd tea.Cmd
		vpCmd tea.Cmd
		cmds  []tea.Cmd
	)

	switch msg := msg.(type) {
	case spinner.TickMsg:
		var spinCmd tea.Cmd
		m.spin, spinCmd = m.spin.Update(msg)
		cmds = append(cmds, spinCmd)

	case tea.KeyMsg:
		switch msg.Type {
		case tea.KeyCtrlC, tea.KeyEsc:
			return m, tea.Quit
		case tea.KeyEnter:
			line := strings.TrimSpace(m.textInput.Value())
			m.textInput.SetValue("")
			if line != "" {
				m.logs = append(m.logs, dimStyle.Render("> "+line))
				cmd := m.handleCommand(line)
				if cmd != nil {
					cmds = append(cmds, cmd)
				}
			}
			m.viewport.SetContent(wrapLogs(m.logs, m.viewport.Width))
			m.viewport.GotoBottom()
			return m, tea.Batch(cmds...)
		}

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

	case LogMsg:
		// Clean ANSI reset for empty lines
		txt := string(msg)
		if txt != "" && txt != "\n" {
			m.logs = append(m.logs, strings.TrimRight(txt, "\n"))
			// Cap at 1000 lines to prevent UI freeze
			if len(m.logs) > 1000 {
				m.logs = m.logs[len(m.logs)-1000:]
			}
			m.viewport.SetContent(wrapLogs(m.logs, m.viewport.Width))
			m.viewport.GotoBottom()
		}

	case tickMsg:
		m.updateStatus()
		
		// Update spinner color based on worker health
		workers := m.manager.List()
		hasDisabled := false
		for _, w := range workers {
			if w.IsDisabled() {
				hasDisabled = true
				break
			}
		}
		if hasDisabled {
			m.spin.Style = lipgloss.NewStyle().Foreground(lipgloss.Color("#FFFF00")) // Yellow
		} else {
			m.spin.Style = lipgloss.NewStyle().Foreground(lipgloss.Color("#00FF00")) // Green
		}
		
		cmds = append(cmds, tickCmd())
	}

	// Update components
	m.textInput, tiCmd = m.textInput.Update(msg)
	m.viewport, vpCmd = m.viewport.Update(msg)

	cmds = append(cmds, tiCmd, vpCmd)
	return m, tea.Batch(cmds...)
}

func (m *model) updateStatus() {
	workers := m.manager.List()

	m.mode = detectMode(workers)
	m.mt5Status = detectMT5(workers)

	// Dimensões do grid: esquerda ~33%, direita o restante.
	m.leftWidth = m.width * 33 / 100
	if m.leftWidth < 20 {
		m.leftWidth = 20
	}
	m.rightWidth = m.width - m.leftWidth - 3
	if m.rightWidth < 30 {
		m.rightWidth = 30
	}

	// Rodapé: " " + spinner(1) + prompt " mt5bot ❯ " (9) + input. O input
	// precisa encolher com o terminal para a linha não quebrar.
	m.textInput.Width = m.width - 12
	if m.textInput.Width < 10 {
		m.textInput.Width = 10
	}

	var b strings.Builder
	if len(workers) == 0 {
		b.WriteString(dimStyle.Render("Nenhum robô ativo. Digite /study <ATIVO> [TIMEFRAME]"))
	} else {
		b.WriteString(titleStyle.Render("ATIVOS EM EXECUÇÃO"))
		b.WriteString("\n")
		b.WriteString(dimStyle.Render("ATIVO    TF  STATUS"))
		b.WriteString("\n")
		b.WriteString(dimStyle.Render(strings.Repeat("─", m.leftWidth-2)))
		b.WriteString("\n")
		for _, w := range workers {
			badge := renderBadge(statusBadge(w.StatusText), 6)
			uptime := time.Since(w.StartTime).Round(time.Second)
			b.WriteString(fmt.Sprintf("%-8s %-5s %s  %s\n", w.Symbol, w.Timeframe, badge, dimStyle.Render(uptime.String())))
		}
	}
	m.dashboard = b.String()

	m.perfContent = perfPanelContent(workers, m.mode, m.rightWidth-2)
	contentLines := 1
	if m.perfContent != "" {
		contentLines = strings.Count(m.perfContent, "\n") + 1
	}
	m.perfPanelHeight = 4 + contentLines
	if m.perfPanelHeight > maxPerfPanelHeight {
		m.perfPanelHeight = maxPerfPanelHeight
	}

	// Alturas: top bar (1) + rodapé (1) + painel performance (dinâmico) +
	// chrome do log (4). vpHeight = m.height - perfPanelHeight - 6 alinha o
	// rodapé do log com o do painel esquerdo.
	const topBarHeight, footerHeight, logChrome = 1, 1, 4
	panelsHeight := m.height - topBarHeight - footerHeight
	vpHeight := panelsHeight - m.perfPanelHeight - logChrome
	if vpHeight < 0 {
		vpHeight = 0
	}
	m.viewport.Width = m.rightWidth - 2
	m.viewport.Height = vpHeight
}

func (m *model) handleCommand(line string) tea.Cmd {
	cmd := parseCommand(line)
	green := lipgloss.NewStyle().Foreground(lipgloss.Color("#00FF00"))
	red := lipgloss.NewStyle().Foreground(lipgloss.Color("#FF0000"))
	dim := lipgloss.NewStyle().Foreground(lipgloss.Color("#888888"))
	bold := lipgloss.NewStyle().Bold(true)

	switch cmd.Name {
	case "add":
		if cmd.Symbol == "" {
			m.logs = append(m.logs, red.Render(tr("usage_add")))
			return nil
		}
		worker := NewPythonWorker(cmd.Symbol, cmd.Timeframe)
		if err := m.manager.Add(worker); err != nil {
			m.logs = append(m.logs, red.Render(err.Error()))
			return nil
		}
		go worker.Start()
		m.logs = append(m.logs, green.Render(fmt.Sprintf(tr("worker_started"), cmd.Symbol, cmd.Timeframe)))
		return nil

	case "study":
		if cmd.Symbol == "" {
			m.logs = append(m.logs, red.Render("Uso: /study <ATIVO> [TIMEFRAME]"))
			return nil
		}
		worker := NewPythonWorker(cmd.Symbol, cmd.Timeframe)
		worker.IsStudyMode = true
		if err := m.manager.Add(worker); err != nil {
			m.logs = append(m.logs, red.Render(err.Error()))
			return nil
		}
		go worker.Start()
		m.logs = append(m.logs, green.Render(fmt.Sprintf("Iniciando simulação (Study Mode) para %s (%s)", cmd.Symbol, cmd.Timeframe)))
		return nil

	case "stop":
		if cmd.Symbol == "" {
			m.logs = append(m.logs, red.Render(tr("usage_stop")))
			return nil
		}
		if m.manager.Remove(cmd.Symbol) {
			m.logs = append(m.logs, green.Render(fmt.Sprintf(tr("worker_stopped"), cmd.Symbol)))
		} else {
			m.logs = append(m.logs, red.Render(fmt.Sprintf(tr("worker_notfound"), cmd.Symbol)))
		}

	case "mechanic":
		workers := m.manager.List()
		healed := 0
		for _, w := range workers {
			if w.IsDisabled() {
				w.Heal()
				healed++
				m.logs = append(m.logs, green.Render(fmt.Sprintf("Mecânico consertou e reiniciou o robô de %s!", w.Symbol)))
			}
		}
		if healed == 0 {
			m.logs = append(m.logs, dim.Render("Nenhum robô precisando de reparos."))
		}
		return nil

	case "list":
		workers := m.manager.List()
		if len(workers) == 0 {
			m.logs = append(m.logs, dim.Render(tr("no_workers")))
			return nil
		}
		m.logs = append(m.logs, bold.Render(tr("workers_active")))
		for _, w := range workers {
			m.logs = append(m.logs, fmt.Sprintf(" - %s (Timeframe: %s) Status: %s", w.Symbol, w.Timeframe, w.StatusText))
		}

	case "report":
		m.logs = append(m.logs, dim.Render(tr("report_gen")))
		cmdPy := exec.Command("python", "../tracker.py", "--report")
		out, err := cmdPy.CombinedOutput()
		if err != nil {
			m.logs = append(m.logs, red.Render(fmt.Sprintf("Error running report: %v\n%s", err, string(out))))
		} else {
			m.logs = append(m.logs, string(out))
		}

	case "dashboard":
		m.logs = append(m.logs, dim.Render(tr("dashboard_open")))
		cmdPy := exec.Command("python", "../dashboard.py")
		cmdPy.Start()

	case "help":
		m.logs = append(m.logs, bold.Render(tr("help_title")))
		m.logs = append(m.logs, tr("help_add"))
		m.logs = append(m.logs, tr("help_study"))
		m.logs = append(m.logs, tr("help_stop"))
		m.logs = append(m.logs, tr("help_list"))
		m.logs = append(m.logs, tr("help_report"))
		m.logs = append(m.logs, tr("help_dashboard"))
		m.logs = append(m.logs, tr("help_fix"))
		m.logs = append(m.logs, tr("help_quit"))
		m.logs = append(m.logs, tr("help_quit_cancel"))
		m.logs = append(m.logs, tr("help_quit_flat"))
		m.logs = append(m.logs, tr("help_quit_all"))
		m.logs = append(m.logs, tr("help_lang"))

	case "idioma":
		if cmd.Symbol == "" || normalizeLang(cmd.Symbol) == "" {
			m.logs = append(m.logs, red.Render(tr("lang_invalid")))
			return nil
		}
		currentLang = normalizeLang(cmd.Symbol)
		saveLang(currentLang)
		m.logs = append(m.logs, green.Render(tr("lang_set")))

	case "quit":
		m.logs = append(m.logs, lipgloss.NewStyle().Foreground(lipgloss.Color("#FFA500")).Render(tr("shutdown_start")))
		if cmd.Action != "" {
			m.logs = append(m.logs, dim.Render(fmt.Sprintf(tr("action_requested"), cmd.Action)))
			shutdownCmd := exec.Command("python", "../brain/shutdown_manager.py", cmd.Action)
			out, err := shutdownCmd.CombinedOutput()
			if err != nil {
				m.logs = append(m.logs, red.Render(fmt.Sprintf("%s %v\n%s", tr("shutdown_err"), err, string(out))))
			} else {
				m.logs = append(m.logs, string(out))
			}
		} else {
			m.logs = append(m.logs, dim.Render(tr("shutdown_none")))
		}
		return tea.Quit

	default:
		m.logs = append(m.logs, red.Render(tr("unknown_cmd")))
	}
	return nil
}

func (m model) View() string {
	if !m.ready {
		return "\n  Iniciando Maestro..."
	}

	header := m.topBar()

	// Nota lipgloss v1.1.0: Width/Height com border SOMAM a borda ao tamanho
	// (Width(n) + borda = n+2). Por isso subtraímos 2 do frame para o total
	// bater exatamente em m.leftWidth / m.rightWidth / (m.height-2).
	leftPanel := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(ColorBorder).
		Width(m.leftWidth - 2).
		Height(m.height - 4).
		Render(m.dashboard)

	logTitle := "EVENT LOG (Live)"
	if m.mode == "SIMULATOR" {
		logTitle = "EVENT LOG (Simulador)"
	}

	logPanel := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(ColorBorder).
		Width(m.rightWidth - 2).
		Render(lipgloss.JoinVertical(lipgloss.Left,
			lipgloss.NewStyle().Bold(true).Foreground(ColorText).Render(logTitle),
			dimStyle.Render(strings.Repeat("─", m.rightWidth-2)),
			m.viewport.View(),
		))

	perfTitle := "PERFORMANCE RESUMO (Por Ativo)"
	if m.mode == "SIMULATOR" {
		perfTitle = "PERFORMANCE RESUMO (Sessão Atual)"
	}
	perfPanel := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(ColorBorder).
		Width(m.rightWidth - 2).
		Height(m.perfPanelHeight - 2).
		Render(lipgloss.JoinVertical(lipgloss.Left,
			lipgloss.NewStyle().Bold(true).Foreground(ColorText).Render(perfTitle),
			dimStyle.Render(strings.Repeat("─", m.rightWidth-2)),
			m.perfContent,
		))

	rightColumn := lipgloss.JoinVertical(lipgloss.Top, logPanel, perfPanel)
	middle := lipgloss.JoinHorizontal(lipgloss.Top, leftPanel, rightColumn)

	return fmt.Sprintf("%s\n%s\n %s%s", header, middle, m.spin.View(), m.textInput.View())
}

func main() {
	for _, arg := range os.Args[1:] {
		if arg == "--version" || arg == "-v" {
			fmt.Println("MT5Bot v" + botVersion())
			os.Exit(0)
		} else if strings.HasPrefix(arg, "-") && arg != "--report" && arg != "--dashboard" && arg != "--quick" && arg != "--help" && arg != "-h" {
			fmt.Printf("Erro crítico: flag desconhecida '%s'\n", arg)
			os.Exit(1)
		}
	}

	// Remover arquivo de lock de shutdown antigo, se existir
	os.Remove("../.no_new_trades")
	os.Remove(".no_new_trades")

	currentLang = loadSavedLang()

	// Redirect standard log to our Bubbletea program
	log.SetFlags(log.Ltime)
	log.SetOutput(logWriter{})

	m := initialModel()
	p = tea.NewProgram(
		m,
		tea.WithAltScreen(),       // use the full size of the terminal
		tea.WithMouseCellMotion(), // turn on mouse support
	)

	if _, err := p.Run(); err != nil {
		fmt.Printf("Erro na inicialização: %v", err)
		os.Exit(1)
	}

	// Application stopped
	fmt.Println(lipgloss.NewStyle().Foreground(lipgloss.Color("#888888")).Render(tr("msg_shutting")))
	m.manager.StopAll()
	fmt.Println(lipgloss.NewStyle().Foreground(lipgloss.Color("#00FF00")).Render(tr("msg_done")))
}
