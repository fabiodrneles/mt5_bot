# Arquitetura — Maestro Go (Supervisor)

Fonte: `raw/design-spec.md`, `raw/aprofundamento.md` · Status: Fase 3 (planejado)

## Papel
O **maestro em Go** é o **supervisor** do sistema — NÃO calcula nada, NÃO está no caminho da ordem. Fica **fora do caminho crítico** (zero latência adicionada).

## Responsabilidades
1. **Acompanhamento** (heartbeat): monitora o cérebro Python (heartbeat a cada 1s, timeout 3s).
2. **Orquestração**: fila de ordens, confirmação de execução.
3. **Resiliência**: reinício automático do Python se cair (proteção contra crash loop: 3 tentativas com 2 min de espera).
4. **Logging rotativo**: log girado por tamanho (5MB × 3 arquivos).
5. **Graceful shutdown**: fecha janela/processo de forma limpa.

## Por que Go
- Binário único, leve, sem runtime — roda no i3 4GB sem peso.
- Goroutines para concorrência (heartbeat + supervisão) trivial.
- Compilação cruzada e `-ldflags "-s -w -H=windowsgui"` para EXE sem console.

## Por que NÃO Python como maestro
- Go não tem biblioteca nativa de MT5 (L288-297 do `aprofundamento.md`); Python tem o pacote `MetaTrader5`.
- Python é o "cérebro" (indica, pensa, fala com o MT5); Go é o "maestro" (supervisiona o fluxo).

## No bot (estado atual)
- `dashboard.py`, `tui.py` — interface de monitoramento.
- `run_bot.py`, `__main__.py` — entry points.
- Maestro Go ainda **não existe** (Fase 3).

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
