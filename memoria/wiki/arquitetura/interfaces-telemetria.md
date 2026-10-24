# Interfaces e telemetria (v2.12.0)

Três interfaces, uma fonte de dados: `mt5bot/core/telemetry.py`.

| Interface | Comando | Para quê |
|---|---|---|
| Painel do Modo Quant | `bot.bat quant` | Operar as rotas validadas; painel colorido no console (ANSI 256 cores) |
| Maestro (Go, TUI) | `mt5bot.bat` | Vários robôs em paralelo, `/study`, `/add`, `/quit` |
| Dashboard web | `bot.bat dashboard` ou `/dashboard` | Visão ao vivo no navegador, curva de patrimônio, histórico em US$ |

## Telemetria
- `account_snapshot()`: login, REAL/DEMO, saldo, patrimônio e margem livre.
- `bot_positions()`: só as posições com o MAGIC do bot; as manuais ficam de fora.
- `route_risk()`: perda no SL com o lote mínimo × o limite da rota (`max_risk_pct` ou `QUANT_MAX_RISK_PCT`).
- `server_now()` e `next_close_text()`: relógio do servidor estimado pelo tick mais recente (cripto 24/7 serve de relógio no fim de semana). Detecta "mercado fechado".
- `trade_stats()` e `group_stats()`: estatísticas em US$ a partir do `pnl_money`, que é o lucro real do MT5.

O `interfaces/brain_worker.py` anexa `telemetry` a cada resposta ao Maestro. O `maestro/worker.go` guarda essa telemetria em `PythonWorker.telemetry`, e o `maestro/ui.go` desenha o cabeçalho e os cartões.

## Decisões
- O dashboard antigo editava a configuração só na memória do próprio processo, sem efeito nos robôs. A configuração agora é **somente leitura** na web, e a fonte da verdade continua sendo o `config.py`.
- O `/quit close-all`, o `wait-flat` e o `cancel-open` agem **só no que é do robô** (MAGIC), igual ao `bot.bat panic`.
- No Maestro, Esc limpa a linha e não encerra mais o programa (antes fechava por acidente).
