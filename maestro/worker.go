package main

import (
	"bufio"
	"encoding/json"
	"log"
	"os"
	"os/exec"
	"sync"
	"time"
)

type PythonWorker struct {
	Symbol    string
	Timeframe string
	cmd       *exec.Cmd
	stdinPipe *bufio.Writer
	isRunning bool
	mu        sync.Mutex
	stopChan  chan struct{}
	lastPong  time.Time
}

type WorkerManager struct {
	workers []*PythonWorker
	mu      sync.Mutex
}

func NewWorkerManager() *WorkerManager {
	return &WorkerManager{
		workers: make([]*PythonWorker, 0),
	}
}

func (m *WorkerManager) Add(w *PythonWorker) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.workers = append(m.workers, w)
}

func (m *WorkerManager) Remove(symbol string) bool {
	m.mu.Lock()
	defer m.mu.Unlock()
	for i, w := range m.workers {
		if w.Symbol == symbol {
			w.Stop()
			// Remove from slice
			m.workers = append(m.workers[:i], m.workers[i+1:]...)
			return true
		}
	}
	return false
}

func (m *WorkerManager) List() []*PythonWorker {
	m.mu.Lock()
	defer m.mu.Unlock()
	// Return a copy of the slice to avoid race conditions
	list := make([]*PythonWorker, len(m.workers))
	copy(list, m.workers)
	return list
}

func (m *WorkerManager) StopAll() {
	m.mu.Lock()
	defer m.mu.Unlock()
	for _, w := range m.workers {
		w.Stop()
	}
}

func NewPythonWorker(symbol string, timeframe string) *PythonWorker {
	if timeframe == "" {
		timeframe = "H1" // Default
	}
	return &PythonWorker{
		Symbol:    symbol,
		Timeframe: timeframe,
		stopChan:  make(chan struct{}),
	}
}

func (w *PythonWorker) Start() {
	for {
		err := w.runProcess()
		if err != nil {
			log.Printf("[MAESTRO] Worker %s caiu: %v. Reiniciando em 5 segundos...", w.Symbol, err)
		}
		
		select {
		case <-w.stopChan:
			log.Printf("[MAESTRO] Worker %s parado definitivamente.", w.Symbol)
			return
		case <-time.After(5 * time.Second):
			// loop continues, restarting process
		}
	}
}

func (w *PythonWorker) Stop() {
	close(w.stopChan)
	if w.cmd != nil && w.cmd.Process != nil {
		w.cmd.Process.Kill()
	}
}

func (w *PythonWorker) runProcess() error {
	w.cmd = exec.Command("python", "../brain/main.py")
	
	stdin, err := w.cmd.StdinPipe()
	if err != nil {
		return err
	}
	w.stdinPipe = bufio.NewWriter(stdin)

	stdout, err := w.cmd.StdoutPipe()
	if err != nil {
		return err
	}
	
	// Pass stderr to OS so we can see Python logs in the console
	w.cmd.Stderr = os.Stderr

	if err := w.cmd.Start(); err != nil {
		return err
	}

	w.isRunning = true
	w.lastPong = time.Now()
	log.Printf("[MAESTRO] Processo Python (Brain) iniciado para %s [PID: %d]", w.Symbol, w.cmd.Process.Pid)

	// Inicia a goroutine de Heartbeat (Ping) e Watchdog
	go w.heartbeatLoop()

	// Leitura do Stdout (respostas do Python)
	scanner := bufio.NewScanner(stdout)
	for scanner.Scan() {
		line := scanner.Text()
		w.handleResponse(line)
	}

	w.isRunning = false
	return w.cmd.Wait()
}

func (w *PythonWorker) handleResponse(line string) {
	var resp map[string]interface{}
	err := json.Unmarshal([]byte(line), &resp)
	if err != nil {
		log.Printf("[MAESTRO] [%s] Unmarshal error: %v | raw: %s", w.Symbol, err, line)
		return
	}

	// Tratar Pong
	if pong, ok := resp["pong"]; ok && pong.(bool) {
		// Heartbeat recebido, o worker ta vivo
		w.mu.Lock()
		w.lastPong = time.Now()
		w.mu.Unlock()
		return
	}
	
	// Printar decisoes
	log.Printf("[MAESTRO] [%s] Decision: %s", w.Symbol, line)
}

func (w *PythonWorker) heartbeatLoop() {
	ticker := time.NewTicker(1 * time.Second)
	defer ticker.Stop()

	for {
		if !w.isRunning {
			return
		}

		select {
		case <-ticker.C:
			w.mu.Lock()
			timeSincePong := time.Since(w.lastPong)
			w.mu.Unlock()
			
			if timeSincePong > 3*time.Second {
				log.Printf("[MAESTRO] [%s] WATCHDOG TIMEOUT (3s sem pong). Matando processo...", w.Symbol)
				if w.cmd != nil && w.cmd.Process != nil {
					w.cmd.Process.Kill()
				}
				return
			}

			w.sendCommand(map[string]interface{}{
				"ping": true,
			})
			
			// Envia o comando principal de scan
			w.sendCommand(map[string]interface{}{
				"symbol":    w.Symbol,
				"action":    "scan",
				"timeframe": w.Timeframe,
			})
		case <-w.stopChan:
			return
		}
	}
}

func (w *PythonWorker) sendCommand(cmd map[string]interface{}) {
	w.mu.Lock()
	defer w.mu.Unlock()

	if !w.isRunning || w.stdinPipe == nil {
		return
	}

	data, _ := json.Marshal(cmd)
	w.stdinPipe.WriteString(string(data) + "\n")
	w.stdinPipe.Flush()
}
