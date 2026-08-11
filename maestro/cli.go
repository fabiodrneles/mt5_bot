package main

import "strings"

// Command representa um comando da CLI do Maestro, ja normalizado.
type Command struct {
	Name      string // "add" | "stop" | "list" | "report" | "dashboard" | "help" | "quit" | "unknown" | ""
	Symbol    string
	Timeframe string // default "H1" quando /add sem especificar
	Action    string // acoes suplementares: "cancel-open" | "wait-flat" | "close-all"
}

// parseCommand converte a linha digitada no terminal em um Command.
// Linhas vazias retornam Command{Name: ""} (ignoradas pelo caller).
func parseCommand(line string) Command {
	parts := strings.Fields(line)
	if len(parts) == 0 {
		return Command{}
	}

	raw := strings.ToLower(parts[0])
	switch raw {
	case "/add":
		cmd := Command{Name: "add", Timeframe: "H1"}
		if len(parts) > 1 {
			cmd.Symbol = strings.ToUpper(parts[1])
		}
		if len(parts) > 2 {
			cmd.Timeframe = strings.ToUpper(parts[2])
		}
		return cmd

	case "/stop", "/remove":
		cmd := Command{Name: "stop"}
		if len(parts) > 1 {
			cmd.Symbol = strings.ToUpper(parts[1])
		}
		return cmd

	case "/list":
		return Command{Name: "list"}

	case "/report":
		return Command{Name: "report"}

	case "/dashboard":
		return Command{Name: "dashboard"}

	case "/help":
		return Command{Name: "help"}

	case "/quit", "/exit", "exit":
		cmd := Command{Name: "quit"}
		if len(parts) > 1 {
			cmd.Action = strings.ToLower(parts[1])
		}
		return cmd

	default:
		return Command{Name: "unknown"}
	}
}