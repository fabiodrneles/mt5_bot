package main

import (
	"log"
	"os"
	"os/signal"
	"syscall"
)

// Symbols to monitor (this could be read from a config file)
var symbols = []string{"EURUSD", "GBPUSD", "WIN$N", "WDOS$N"}

func main() {
	log.Println("=== Iniciando Maestro (Golang MT5 Supervisor) ===")
	
	// Create a manager to hold all worker processes
	manager := NewWorkerManager()

	// Spawn a worker for each symbol
	for _, sym := range symbols {
		worker := NewPythonWorker(sym)
		manager.Add(worker)
		go worker.Start()
	}

	// Wait for termination signal
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	
	<-sigChan
	log.Println("Encerrando Maestro. Matando workers...")
	
	manager.StopAll()
	log.Println("Maestro finalizado com sucesso.")
}
