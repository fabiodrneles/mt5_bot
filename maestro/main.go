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

			parts := strings.Split(line, " ")
			cmd := strings.ToLower(parts[0])

			switch cmd {
			case "/add":
				if len(parts) < 2 {
					fmt.Println(ColorRed + "Uso: /add <ativo> [timeframe] - Ex: /add WIN M5" + ColorReset)
					continue
				}
				sym := strings.ToUpper(parts[1])
				tf := "H1" // default
				if len(parts) > 2 {
					tf = strings.ToUpper(parts[2])
				}
				worker := NewPythonWorker(sym, tf)
				manager.Add(worker)
				go worker.Start()
				fmt.Printf(ColorGreen+"Worker iniciado para %s (%s)"+ColorReset+"\n", sym, tf)

			case "/stop", "/remove":
				if len(parts) < 2 {
					fmt.Println(ColorRed + "Uso: /stop <ativo> - Ex: /stop WIN" + ColorReset)
					continue
				}
				sym := strings.ToUpper(parts[1])
				if manager.Remove(sym) {
					fmt.Printf(ColorGreen+"Worker de %s encerrado com sucesso."+ColorReset+"\n", sym)
				} else {
					fmt.Printf(ColorRed+"Worker de %s nao encontrado."+ColorReset+"\n", sym)
				}

			case "/list":
				workers := manager.List()
				if len(workers) == 0 {
					fmt.Println(ColorDim + "Nenhum worker ativo no momento." + ColorReset)
					continue
				}
				fmt.Println(ColorBold + "Workers Ativos:" + ColorReset)
				for _, w := range workers {
					fmt.Printf(" - %s (Timeframe: %s)\n", w.Symbol, w.Timeframe)
				}

			case "/report":
				fmt.Println(ColorDim + "Gerando relatorio de performance..." + ColorReset)
				cmd := exec.Command("python", "../tracker.py", "--report")
				cmd.Stdout = os.Stdout
				cmd.Stderr = os.Stderr
				cmd.Run()

			case "/dashboard":
				fmt.Println(ColorDim + "Abrindo Web Dashboard..." + ColorReset)
				cmd := exec.Command("python", "../dashboard.py")
				cmd.Stdout = os.Stdout
				cmd.Stderr = os.Stderr
				cmd.Start()

			case "/help":
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

			case "/quit", "/exit", "exit":
				fmt.Println(ColorOrange + "Iniciando processo de shutdown..." + ColorReset)
				
				if len(parts) > 1 {
					action := strings.ToLower(parts[1])
					fmt.Printf(ColorDim+"Acao solicitada: %s"+ColorReset+"\n", action)
					
					// Spawn the python shutdown manager
					shutdownCmd := exec.Command("python", "../brain/shutdown_manager.py", action)
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
				fmt.Printf(ColorRed+"Comando desconhecido: %s. Digite /help"+ColorReset+"\n", cmd)
			}
		}
	}()

	<-sigChan
	log.Println(ColorReset + "Encerrando Maestro. Matando workers..." + ColorReset)

	manager.StopAll()
	log.Println(ColorGreen + "Maestro finalizado com sucesso." + ColorReset)
}
