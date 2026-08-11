# Arquitetura — Cérebro Python (Motor Multi-Setup)

Fonte: `raw/design-spec.md`, `raw/aprofundamento.md` · Status: núcleo (implementado)

## Papel
O **Python é o cérebro**: calcula indicadores, detecta setups, gera sinais e **fala com o MetaTrader 5** (única linguagem com pacote nativo `MetaTrader5`).

## Princípios de design (definidos no aprofundamento)
1. **Stateless por ciclo**: cada execução de `on_tick` é autocontida; o estado vive em `SymbolState` (persistido/recuperado via `persistence.py`).
2. **Hydration de 100 candles**: ao iniciar, carrega ~100 candles de histórico para calcular indicadores sem esperar acumular.
3. **MT5 = fonte da verdade**: o estado real (posição, preço) sempre vem do MT5, não de cache.
4. **UTC em toda a lógica** (timestamps consistentes).
5. **Config via `.env`** — sem segredos/host no código.
6. **Logging rotativo** (5MB × 3), nunca `print()` em produção.

## Componentes atuais
| Arquivo | Papel |
|---|---|
| `indicators.py` | MME9, MME21, MME50, MM200, IFR, Bollinger, VWAP, Fibonacci (planejado) |
| `strategy.py` | FSM `SCANNING → SIGNAL_READY → IN_POSITION → WATCHING_92`; `check_setup_*` |
| `config.py` | Parâmetros centralizados (EMA9, EMA21, ATR, RVOL, RRR, saída parcial...) |
| `executor.py` | Envio de ordens ao MT5 |
| `risk_calculator.py` | Tamanho da posição (1% risco) |
| `persistence.py` | Estado persistido entre ciclos |
| `tracker.py` | Rastreamento de trades |
| `metrics.py` | (Fase 1) Estatísticas → expectância real |

## Motor multi-setup (Fase 2, planejado)
- `CONFIG_SETUPS` em `config.py` (quais setups ativos, pesos).
- `SetupSignal` (dataclass): setup, direção, preço, stop, alvo.
- `scoring.py`: filtra `RRR ≥ 1` + pontua sinais (score) — **elimina score 0, ordena desc, executa só o 1º**.
- Setups novos: 9.4, Ponto Contínuo, FFFD, DiNapoli, Rompimento Falso, IFR2, SAR.
- Filtros: MM200/MM50/IFR9/VWAP (`MTF_FILTER_ENABLED`).
- Alvos: Fibonacci 100% e 161.8%; trailing stop.

## Maestro vs Cérebro (interação)
- Maestro Go supervisiona (heartbeat, reinício); Python executa a lógica.
- Comunicação: fila/arquivo de status (o maestro NÃO bloqueia a ordem).
