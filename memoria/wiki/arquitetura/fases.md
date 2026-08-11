# Fases do Projeto

Fonte: `raw/design-spec.md`, `ROADMAP_IMPROVEMENTS.md` · Status: mapa de implementação

## Fase 1 — Infraestrutura (ROADMAP: concluída)
- Logger rotativo (5MB × 3), timestamps UTC.
- Stateless + hydration (100 candles).
- Config via `.env`.
- `metrics.py` → expectância real.
- Heartbeat 1s/3s.
- Proteção contra crash loop (3×2min).

## Fase 2 — Motor Multi-Setup (em andamento)
- `CONFIG_SETUPS` + `SetupSignal` + `scoring.py` (RRR ≥ 1, ordenar, executar 1º).
- Novos setups: **9.4, Ponto Contínuo, FFFD, DiNapoli, Rompimento Falso, IFR2, SAR**.
- Filtros: MM200, MM50, IFR9, VWAP.
- Alvos: Fibonacci 100% / 161.8%, trailing.
- Implementado até aqui: 9.1, 9.2, 9.3, 9.4, Ponto Contínuo, FFFD, GAP, DiNapoli, Rompimento Falso, IFR2, SAR, MTF filter, RVOL.

## Fase 3 — Maestro Go (planejado)
- `orchestrator/` com `go.mod`, `main.go`, `worker.go`, `heartbeat.go`, `cli.go`.
- Supervisão (reinício, heartbeat), graceful shutdown.
- Build: `go build -ldflags "-s -w -H=windowsgui" -o mt5bot.exe`.

## ROADMAP_IMPROVEMENTS.md (estado)
- Fases 1, 2, 3, 5 concluídas conforme CHANGELOG (Fase 3 "finalizada" em 2025-02-07).
- Fase 4 (desagregada) — ver detalhes no arquivo.
- **Obs.**: há sobreposição de nomenclatura — o spec de multi-setup (Fase 2) referencia fases do ROADMAP de forma diferente. Confirmar mapeamento real ao implementar.

## Decisão de arquitetura (ADL)
- **Go = maestro** (fora do caminho da ordem), **Python = cérebro** (único que fala MT5).
- Motivo: `MetaTrader5` é Python-only; Go não tem lib nativa MT5.
