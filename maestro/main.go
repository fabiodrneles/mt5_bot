package main

import (
	"bufio"
	"fmt"
	"log"
	"os"
	"os/exec"
	"os/signal"
	"strings"
	"syscall"
)

// ANSI Colors
const (
	ColorReset  = "\033[0m"
	ColorOrange = "\033[38;5;208m"
	ColorDim    = "\033[2m"
	ColorGreen  = "\033[32m"
	ColorRed    = "\033[31m"
	ColorBold   = "\033[1m"
)

func printASCIIArt() {
	fmt.Println(ColorOrange + ColorBold)
	fmt.Println(`    __  ___  __  ______    ____        __ `)
	fmt.Println(`   /  |/  / / / / ____/   / __ )____  / /_`)
	fmt.Println(`  / /|_/ / / / /___ \    / __  / __ \/ __/`)
	fmt.Println(` / /  / / / / ____/ /   / /_/ / /_/ / /_  `)
	fmt.Println(`/_/  /_/ /_/ /_____/   /_____/\____/\__/  `)
	fmt.Println(ColorReset)
	fmt.Println(ColorDim + " Measured, disciplined execution — performance varies with market conditions." + ColorReset)
	fmt.Println(ColorDim + " Digite /help para ver os comandos disponíveis." + ColorReset)
	fmt.Println()
}

func main() {
	// Configure logging to be dim
	log.SetFlags(log.Ltime)
	log.SetPrefix(ColorDim)

	// Remover arquivo de lock de shutdown antigo, se existir
	os.Remove("../.no_new_trades")
	os.Remove(".no_new_trades")

	printASCIIArt()

	// Create a manager to hold all worker processes
	manager := NewWorkerManager()

	// Wait for termination signal
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	// Inicia a Goroutine da CLI Interativa
	go func() {
		scanner := bufio.NewScanner(os.Stdin)
		for {
			fmt.Print(ColorOrange + "mt5bot ❯ " + ColorReset)
			if !scanner.Scan() {
				break
			}
			line := strings.TrimSpace(scanner.Text())
			if line == "" {
				continue
			}

			cmd := parseCommand(line)

			switch cmd.Name {
			case "add":
				if cmd.Symbol == "" {
					fmt.Println(ColorRed + "Uso: /add <ativo> [timeframe] - Ex: /add WIN M5" + ColorReset)
					continue
				}
				worker := NewPythonWorker(cmd.Symbol, cmd.Timeframe)
				manager.Add(worker)
				go worker.Start()
				fmt.Printf(ColorGreen+"Worker iniciado para %s (%s)"+ColorReset+"\n", cmd.Symbol, cmd.Timeframe)

			case "stop":
				if cmd.Symbol == "" {
					fmt.Println(ColorRed + "Uso: /stop <ativo> - Ex: /stop WIN" + ColorReset)
					continue
				}
				if manager.Remove(cmd.Symbol) {
					fmt.Printf(ColorGreen+"Worker de %s encerrado com sucesso."+ColorReset+"\n", cmd.Symbol)
				} else {
					fmt.Printf(ColorRed+"Worker de %s nao encontrado."+ColorReset+"\n", cmd.Symbol)
				}

			case "list":
				workers := manager.List()
				if len(workers) == 0 {
					fmt.Println(ColorDim + "Nenhum worker ativo no momento." + ColorReset)
					continue
				}
				fmt.Println(ColorBold + "Workers Ativos:" + ColorReset)
				for _, w := range workers {
					fmt.Printf(" - %s (Timeframe: %s)\n", w.Symbol, w.Timeframe)
				}

			case "report":
				fmt.Println(ColorDim + "Gerando relatorio de performance..." + ColorReset)
				cmdPy := exec.Command("python", "../tracker.py", "--report")
				cmdPy.Stdout = os.Stdout
				cmdPy.Stderr = os.Stderr
				cmdPy.Run()

			case "dashboard":
				fmt.Println(ColorDim + "Abrindo Web Dashboard..." + ColorReset)
				cmdPy := exec.Command("python", "../dashboard.py")
				cmdPy.Stdout = os.Stdout
				cmdPy.Stderr = os.Stderr
				cmdPy.Start()

			case "help":
				fmt.Println(ColorBold + "Comandos disponiveis:" + ColorReset)
				fmt.Println("  /add <ativo> [tf] - Adiciona e inicia um ativo. Ex: /add WIN M5")
				fmt.Println("  /stop <ativo>     - Para a operacao em um ativo.")
				fmt.Println("  /list             - Lista os ativos operando atualmente.")
				fmt.Println("  /report           - Exibe o relatorio de performance no terminal.")
				fmt.Println("  /dashboard        - Abre o painel visual no navegador.")
				fmt.Println("  /quit             - Encerra o Maestro mantendo o estado no MT5.")
				fmt.Println("  /quit cancel-open - Cancela ordens pendentes e encerra.")
				fmt.Println("  /quit wait-flat   - Aguarda zerar posicao para desligar.")
				fmt.Println("  /quit close-all   - [PANIC] Liquida todas as posicoes a mercado.")

			case "quit":
				fmt.Println(ColorOrange + "Iniciando processo de shutdown..." + ColorReset)

				if cmd.Action != "" {
					fmt.Printf(ColorDim+"Acao solicitada: %s"+ColorReset+"\n", cmd.Action)

					// Spawn the python shutdown manager
					shutdownCmd := exec.Command("python", "../brain/shutdown_manager.py", cmd.Action)
					shutdownCmd.Stdout = os.Stdout
					shutdownCmd.Stderr = os.Stderr
					err := shutdownCmd.Run()
					if err != nil {
						fmt.Println(ColorRed+"Erro ao executar shutdown manager:"+ColorReset, err)
					}
				} else {
					fmt.Println(ColorDim + "Nenhuma acao especial. Mantendo posicoes no MT5 e encerrando local..." + ColorReset)
				}

				sigChan <- syscall.SIGINT
				return

			default:
				fmt.Printf(ColorRed+"Comando desconhecido: %s. Digite /help"+ColorReset+"\n", strings.TrimSpace(line))
			}
		}
	}()

	<-sigChan
	log.Println(ColorReset + "Encerrando Maestro. Matando workers..." + ColorReset)

	manager.StopAll()
	log.Println(ColorGreen + "Maestro finalizado com sucesso." + ColorReset)
}
