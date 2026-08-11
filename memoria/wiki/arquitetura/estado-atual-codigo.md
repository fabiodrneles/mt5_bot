# Estado Atual do Código

Fonte: inspeção do repo (strategy.py, indicators.py, config.py, CHANGELOG.md)

## Estrutura de arquivos
| Arquivo | Status | Papel |
|---|---|---|
| `main.py` | implementado | Entry point principal |
| `run_bot.py` | implementado | Runner |
| `__main__.py` | implementado | `python -m` |
| `strategy.py` | implementado | FSM e detecção de setups |
| `indicators.py` | implementado | Indicadores (EMA9/21, slopes, IFR) |
| `config.py` | implementado | Parâmetros centralizados |
| `executor.py` | implementado | Ordens MT5 |
| `risk_calculator.py` | implementado | Risco 1% |
| `persistence.py` | implementado | Estado persistente |
| `tracker.py` | implementado | Rastreamento |
| `dashboard.py`/`tui.py` | implementado | UI |
| `metrics.py` | planejado | Expectância (Fase 1) |
| `orchestrator/` (Go) | planejado | Maestro (Fase 3) |

## strategy.py (FSM)
- `State` enum: `SCANNING`, `SIGNAL_READY`, `IN_POSITION`, `WATCHING_92`.
- `SymbolState`: `setup_type` = "9.1"/"9.2" (e 9.3 etc.).
- Funções `check_setup_91_buy/sell`, `check_setup_92_*`, `check_setup_93_*`.
- WATCHING_92: aguarda condições do 9.2 (correção rápida).

## indicators.py
- `ema`, `get_ema9`, `get_ema21`, `slopes` (inclinação), `virou`/`apontando`.
- `check_pullback_to_ema9` (recuo de 2+ candles → 9.3).
- `check_setup_93_buy/sell`.

## config.py (parâmetros-chave)
- `EMA_PERIOD=9`, `EMA_FILTER_PERIOD=21`.
- `PARTIAL_EXIT`: 50% / 1.00 (1x risco).
- `FLAT_TICKS`: 5.
- `ADAPTIVE_TARGET`: lookback 20.
- `ATR_PERIOD=14`, `ATR_MULTIPLIER=50`.
- `MTF_FILTER_ENABLED`: filtro multi-TF.
- `RVOL_THRESHOLD=1.15`, `RVOL_LOOKBACK=20`.
- `MIN_RISK_REWARD`: RRR mínimo.

## CHANGELOG.md (pontos L62-68)
- 9.3, MTF filter e RVOL implementados (Fase 2).
- Fases 1,2,3,5 do ROADMAP concluídas; Fase 4 desagregada.

## Observação
- Setups implementados hoje: **9.1, 9.2 (parcial), 9.3**.
- Faltam (Fase 2): **9.4, Ponto Contínuo, FFFD, DiNapoli, Rompimento Falso, IFR2, SAR**, scoring, filtros MM200/MM50/IFR9/VWAP, Fibonacci.
- Fase 3 (maestro Go) não iniciada.
