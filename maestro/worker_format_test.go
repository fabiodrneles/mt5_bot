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
	// A mensagem de erro deve ser pintada com o token vermelho.
	refRed := lipgloss.NewStyle().Foreground(ColorRed).Render("ERRO: MT5 desconectado")
	if !strings.Contains(out, refRed) {
		t.Fatalf("erro deveria ser colorido com ColorRed: %q", out)
	}
}