package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"log"
	"os/exec"
	"sync"
	"time"
	"hash/fnv"

	"github.com/charmbracelet/lipgloss"
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
	IsStudyMode bool
	StatusText string
	StartTime   time.Time

	// Crash Loop Protection (spec 6.4)
	crashFirst time.Time // instante da 1a falha dentro da janela de observacao
	crashCount int       // falhas na janela
	disabled   bool      // desligado apos 3 falhas em <2min (ate comando manual)
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

func (m *WorkerManager) Add(w *PythonWorker) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	
	for _, existing := range m.workers {
		if existing.Symbol == w.Symbol && existing.Timeframe == w.Timeframe {
			return fmt.Errorf("robô para %s %s já está em execução", w.Symbol, w.Timeframe)
		}
	}
	
	m.workers = append(m.workers, w)
	return nil
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
		StartTime: time.Now(),
		stopChan:  make(chan struct{}),
	}
}

func (w *PythonWorker) Start() {
	for {
		err := w.runProcess()
		if err != nil {
			// Crash Loop Protection (spec 6.4): 3 falhas em <2 min -> desliga
			w.mu.Lock()
			disable := w.recordFailure(time.Now())
			w.mu.Unlock()
			if disable {
				log.Printf("[MAESTRO] CRASH LOOP: worker %s desligado para proteger a banca", w.Symbol)
				return
			}
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

// recordFailure registra uma falha do processo na janela de observacao de
// 2 minutos. Retorna true quando a protecao de crash loop dispara (3 falhas).
// Chamada apenas sob w.mu. Uma vez desligado, permanece desligado.
func (w *PythonWorker) recordFailure(now time.Time) bool {
	if w.disabled {
		return true
	}
	if w.crashCount == 0 {
		w.crashFirst = now
	}
	// Janela expirou: reinicia a contagem a partir desta falha.
	if now.Sub(w.crashFirst) > 2*time.Minute {
		w.crashFirst = now
		w.crashCount = 0
	}
	w.crashCount++
	if w.crashCount >= 3 {
		w.disabled = true
		return true
	}
	return false
}

func (w *PythonWorker) IsDisabled() bool {
	w.mu.Lock()
	defer w.mu.Unlock()
	return w.disabled
}

func (w *PythonWorker) Heal() {
	w.mu.Lock()
	if !w.disabled {
		w.mu.Unlock()
		return
	}
	w.disabled = false
	w.crashCount = 0
	w.mu.Unlock()
	// Re-creates stopChan if it was closed
	w.stopChan = make(chan struct{})
	go w.Start()
}

func (w *PythonWorker) Stop() {
	close(w.stopChan)
	if w.cmd != nil && w.cmd.Process != nil {
		w.cmd.Process.Kill()
	}
}

func (w *PythonWorker) runProcess() error {
	w.cmd = exec.Command("python", "-u", "-m", "interfaces.brain_worker")
	w.cmd.Dir = ".."
	
	stdin, err := w.cmd.StdinPipe()
	if err != nil {
		return err
	}
	w.stdinPipe = bufio.NewWriter(stdin)

	stdout, err := w.cmd.StdoutPipe()
	if err != nil {
		return err
	}
	
	stderr, err := w.cmd.StderrPipe()
	if err != nil {
		return err
	}
	// Gerar uma cor deterministica para o Simbolo
	h := fnv.New32a()
	h.Write([]byte(w.Symbol))
	colors := []string{"#00FFFF", "#00FF00", "#FF00FF", "#FFFF00", "#FFA500", "#FFC0CB", "#8A2BE2", "#00BFFF"}
	colorHex := colors[int(h.Sum32())%len(colors)]
	prefixStyle := lipgloss.NewStyle().Foreground(lipgloss.Color(colorHex)).Bold(true)
	prefix := prefixStyle.Render(fmt.Sprintf("[%s|%s]", w.Symbol, w.Timeframe))

	go func() {
		scanner := bufio.NewScanner(stderr)
		for scanner.Scan() {
			text := scanner.Text()
			// Evita logs vazios repetitivos
			if text != "" && text != "\n" {
				log.Printf("%s %s", prefix, text)
			}
		}
	}()

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
	
	// Atualiza StatusText
	if st, ok := resp["state_text"]; ok && st != nil {
		if stStr, ok := st.(string); ok {
			w.mu.Lock()
			w.StatusText = stStr
			w.mu.Unlock()
		}
	}
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
			
			if timeSincePong > 15*time.Second {
				log.Printf("[MAESTRO] [%s] WATCHDOG TIMEOUT (15s sem pong). Matando processo...", w.Symbol)
				if w.cmd != nil && w.cmd.Process != nil {
					w.cmd.Process.Kill()
				}
				return
			}

			w.sendCommand(map[string]interface{}{
				"ping": true,
			})
			
			actionType := "scan"
			if w.IsStudyMode {
				actionType = "study"
			}
			// Envia o comando principal de scan ou study
			w.sendCommand(map[string]interface{}{
				"symbol":    w.Symbol,
				"action":    actionType,
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
