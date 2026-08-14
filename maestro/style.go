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