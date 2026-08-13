package main

import (
	"fmt"
	"log"
	"os"
	"os/exec"
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

// Styling (Lipgloss)
var (
	titleStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#FF8C00")).
			Bold(true)

	inputStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#FFB067"))
)

func getASCIIArt() string {
	colors := []lipgloss.Color{
		lipgloss.Color("#D35400"), // Dark orange
		lipgloss.Color("#E67E22"), // Orange
		lipgloss.Color("#F39C12"), // Orange-yellow
		lipgloss.Color("#F1C40F"), // Lighter
		lipgloss.Color("#F4D03F"), // Yellowish
		lipgloss.Color("#F7DC6F"), // Yellow
	}

	lines := []string{
		`███╗   ███╗  █████╗  ███████╗ ███████╗ ████████╗ ██████╗   ██████╗ `,
		`████╗ ████║ ██╔══██╗ ██╔════╝ ██╔════╝ ╚══██╔══╝ ██╔══██╗ ██╔═══██╗`,
		`██╔████╔██║ ███████║ █████╗   ███████╗    ██║    ██████╔╝ ██║   ██║`,
		`██║╚██╔╝██║ ██╔══██║ ██╔══╝   ╚════██║    ██║    ██╔══██╗ ██║   ██║`,
		`██║ ╚═╝ ██║ ██║  ██║ ███████╗ ███████║    ██║    ██║  ██║ ╚██████╔╝`,
		`╚═╝     ╚═╝ ╚═╝  ╚═╝ ╚══════╝ ╚══════╝    ╚═╝    ╚═╝  ╚═╝  ╚═════╝ `,
	}

	var sb strings.Builder
	sb.WriteString("\n")
	for i, line := range lines {
		style := lipgloss.NewStyle().Foreground(colors[i]).Bold(true)
		sb.WriteString(style.Render(line) + "\n")
	}
	sb.WriteString("\n")
	dimStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#888888"))
	sb.WriteString(dimStyle.Render(tr("ascii_tag")) + "\n")
	sb.WriteString(dimStyle.Render(tr("ascii_help")) + "\n\n")

	return sb.String()
}

type model struct {
	viewport    viewport.Model
	textInput   textinput.Model
	spin        spinner.Model
	manager     *WorkerManager
	logs        []string
	ready       bool
	dashboard   string
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
				m.logs = append(m.logs, lipgloss.NewStyle().Foreground(lipgloss.Color("#888888")).Render("> "+line))
				cmd := m.handleCommand(line)
				if cmd != nil {
					cmds = append(cmds, cmd)
				}
			}
			wrapStyle := lipgloss.NewStyle().Width(m.viewport.Width)
			m.viewport.SetContent(wrapStyle.Render(strings.Join(m.logs, "\n")))
			m.viewport.GotoBottom()
			return m, tea.Batch(cmds...)
		}

	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
		
		m.updateStatus() // Force dashboard string update to calculate its height

		headerHeight := lipgloss.Height(getASCIIArt())
		footerHeight := 1 // text input
		vpHeight := msg.Height - headerHeight - footerHeight
		if vpHeight < 0 {
			vpHeight = 0
		}
		
		leftPanelWidth := 45
		vpWidth := msg.Width - leftPanelWidth - 6 // left panel + margins + right panel border and padding
		if vpWidth < 10 {
			vpWidth = 10
		}

		if !m.ready {
			m.viewport = viewport.New(vpWidth, vpHeight)
			wrapStyle := lipgloss.NewStyle().Width(m.viewport.Width)
			m.viewport.SetContent(wrapStyle.Render(strings.Join(m.logs, "\n")))
			m.viewport.GotoBottom()
			m.ready = true
		} else {
			m.viewport.Width = vpWidth
			m.viewport.Height = vpHeight
			wrapStyle := lipgloss.NewStyle().Width(m.viewport.Width)
			m.viewport.SetContent(wrapStyle.Render(strings.Join(m.logs, "\n")))
		}

	case LogMsg:
		// Clean ANSI reset for empty lines
		txt := string(msg)
		if txt != "" && txt != "\n" {
			m.logs = append(m.logs, strings.TrimRight(txt, "\n"))
			// Cap at 1000 lines to prevent UI freeze
			if len(m.logs) > 1000 {
				m.logs = m.logs[len(m.logs)-1000:]
			}
			wrapStyle := lipgloss.NewStyle().Width(m.viewport.Width)
			m.viewport.SetContent(wrapStyle.Render(strings.Join(m.logs, "\n")))
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
	var dashBuilder strings.Builder
	workers := m.manager.List()
	
	if len(workers) == 0 {
		dashBuilder.WriteString(lipgloss.NewStyle().Foreground(lipgloss.Color("#888888")).Render("Nenhum robô ativo. Digite /study <ATIVO> [TIMEFRAME]"))
	} else {
		dashBuilder.WriteString(lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("#FFA500")).Render("ATIVOS EM EXECUÇÃO:"))
		dashBuilder.WriteString("\n")
		for _, w := range workers {
			status := w.StatusText
			if status == "" {
				status = "🟡 INICIALIZANDO"
			}
			uptime := time.Since(w.StartTime).Round(time.Second)
			dashBuilder.WriteString(fmt.Sprintf("  %-10s | %-5s | %-8s | %s\n", w.Symbol, w.Timeframe, uptime, status))
		}
	}
	
	m.dashboard = lipgloss.NewStyle().
		Padding(0, 1).
		Width(45). // Fixed width for left panel
		Render(dashBuilder.String())
		
	// Recalculate viewport height
	headerHeight := lipgloss.Height(getASCIIArt())
	vpHeight := m.height - headerHeight - 1
	if vpHeight < 0 {
		vpHeight = 0
	}
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

	header := getASCIIArt()

	leftPanel := lipgloss.NewStyle().
		Width(45).
		MarginRight(2).
		Render(m.dashboard)

	rightPanel := lipgloss.NewStyle().
		Border(lipgloss.NormalBorder(), false, false, false, true).
		BorderForeground(lipgloss.Color("#444444")).
		PaddingLeft(2).
		Render(m.viewport.View())

	middleSection := lipgloss.JoinHorizontal(lipgloss.Top, leftPanel, rightPanel)

	return fmt.Sprintf(
		"%s\n%s\n %s%s",
		header,
		middleSection,
		m.spin.View(),
		m.textInput.View(),
	)
}

func main() {
	for _, arg := range os.Args[1:] {
		if arg == "--version" || arg == "-v" {
			fmt.Println("MT5Bot v2.2.4")
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
