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
	case strings.Contains(upper, "LOCK"),
		strings.Contains(upper, "BLOQUEADO"):
		return StatusBadge{Label: "LOCK", Color: ColorDim}
	case strings.Contains(upper, "REJEITADO"),
		strings.Contains(upper, "FECHADO"),
		strings.Contains(upper, "MAX LOSS"):
		return StatusBadge{Label: "WAIT", Color: ColorAmber}
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