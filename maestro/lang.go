package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
)

type Lang string

const (
	LangDefault Lang = "pt"
	LangPt      Lang = "pt"
	LangEn      Lang = "en"
	LangEs      Lang = "es"
)

// currentLang e o idioma ativo da interface (carregado no start, mutavel via /idioma).
var currentLang = LangDefault

var translations = map[Lang]map[string]string{
	LangPt: {
		"usage_add":        "Uso: /add <ativo> [timeframe] - Ex: /add WIN M5",
		"worker_started":   "Worker iniciado para %s (%s)",
		"usage_stop":       "Uso: /stop <ativo> - Ex: /stop WIN",
		"worker_stopped":   "Worker de %s encerrado com sucesso.",
		"worker_notfound":  "Worker de %s nao encontrado.",
		"no_workers":       "Nenhum worker ativo no momento.",
		"workers_active":   "Workers Ativos:",
		"report_gen":       "Gerando relatorio de performance...",
		"dashboard_open":   "Abrindo Web Dashboard...",
		"help_title":       "Comandos disponiveis:",
		"help_add":         "  /add <ativo> [tf] - Adiciona e inicia um ativo. Ex: /add WIN M5",
		"help_stop":        "  /stop <ativo>     - Para a operacao em um ativo.",
		"help_list":        "  /list             - Lista os ativos operando atualmente.",
		"help_report":      "  /report           - Exibe o relatorio de performance no terminal.",
		"help_dashboard":   "  /dashboard        - Abre o painel visual no navegador.",
		"help_quit":        "  /quit             - Encerra o Maestro mantendo o estado no MT5.",
		"help_quit_cancel": "  /quit cancel-open - Cancela ordens pendentes e encerra.",
		"help_quit_flat":   "  /quit wait-flat   - Aguarda zerar posicao para desligar.",
		"help_quit_all":    "  /quit close-all   - [PANIC] Liquida todas as posicoes a mercado.",
		"help_lang":        "  /idioma <pt|en|es> - Troca o idioma da interface.",
		"shutdown_start":   "Iniciando processo de shutdown...",
		"action_requested": "Acao solicitada: %s",
		"shutdown_err":     "Erro ao executar shutdown manager:",
		"shutdown_none":    "Nenhuma acao especial. Mantendo posicoes no MT5 e encerrando local...",
		"unknown_cmd":      "Comando desconhecido: %s. Digite /help",
		"msg_shutting":     "Encerrando Maestro. Matando workers...",
		"msg_done":         "Maestro finalizado com sucesso.",
		"ascii_tag":        " Measured, disciplined execution — performance varies with market conditions.",
		"ascii_help":       " Digite /help para ver os comandos disponíveis.",
		"lang_set":         "Idioma alterado com sucesso.",
		"lang_invalid":     "Idioma invalido. Uso: /idioma <pt|en|es>",
	},
	LangEn: {
		"usage_add":        "Usage: /add <symbol> [timeframe] - Ex: /add WIN M5",
		"worker_started":   "Worker started for %s (%s)",
		"usage_stop":       "Usage: /stop <symbol> - Ex: /stop WIN",
		"worker_stopped":   "Worker %s stopped successfully.",
		"worker_notfound":  "Worker %s not found.",
		"no_workers":       "No active workers at the moment.",
		"workers_active":   "Active Workers:",
		"report_gen":       "Generating performance report...",
		"dashboard_open":   "Opening Web Dashboard...",
		"help_title":       "Available commands:",
		"help_add":         "  /add <symbol> [tf] - Adds and starts a symbol. Ex: /add WIN M5",
		"help_stop":        "  /stop <symbol>     - Stops trading on a symbol.",
		"help_list":        "  /list             - Lists currently running symbols.",
		"help_report":      "  /report           - Shows the performance report in the terminal.",
		"help_dashboard":   "  /dashboard        - Opens the visual dashboard in the browser.",
		"help_quit":        "  /quit             - Shuts down Maestro keeping MT5 state.",
		"help_quit_cancel": "  /quit cancel-open - Cancels pending orders and shuts down.",
		"help_quit_flat":   "  /quit wait-flat   - Waits for a flat position before shutdown.",
		"help_quit_all":    "  /quit close-all   - [PANIC] Closes all positions at market.",
		"help_lang":        "  /idioma <pt|en|es> - Changes the interface language.",
		"shutdown_start":   "Starting shutdown process...",
		"action_requested": "Requested action: %s",
		"shutdown_err":     "Error running shutdown manager:",
		"shutdown_none":    "No special action. Keeping MT5 positions and shutting down locally...",
		"unknown_cmd":      "Unknown command: %s. Type /help",
		"msg_shutting":     "Shutting down Maestro. Killing workers...",
		"msg_done":         "Maestro finished successfully.",
		"ascii_tag":        " Measured, disciplined execution — performance varies with market conditions.",
		"ascii_help":       " Type /help to see available commands.",
		"lang_set":         "Language changed successfully.",
		"lang_invalid":     "Invalid language. Usage: /idioma <pt|en|es>",
	},
	LangEs: {
		"usage_add":        "Uso: /add <simbolo> [timeframe] - Ej: /add WIN M5",
		"worker_started":   "Worker iniciado para %s (%s)",
		"usage_stop":       "Uso: /stop <simbolo> - Ej: /stop WIN",
		"worker_stopped":   "Worker de %s detenido con exito.",
		"worker_notfound":  "Worker de %s no encontrado.",
		"no_workers":       "Ningun worker activo en este momento.",
		"workers_active":   "Workers Activos:",
		"report_gen":       "Generando informe de rendimiento...",
		"dashboard_open":   "Abriendo Dashboard Web...",
		"help_title":       "Comandos disponibles:",
		"help_add":         "  /add <simbolo> [tf] - Anade e inicia un simbolo. Ej: /add WIN M5",
		"help_stop":        "  /stop <simbolo>     - Detiene la operacion en un simbolo.",
		"help_list":        "  /list             - Lista los simbolos en operacion.",
		"help_report":      "  /report           - Muestra el informe de rendimiento en el terminal.",
		"help_dashboard":   "  /dashboard        - Abre el panel visual en el navegador.",
		"help_quit":        "  /quit             - Cierra Maestro manteniendo el estado en MT5.",
		"help_quit_cancel": "  /quit cancel-open - Cancela ordenes pendientes y cierra.",
		"help_quit_flat":   "  /quit wait-flat   - Espera a posicion plana antes de apagar.",
		"help_quit_all":    "  /quit close-all   - [PANIC] Liquida todas las posiciones a mercado.",
		"help_lang":        "  /idioma <pt|en|es> - Cambia el idioma de la interfaz.",
		"shutdown_start":   "Iniciando proceso de cierre...",
		"action_requested": "Accion solicitada: %s",
		"shutdown_err":     "Error al ejecutar gestor de cierre:",
		"shutdown_none":    "Sin accion especial. Manteniendo posiciones en MT5 y cerrando local...",
		"unknown_cmd":      "Comando desconocido: %s. Escriba /help",
		"msg_shutting":     "Cerrando Maestro. Matando workers...",
		"msg_done":         "Maestro finalizado con exito.",
		"ascii_tag":        " Medicion, disciplina y ejecucion — el rendimiento varia con las condiciones del mercado.",
		"ascii_help":       " Escriba /help para ver los comandos disponibles.",
		"lang_set":         "Idioma cambiado con exito.",
		"lang_invalid":     "Idioma invalido. Uso: /idioma <pt|en|es>",
	},
}

func tr(key string) string {
	if set, ok := translations[currentLang]; ok {
		if val, ok := set[key]; ok {
			return val
		}
	}
	return translations[LangDefault][key]
}

func normalizeLang(s string) Lang {
	switch strings.ToLower(strings.TrimSpace(s)) {
	case "pt", "pt-br", "portugues", "portuguese":
		return LangPt
	case "en", "ingles", "english":
		return LangEn
	case "es", "espanol", "spanish":
		return LangEs
	default:
		return ""
	}
}

// langFilePath retorna o caminho do arquivo de idioma em %APPDATA%/mt5bot
// (mesma convencao do persistence.py do cerebro Python).
func langFilePath() string {
	appdata := os.Getenv("APPDATA")
	if appdata == "" {
		appdata = os.Getenv("LOCALAPPDATA")
	}
	if appdata != "" {
		return filepath.Join(appdata, "mt5bot", "lang.json")
	}
	home, err := os.UserHomeDir()
	if err != nil {
		home = "."
	}
	return filepath.Join(home, ".mt5bot", "lang.json")
}

func loadSavedLang() Lang {
	data, err := os.ReadFile(langFilePath())
	if err != nil {
		return LangDefault
	}
	var stored struct {
		Lang string `json:"lang"`
	}
	if json.Unmarshal(data, &stored) != nil {
		return LangDefault
	}
	if l := normalizeLang(stored.Lang); l != "" {
		return l
	}
	return LangDefault
}

func saveLang(l Lang) {
	path := langFilePath()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return
	}
	payload, err := json.Marshal(map[string]string{"lang": string(l)})
	if err != nil {
		return
	}
	_ = os.WriteFile(path, payload, 0o644)
}
