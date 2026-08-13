# Arquitetura — Maestro Go (Supervisor)

Fonte: `raw/design-spec.md`, `raw/aprofundamento.md` · Status: **Concluído (Fase 3 Finalizada)**

## Papel
O **maestro em Go** é o **supervisor** do sistema e o terminal principal do usuário — NÃO calcula sinais e NÃO está no caminho da ordem, focando apenas na orquestração, gestão de processos e interface de usuário.

## Responsabilidades
1. **Acompanhamento** (heartbeat): monitora o cérebro Python via pipes padrão (heartbeat a cada 1s, timeout 15s).
2. **Orquestração**: gerencia os workers isolados e o `WorkerManager` (permitindo múltiplos timeframes).
3. **Resiliência**: reinício automático do Python se cair (proteção contra crash loop: 3 tentativas com 2 min de espera).
4. **Interface Gráfica (TUI)**: Interface Split-Screen elegante baseada em `bubbletea` e `lipgloss` para visualização em tempo real.
5. **Namespaces de Logs**: Intercepta o stderr do Python e aplica color-coding via Hash (`#00FFFF`, etc) baseando-se no ativo, resolvendo problemas visuais de spam/mistura de logs.

## Por que Go
- Binário único, leve, sem runtime — roda no i3 4GB sem peso.
- Goroutines para concorrência (heartbeat + supervisão e TUI assíncrona).
- Compilação cruzada e `-ldflags "-s -w"` para EXE ultra responsivo.

## Por que NÃO Python como maestro
- Go não tem biblioteca nativa de MT5 (L288-297 do `aprofundamento.md`); Python tem o pacote `MetaTrader5`.
- Python é o "cérebro" (indica, pensa, fala com o MT5); Go é o "maestro" (supervisiona o fluxo e desenha a UI).

## No bot (estado atual)
- **O Maestro Go já está implementado e compilado em `maestro.exe`**.
- Trabalha roteando comandos (`/study`, `/add`, `/quit`, etc.) aos respectivos *Python Workers* de forma isolada e simultânea.

## Estrutura planejada (spec)
```
orchestrator/
├── go.mod
├── main.go      # bootstrap, flags CLI
├── worker.go    # spawn/monitor do Python, heartbeat
├── heartbeat.go # lógica de heartbeat 1s/3s
└── cli.go       # comandos (start/stop/status)
```
Build: `go build -ldflags "-s -w -H=windowsgui" -o mt5bot.exe`
