package main

import (
	"fmt"
	"os"
	"regexp"
	"strconv"
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

// rgbSequence converte "#RRGGBB" na sequência SGR truecolor (ex.: "38;2;122;162;247").
func rgbSequence(c lipgloss.Color) string {
	hex := strings.TrimPrefix(string(c), "#")
	r, _ := strconv.ParseUint(hex[0:2], 16, 8)
	g, _ := strconv.ParseUint(hex[2:4], 16, 8)
	b, _ := strconv.ParseUint(hex[4:6], 16, 8)
	return fmt.Sprintf("38;2;%d;%d;%d", r, g, b)
}

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
	if !strings.Contains(out, rgbSequence(ColorRed)) {
		t.Fatalf("erro deveria ser colorido com ColorRed: %q", out)
	}
}