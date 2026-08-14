package main

import (
	"testing"

	"github.com/charmbracelet/lipgloss"
)

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