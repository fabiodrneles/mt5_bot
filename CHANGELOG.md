# Changelog

## v1.7.0 — 2026-08-11

Principais mudanças:

- **Filtros macro Fase 2.5 (`brain/indicators.py`)**:
  - `calculate_vwap` — VWAP ancorado por dia de negociação (fallback janela deslizante).
  - `check_mm50_filter` / `check_ifr9_filter` / `check_vwap_filter` — todos com fallback permissivo (`True`) e flags em `config.py` (`MM50_ENABLED`, `IFR9_ENABLED`, `VWAP_ENABLED`, `VWAP_MAX_DEVIATION_ATR`).
- **Alvos por Extensão de Fibonacci**:
  - `swing_levels` + `fib_extension_targets` (1.0x e 1.618x da amplitude) para setups que não definem alvo próprio.
- **Motor de decisão (`brain/scoring.py`)**:
  - `calcular_score` com veto (MM50/VWAP/MTF contra) e bônus (IFR9 saindo de exaustão, toque na VWAP).
  - `aplicar_scoring` com gate RRR (`MIN_RISK_REWARD`) e ordenação por score; executa apenas o 1º candidato.
- **Filtro MTF integrado ao scoring**:
  - `execution_manager` pré-computa `check_mtf_trend` uma vez por side e injeta no scoring como veto por-setup (antes era abort pós-ranking, derrubando todo o scan).
- **Modo Assistência: Posições Externas**:
  - O bot adota posições abertas manualmente no MT5, guia stop (breakeven/trailing EMA9) e alvo (parcial 50%), com reconciliação automática (`MANAGE_EXTERNAL_POSITIONS`).
- **Watchdog no Maestro Go**: `lastPong` rastreado por worker; stderr do Python roteado ao OS (`maestro/worker.go`).
- **89 testes verdes** (antes 84; +5 de MTF no scoring).
- Bump de versão para `1.7.0`.

## v1.6.0 — 2026-08-11

Principais mudanças:

- **Motor multi-setup (`brain/setups.py` + `CONFIG_SETUPS`)**: GAP, 9.1, 9.2, 9.3, 9.4, Ponto Contínuo (PC), FFFD, DiNapoli, IFR2, SAR, Rompimento Falso, com filtro macro SMA200.
- **Arquitetura Híbrida Maestro Go + Cérebro Python**: `brain/main.py` e `brain/shutdown_manager.py` como entry points dos workers; `brain/execution_manager.py` orquestra o ciclo (scoring, risco, execução).
- **Memória permanente RAG** (`memoria/`) baseada nos livros-fonte, com indexador e consulta BM25 em stdlib.
- **Spec de design** em `docs/superpowers/specs/2026-08-11-mt5-multi-setup-maestro-design.md`.
- Bump de versão para `1.6.0`.

## v1.5.2 — 2026-08-11

Principais mudanças:

- **Alinhamento Retangular Perfeito na TUI (`tui.py`)**:
  - Implementação de `_visible_len()` com Regex para ignorar caracteres não-imprimíveis de cores ANSI.
  - Correção de cálculo de largura de borda direita (`│`), garantindo caixas retangulares 100% retas no Windows PowerShell, CMD e Linux.
- Bump de versão para `1.5.2`.

## v1.5.1 — 2026-08-11


Principais mudanças:

- **Filtragem de Ativos Válidos pela Corretora (`mt5.symbol_info`)**:
  - Garantia de que ativos não oferecidos pela corretora do usuário (ex: Hantec Markets) sejam filtrados e removidos da observação sem interromper a execução.
  - As sugestões de mercado aberto agora verificam a presença do ativo no servidor do MT5 da corretora conectada antes de exibi-lo na tela.
- Bump de versão para `1.5.1`.

## v1.5.0 — 2026-08-11


Principais mudanças:

- **Horários Operacionais Inteligentes por Ativo no Fuso de Brasília (BRT)** (`config.py` / `risk_calculator.py`):
  - Suporte a janelas de negociação específicas por ativo no fuso BRT (B3 `09:15-17:15`, HK50 `22:15-12:00`, Índices EUA `10:30-17:00`, Forex `03:00-18:00`).
  - Suporte a sessões noturnas que cruzam a meia-noite (como a bolsa de Hong Kong HK50).
- **Sugestão Automática de Ativos Abertos e Cálculo de Margem**:
  - Quando todos os ativos do usuário estiverem fechados, o bot identifica mercados abertos e calcula a margem exata necessária na moeda da conta do usuário (USD/BRL/EUR).
- **Modo de Pré-Aquecimento e Análise de Contexto (Warmup Mode)**:
  - Permite ao usuário manter o bot lendo o mercado em standby para acumular histórico de EMAs e ATR antes da abertura do pregão.
- **Formatação de Terminal Clean com Cerquilhas Coloridas (`[#]`)**:
  - Emojis substituídos por cerquilhas ANSI limpas (Verde `[#]`, Amarelo `[#]`, Vermelho `[#]`).
- **Adição Dinâmica de Ativos via Console**:
  - Digitação direta do código do ativo (ex: `AUDUSD` ou `add AUDUSD`) no console interativo em execução.
- **Suíte de Testes Unitários**:
  - **55 testes unitários** passando com 100% de sucesso.
- Bump de versão para `1.5.0`.

## v1.4.0 — 2026-08-10


Principais mudanças:

- **Pipeline CI/CD com GitHub Actions (`.github/workflows/pytest.yml`)**:
  - Integração contínua automatizada para validar os 53 testes unitários a cada `git push` ou `Pull Request` em múltiplas versões de Python (3.10 a 3.13) nos SOs Ubuntu e Windows.
- **Suíte de Testes do Dashboard Web (`test_dashboard.py`)**:
  - Testes unitários cobrindo renderização HTML, formulário de configuração, processamento de formulário POST `/config/save` e endpoint JSON `/api/summary`.
- **Cobertura de Testes**:
  - 53 testes unitários cobrindo 100% dos módulos do bot com passagem em tempo de execução.
- Bump de versão para `1.4.0`.

## v1.3.0 — 2026-08-10

Principais mudanças:

- **Filtro de Tendência Multi-Timeframe (MTF)** (`indicators.py` / `strategy.py`):
  - Valida se a inclinação da EMA9/EMA21 no timeframe superior (ex: H1 quando operando em M15) confirma o sinal antes de enviar a ordem.
  - Evita entradas contra a tendência primária do mercado.
- **Setup 9.3 de Larry Williams** (`indicators.py` / `strategy.py`):
  - Implementa detecção e disparo automático para o Setup 9.3 (recuo técnico de 2 velas consecutivas mantendo a EMA9 na direção principal).
- **Filtro de Volume Relativo (RVOL)** (`indicators.py` / `strategy.py`):
  - Consulta dinamicamente `real_volume` (B3) ou `tick_volume` (Forex).
  - Bloqueia a entrada se a vela de gatilho não possuir no mínimo 15% a mais de volume em relação à média das últimas 20 velas (`RVOL_THRESHOLD = 1.15`).
- **Dashboard Web UI**:
  - Painel de configuração no navegador atualizado com controles para Filtro MTF, Setup 9.3 e RVOL.
- **Suíte de Testes Unitários**:
  - Adição de 6 novos testes em `test_phase2_strategy.py`, elevando o total para **49 testes unitários** passando com 100% de sucesso.
- Bump de versão para `1.3.0`.

## v1.2.0 — 2026-08-10


Principais mudanças:

- **Módulo de Proteção de Capital (`risk_calculator.py`)**:
  - Consulta o saldo atual da conta MT5 via `account_info().balance`.
  - **Dimensionamento Dinâmico de Lotes (*Position Sizer*)**: Calcula o volume ideal para arriscar exatamente 1.0% do saldo por operação (`config.MAX_RISK_PER_TRADE_PERCENT`).
  - **Escudo de Proteção contra Risco Absoluto (*Risk Shield*)**: Bloqueia e cancela a ordem no ato se o Stop Loss no lote mínimo exigir um risco financeiro superior a 1.5% do saldo (`config.ABSOLUTE_MAX_TRADE_RISK_PERCENT`).
- **Trava Diária de Perda Máxima (*Daily Max Loss*)**: Bloqueia a abertura de novas posições no dia se as perdas acumuladas atingirem 2.0% do saldo total da conta (`config.MAX_DAILY_LOSS_PERCENT`).
- **Filtro de Spread Máximo (*Max Spread Filter*)**: Valida o spread em tempo real e rejeita ordens se o spread ultrapassar 50 pontos (`config.MAX_SPREAD_POINTS`).
- **Breakeven Automático**: Ajusta o Stop Loss para o preço de entrada assim que a posição atinge 1x ATR de lucro a favor (`config.ENABLE_BREAKEVEN`).
- **Filtro de Janela de Horário**: Valida o horário operacional permitido (`09:15` às `16:45`).
- **Testes Unitários**: Expansão da suíte para 43 testes unitários com 100% de aprovação.
- Bump de versão para `1.2.0`.

## v1.1.0 — 2026-08-10

Principais mudanças:

- Moveu persistencia (`state.json`, `trades.json`) para `%APPDATA%/mt5bot` (Windows) ou `~/.mt5bot` (outros). Evita gravação em site-packages e problemas de permissões/corruptos.
- Implementou conversao segura para JSON em `persistence.save_states()` e `tracker._save_trades()` (converte `numpy` types, `datetime` para strings ISO, arrays para listas).
- Backup automático de arquivos de estado corrompidos: renomeia para `state.json.corrupt.<timestamp>` e inicia do zero (gera warning log).
- Shutdown interativo e seguro:
  - Default: `save-only` (nao cancela ordens/posicoes)
  - `wait-flat`: aguarda posicoes e ordens encerrarem antes de sair (com timeout configuravel)
  - `cancel-open`: cancela ordens pendentes antes de encerrar (uso explicito)
  - CLI flag: `--shutdown-action` e comandos no console (`exit`, `exit now`, `exit when flat`).
- Mensagens de log e rejeicao de sinais foram tornadas mais curtas e profissionais para auditoria automatizada.
- Testes: restauração e estabilização de `test_strategy.py`, adicionada estrategia de mock compartilhado via `conftest.py`. Suíte rodando com `pytest`.
- Bump de versão para `1.1.0` e atualização do tagline para inglês no banner.

Detalhes de implementação e notas de desenvolvedor estão em `DEVELOPER_GUIDE.md`.
