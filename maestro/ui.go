package main

import (
	"fmt"
	"math"
	"strings"
	"time"

	"github.com/charmbracelet/lipgloss"
)

// ---------------------------------------------------------------------------
// Componentes visuais do painel (v2.12): cabecalho com conta, cartoes de robo
// com telemetria (estado, rota quant, risco x limite, proximo candle, posicao)
// e ajuda formatada. Tudo derivado dos design tokens de style.go.
// ---------------------------------------------------------------------------

// commandSuggestions alimenta o autocompletar do prompt (Tab aceita).
var commandSuggestions = []string{
	"/add HK50 H4", "/add US500 D1", "/study HK50 H1", "/study US500 H1",
	"/stop ", "/list", "/report", "/dashboard", "/fix", "/help",
	"/idioma pt", "/idioma en", "/idioma es",
	"/quit", "/quit cancel-open", "/quit wait-flat", "/quit close-all",
}

func pill(text string, fg, bg lipgloss.Color) string {
	return lipgloss.NewStyle().Foreground(fg).Background(bg).Bold(true).Padding(0, 1).Render(text)
}

func money(v float64) string {
	style := lipgloss.NewStyle().Bold(true)
	switch {
	case v > 0:
		return style.Foreground(ColorGreen).Render(fmt.Sprintf("+$%.2f", v))
	case v < 0:
		return style.Foreground(ColorRed).Render(fmt.Sprintf("-$%.2f", math.Abs(v)))
	}
	return lipgloss.NewStyle().Foreground(ColorText).Render("$0.00")
}

func compactDuration(d time.Duration) string {
	d = d.Round(time.Second)
	h, m, s := int(d.Hours()), int(d.Minutes())%60, int(d.Seconds())%60
	switch {
	case h > 0:
		return fmt.Sprintf("%dh%02dm", h, m)
	case m > 0:
		return fmt.Sprintf("%dm%02ds", m, s)
	}
	return fmt.Sprintf("%ds", s)
}

// fleetAccount devolve a conta da telemetria mais recente e o P/L flutuante
// somado das posicoes do robo (um ativo conta uma vez, mesmo com 2 timeframes).
func fleetAccount(workers []*PythonWorker) (*Account, float64, int) {
	var acc *Account
	var newest time.Time
	floating, open := 0.0, 0
	seen := map[string]bool{}
	for _, w := range workers {
		_, tel, at := w.Snapshot()
		if tel.Account != nil && at.After(newest) {
			acc, newest = tel.Account, at
		}
		if seen[w.Symbol] {
			continue
		}
		seen[w.Symbol] = true
		for _, p := range tel.Positions {
			floating += p.Profit
			open++
		}
	}
	return acc, floating, open
}

// headerView: barra de marca + selos (modo, MT5, conta) + relogio, e a faixa da conta.
func (m model) headerView() string {
	workers := m.manager.List()
	acc, floating, open := fleetAccount(workers)

	brand := pill("◆ MT5BOT MAESTRO v"+botVersion(), ColorBg, ColorAmber)
	mode := pill("LIVE", ColorBg, ColorBlue)
	if m.mode == "SIMULATOR" {
		mode = pill("SIMULADOR", ColorBg, ColorAmber)
	}
	mt5 := pill("MT5 ON", ColorBg, ColorGreen)
	if m.mt5Status == "OFF" {
		mt5 = pill("MT5 OFF", ColorBg, ColorRed)
	}
	badges := brand + " " + mode + " " + mt5
	if acc != nil {
		if acc.Real {
			badges += " " + pill("CONTA REAL", ColorText, lipgloss.Color("#B4233C"))
		} else {
			badges += " " + pill("CONTA DEMO", ColorBg, ColorGreen)
		}
	}
	clock := dimStyle.Render(time.Now().Format("02/01 15:04:05") + " ")
	fill := m.width - lipgloss.Width(badges) - lipgloss.Width(clock) - 2
	if fill < 1 { // terminal estreito: o relogio sai primeiro
		clock = ""
		fill = m.width - lipgloss.Width(badges) - 2
	}
	if fill < 0 {
		fill = 0
	}
	line1 := truncateStyled(" "+badges+" "+lipgloss.NewStyle().Foreground(ColorBorder).Render(strings.Repeat("─", fill))+clock, m.width)

	label := func(s string) string { return dimStyle.Render(s) }
	value := func(s string) string { return lipgloss.NewStyle().Foreground(ColorText).Bold(true).Render(s) }
	var line2 string
	if acc == nil {
		line2 = label(" Conta: aguardando o primeiro ciclo de um robô — comece com /add HK50 H4")
	} else {
		line2 = fmt.Sprintf(" %s %s   %s %s   %s %s   %s %s   %s %s",
			label("Saldo"), value(fmt.Sprintf("$%.2f", acc.Balance)),
			label("Patrimônio"), value(fmt.Sprintf("$%.2f", acc.Equity)),
			label("Margem livre"), value(fmt.Sprintf("$%.2f", acc.MarginFree)),
			label("Flutuante"), money(floating),
			label("Posições do robô"), value(fmt.Sprint(open)))
	}
	return line1 + "\n" + truncateStyled(line2, m.width)
}

// truncateStyled corta uma linha com ANSI para nao quebrar o layout.
func truncateStyled(s string, width int) string {
	if lipgloss.Width(s) <= width {
		return s
	}
	return lipgloss.NewStyle().MaxWidth(width).Render(s)
}

// robotCards monta o painel esquerdo: um cartao por robo, com telemetria.
func robotCards(workers []*PythonWorker, width int) string {
	title := titleStyle.Render("ROBÔS") + dimStyle.Render(fmt.Sprintf("  %d ativo(s)", len(workers)))
	if len(workers) == 0 {
		cmd := lipgloss.NewStyle().Foreground(ColorAmber).Bold(true)
		return strings.Join([]string{
			titleStyle.Render("ROBÔS"), "",
			lipgloss.NewStyle().Foreground(ColorText).Render("Nenhum robô ativo."), "",
			dimStyle.Render("Comece por uma rota quant validada:"),
			"  " + cmd.Render("/add HK50 H4"),
			"  " + cmd.Render("/add US500 D1"), "",
			dimStyle.Render("Ou simule sem enviar ordens:"),
			"  " + cmd.Render("/study HK50 H1"), "",
			dimStyle.Render("Tab completa · /help lista tudo"),
		}, "\n")
	}
	lines := []string{title, dimStyle.Render(strings.Repeat("─", width))}
	for i, w := range workers {
		if i > 0 {
			lines = append(lines, dimStyle.Render(strings.Repeat("┄", width)))
		}
		lines = append(lines, workerCard(w, width)...)
	}
	return strings.Join(lines, "\n")
}

// stateLabel tira o emoji do state_text do Python ("🔵 SCANNING" -> "SCANNING").
func stateLabel(state string) string {
	state = strings.TrimSpace(state)
	if i := strings.Index(state, " "); i > 0 && len([]rune(state[:i])) == 1 {
		state = strings.TrimSpace(state[i:])
	}
	if state == "" {
		return "iniciando…"
	}
	return state
}

func workerCard(w *PythonWorker, width int) []string {
	status, tel, _ := w.Snapshot()
	badge := statusBadge(status)
	head := lipgloss.NewStyle().Foreground(lipgloss.Color(w.ColorHex)).Bold(true).Render("● "+w.Symbol) +
		" " + dimStyle.Render(w.Timeframe)
	right := renderBadge(badge, 6) + " " + dimStyle.Render(compactDuration(time.Since(w.StartTime)))
	gap := width - lipgloss.Width(head) - lipgloss.Width(right)
	if gap < 1 {
		gap = 1
	}
	lines := []string{head + strings.Repeat(" ", gap) + right}
	lines = append(lines, "  "+lipgloss.NewStyle().Foreground(badge.Color).Render(truncate(stateLabel(status), width-2)))

	amber := lipgloss.NewStyle().Foreground(ColorAmber)
	kind := amber.Render("experimental")
	switch {
	case w.IsStudyMode:
		kind = amber.Render("simulação") + dimStyle.Render(" · sem ordens")
	case tel.Quant != nil:
		kind = lipgloss.NewStyle().Foreground(ColorPurple).Bold(true).Render("★ QUANT " + tel.Quant.Setup)
	case !tel.LiveAllowed:
		// D5: setups classicos so simulam ao vivo, salvo opcao explicita.
		kind = amber.Render("experimental") + dimStyle.Render(" · só simulação (/study)")
	}
	switch {
	case strings.Contains(tel.NextClose, "fechado"):
		kind += dimStyle.Render(" · " + tel.NextClose)
	case tel.NextClose != "" && tel.NextClose != "—":
		kind += dimStyle.Render(" · candle " + tel.NextClose)
	}
	lines = append(lines, "  "+kind)

	if q := tel.Quant; q != nil && q.Risk != nil {
		if *q.Risk <= q.Limit {
			lines = append(lines, "  "+lipgloss.NewStyle().Foreground(ColorGreen).Render(fmt.Sprintf("✓ risco $%.2f", *q.Risk))+
				dimStyle.Render(fmt.Sprintf(" / limite $%.2f", q.Limit)))
		} else {
			lines = append(lines, "  "+lipgloss.NewStyle().Foreground(ColorAmber).Render(
				fmt.Sprintf("🔒 risco $%.2f > limite $%.2f", *q.Risk, q.Limit)))
		}
	}
	for _, p := range tel.Positions {
		side := lipgloss.NewStyle().Foreground(ColorGreen).Bold(true).Render("▲ BUY")
		if p.Side == "SELL" {
			side = lipgloss.NewStyle().Foreground(ColorRed).Bold(true).Render("▼ SELL")
		}
		lines = append(lines, fmt.Sprintf("  %s %.2f %s %.2f  %s", side, p.Volume, dimStyle.Render("@"), p.Open, money(p.Profit)))
	}
	for i := range lines { // nunca quebrar linha dentro do painel estreito
		lines[i] = truncateStyled(lines[i], width)
	}
	return lines
}

// helpLines formata a ajuda: comando em ambar, descricao em texto neutro.
func helpLines() []string {
	keys := []string{"help_add", "help_study", "help_stop", "help_list", "help_report", "help_dashboard",
		"help_fix", "help_lang", "help_quit", "help_quit_cancel", "help_quit_flat", "help_quit_all"}
	out := []string{lipgloss.NewStyle().Bold(true).Foreground(ColorText).Render(tr("help_title"))}
	cmd := lipgloss.NewStyle().Foreground(ColorAmber).Bold(true)
	for _, k := range keys {
		text := strings.TrimSpace(tr(k))
		if i := strings.Index(text, " - "); i > 0 {
			out = append(out, "  "+cmd.Render(fmt.Sprintf("%-20s", strings.TrimSpace(text[:i])))+" "+
				lipgloss.NewStyle().Foreground(ColorText).Render(strings.TrimSpace(text[i+3:])))
		} else {
			out = append(out, "  "+text)
		}
	}
	out = append(out, dimStyle.Render("  Tab completa o comando · Esc limpa a linha · Ctrl+C sai"))
	return out
}

// reportLines: relatorio de performance em US$ (trades reais), por setup.
func reportLines(trades []Trade) []string {
	total := computeSummary(trades)
	if !total.HasData {
		return []string{dimStyle.Render("Nenhum trade real fechado ainda.")}
	}
	out := []string{
		lipgloss.NewStyle().Bold(true).Foreground(ColorText).Render("RELATÓRIO — trades reais"),
		fmt.Sprintf("  Total: %d trades · acerto %.1f%% · resultado %s", total.Trades, total.WinRate, money(total.PnL)),
	}
	setups := []string{}
	seen := map[string]bool{}
	for _, t := range trades {
		if (t.Result == "win" || t.Result == "loss") && !seen[t.Setup] {
			seen[t.Setup] = true
			setups = append(setups, t.Setup)
		}
	}
	for _, s := range setups {
		var sub []Trade
		for _, t := range trades {
			if t.Setup == s {
				sub = append(sub, t)
			}
		}
		sm := computeSummary(sub)
		name := s
		if name == "" {
			name = "—"
		}
		out = append(out, fmt.Sprintf("  %-10s %3d trades · acerto %5.1f%% · %s", name, sm.Trades, sm.WinRate, money(sm.PnL)))
	}
	return out
}
