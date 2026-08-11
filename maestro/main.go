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
	fmt.Println(ColorDim + tr("ascii_tag") + ColorReset)
	fmt.Println(ColorDim + tr("ascii_help") + ColorReset)
	fmt.Println()
}

func main() {
	// Configure logging to be dim
	log.SetFlags(log.Ltime)
	log.SetPrefix(ColorDim)

	// Remover arquivo de lock de shutdown antigo, se existir
	os.Remove("../.no_new_trades")
	os.Remove(".no_new_trades")

	currentLang = loadSavedLang()
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
					fmt.Println(ColorRed + tr("usage_add") + ColorReset)
					continue
				}
				worker := NewPythonWorker(cmd.Symbol, cmd.Timeframe)
				manager.Add(worker)
				go worker.Start()
				fmt.Printf(ColorGreen+tr("worker_started")+ColorReset+"\n", cmd.Symbol, cmd.Timeframe)

			case "stop":
				if cmd.Symbol == "" {
					fmt.Println(ColorRed + tr("usage_stop") + ColorReset)
					continue
				}
				if manager.Remove(cmd.Symbol) {
					fmt.Printf(ColorGreen+tr("worker_stopped")+ColorReset+"\n", cmd.Symbol)
				} else {
					fmt.Printf(ColorRed+tr("worker_notfound")+ColorReset+"\n", cmd.Symbol)
				}

			case "list":
				workers := manager.List()
				if len(workers) == 0 {
					fmt.Println(ColorDim + tr("no_workers") + ColorReset)
					continue
				}
				fmt.Println(ColorBold + tr("workers_active") + ColorReset)
				for _, w := range workers {
					fmt.Printf(" - %s (Timeframe: %s)\n", w.Symbol, w.Timeframe)
				}

			case "report":
				fmt.Println(ColorDim + tr("report_gen") + ColorReset)
				cmdPy := exec.Command("python", "../tracker.py", "--report")
				cmdPy.Stdout = os.Stdout
				cmdPy.Stderr = os.Stderr
				cmdPy.Run()

			case "dashboard":
				fmt.Println(ColorDim + tr("dashboard_open") + ColorReset)
				cmdPy := exec.Command("python", "../dashboard.py")
				cmdPy.Stdout = os.Stdout
				cmdPy.Stderr = os.Stderr
				cmdPy.Start()

			case "help":
				fmt.Println(ColorBold + tr("help_title") + ColorReset)
				fmt.Println(tr("help_add"))
				fmt.Println(tr("help_stop"))
				fmt.Println(tr("help_list"))
				fmt.Println(tr("help_report"))
				fmt.Println(tr("help_dashboard"))
				fmt.Println(tr("help_quit"))
				fmt.Println(tr("help_quit_cancel"))
				fmt.Println(tr("help_quit_flat"))
				fmt.Println(tr("help_quit_all"))
				fmt.Println(tr("help_lang"))

			case "idioma":
				if cmd.Symbol == "" || normalizeLang(cmd.Symbol) == "" {
					fmt.Println(ColorRed + tr("lang_invalid") + ColorReset)
					continue
				}
				currentLang = normalizeLang(cmd.Symbol)
				saveLang(currentLang)
				fmt.Println(ColorGreen + tr("lang_set") + ColorReset)

			case "quit":
				fmt.Println(ColorOrange + tr("shutdown_start") + ColorReset)

				if cmd.Action != "" {
					fmt.Printf(ColorDim+tr("action_requested")+ColorReset+"\n", cmd.Action)

					// Spawn the python shutdown manager
					shutdownCmd := exec.Command("python", "../brain/shutdown_manager.py", cmd.Action)
					shutdownCmd.Stdout = os.Stdout
					shutdownCmd.Stderr = os.Stderr
					err := shutdownCmd.Run()
					if err != nil {
						fmt.Println(ColorRed+tr("shutdown_err")+ColorReset, err)
					}
				} else {
					fmt.Println(ColorDim + tr("shutdown_none") + ColorReset)
				}

				sigChan <- syscall.SIGINT
				return

			default:
				fmt.Printf(ColorRed+tr("unknown_cmd")+ColorReset+"\n", strings.TrimSpace(line))
			}
		}
	}()

	<-sigChan
	log.Println(ColorReset + tr("msg_shutting") + ColorReset)

	manager.StopAll()
	log.Println(ColorGreen + tr("msg_done") + ColorReset)
}
