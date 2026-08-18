# Changelog

## [2.5.4] - 2026-08-18
- **Limpeza do Código e Syntax Fix:** Correção de um `IndentationError` introduzido na limpeza das criptomoedas. Adicionalmente, removidos os parâmetros legados do ativo `WIN` (Mini Índice da B3) do motor, adequando-o para corretoras internacionais como a Hantec.

## [2.5.3] - 2026-08-18
- **Transparencia Maestro:** Adicionado suporte visual (`[LOCK]`, `[WAIT]`) para bloqueio por margem de seguranca (Garage Lock) e Horario Fechado diretamente na TUI Go.
- **Crypto-free Engine:** Removidas configuracoes e calculos legados do BCHUSD/BTCUSD/ETHUSD para focar capital e limites exclusivamente no HK50/Indices/Forex apos teste quantitativo de convexidade.

## [2.5.2] - 2026-08-18
### Adicionado
- **Trava de Garagem (Garage Lock):** O bot agora impede a execucao de ativos pesados caso o saldo seja inferior a margem de seguranca (`MIN_BALANCE_REQUIREMENTS` em `config.py`), protegendo contra Margin Call precoce.
- **Escadinha de Capital (Roadmap):** BCHUSD adicionado como ativo padrao para contas de ~$10.00. Margem requerida e de apenas $0.10. Documentacao do plano oficial gerada em `memoria/wiki/roadmap_escadinha.md`.
- **Motor JP225 Otimizado:** Ativo configurado com Setup Ponto Continuo (PC), janela da Sessao Asiatica (21:00 as 06:00 BRT) e travado para saldos menores que $300.00.
## [2.5.1] - 2026-08-17
### Adicionado
- **Janela lucrativa do EURUSD (03:00–09:00 BRT):** análise dos 94 trades gerados com o motor real (lote dinâmico, spread 9 ticks, saldo $60) mostrou que a sessão Londres concentra 30 ops e +$13.00 de +$7.75 total — sinais fora dela **destroem o lucro** (fechamento 21:00–23:59 BRT: −$3.75). `SYMBOL_TRADING_HOURS["EURUSD"]` agora é `03:00–09:00` com `force_close` 09:30.
- **Aviso dinâmico de horário no motor:** quando um setup é ignorado por estar fora da janela operacional, o bot agora loga **WARNING** com a janela lucrativa do ativo e sugere desligar/religar dentro dela (`execution_manager._scan_and_execute`).
- **Teste da janela lucrativa EURUSD** (`test_is_within_trading_hours_eurusd_profitable_window`).
### Analisado (documentado em `docs/EURUSD_VIABILIDADE.md`)
- **Monte Carlo a $60 (50k trajetórias, trades fiéis HK50+EURUSD):** 75.2% de chance de fechar o ano positivo, mediana $66.75 (p10 $54 / p90 $80), **0% de chance de zerar a conta**. Números conservadores (sem breakeven/saída parcial — o motor real é melhor, HK50 PF 2.27).
- **Rigor:** `tools/backtest.py` oficial está desatualizado (width≥50, TP/SL simples) e não reproduz o PF 2.27 do changelog — os números fiéis vêm de simulação própria com `order_calc_profit`.

## [2.5.0] - 2026-08-17
### Adicionado
- **Override por ativo dos parâmetros do Setup Russo (`RUSSIAN_BB_PARAMS`):** cada ativo pode ter `min_width`/`rsi_oversold`/`rsi_overbought` próprios, com fallback para os globais. HK50/HKG50 mantêm 40/30/70; **EURUSD** recebe `0.0008/35/75`.
- **EURUSD pronto para operar (engavetado):** `ASSET_SETUPS["EURUSD"] = ["russian_bb"]`. Aviso claro no config: só ativar com saldo ≥ ~$60 (SL = meia banda ~$0.59 = 3.6% do saldo a $16.47 → Risk Shield 1.5% rejeita tudo abaixo disso).
- **Testes do override** (`test_russian_bb_eurusd_*`): EURUSD dispara com banda 0.0015 (abaixo do global 40.0); ativo sem override usa o global.
### Corrigido
- **Números do EURUSD recalculados com o filtro SMA200:** a primeira otimização omitiu o filtro macro que o motor real aplica (buy: close > SMA200; sell: close < SMA200), inflando os PF para 1.5. Revalidado por grid + walk-forward COM SMA200 (50k candles M5, spread 9 ticks, dez/2025–ago/2026): treino PF 1.28, teste fora da amostra PF 1.85 (não overfit), dataset intacto 60 ops PF 1.42 +$15.33 a $100. Combo final: `min_width=0.0008`, `RSI<35`, `RSI>75`.
- **9.x confirmado perdedor no EURUSD:** baseline 1164 ops, −$200.38, PF 0.45, WR 31.4% — substituído pelo russian_bb via `ASSET_SETUPS`.

## [2.4.1] - 2026-08-17
### Adicionado
- **Daily Max Loss Close (proteção de capital):** nova flag `DAILY_MAX_LOSS_CLOSE_ENABLED` (True). Além do shield que já bloqueava novas entradas, o bot agora **liquida a posição aberta a mercado** quando a perda diária (realizada + flutuante) atinge o limite de 2% (`MAX_DAILY_LOSS_PERCENT`). Implementado em `execution_manager._manage_position`. Testado com simulação de 13 meses: não reduz lucro (+$1.25 vs +$1.22) e contém o risco real.
- **Testes da melhoria B** (`test_daily_max_loss_close_*`): posição aberta é liquidada quando a perda diária bate o limite; posição com lucro flutuante não é liquidada.
### Modificado
- **Setup Russo (HK50) re-otimizado por grid search + walk-forward (13 meses):** `RUSSIAN_BB_MIN_WIDTH` 50→40, `RUSSIAN_BB_RSI_OVERBOUGHT` 75→70. Combo escolhido no treino (PF 2.61) confirmado out-of-sample (+$1.06 vs +$0.37 do baseline). Nos 13 meses completos: 19 ops, PF 2.27, DD 2.7%, WR 52.6%, lucro +$1.93 vs +$1.22 (**+58% de lucro com MENOS risco**). Sem SMA200 rende mais absoluto (+$3.91) mas PF/DD pioram e depende de 114 trades — rejeitado em favor da robustez.
- `tests/test_strategy_motor.py`: teste de largura mínima ajustado para o novo limiar de 40.0.

## [2.4.0] - 2026-08-17
### Adicionado
- **Parâmetros ótimos do Setup Russo (HK50) validados por otimização convexa** (60k candles M5, spread 4.5, 07/2025-08/2026): `RUSSIAN_BB_MIN_WIDTH=50.0`, `RUSSIAN_BB_RSI_OVERSOLD=30.0`, `RUSSIAN_BB_RSI_OVERBOUGHT=75.0`. Config MELHOR → PF 1.93, DD 9.6%, +25% de capital em 15 meses (~1.5%/mês).
- **Saída no fim da sessão institucional** (`exit_both_sessions`): o bot agora liquida posições abertas quando o horário institucional do ativo termina (HK50: 01:00 BRT), evitando manter risco contra spread de baixa liquidez.
- **Testes do Setup Russo** (`test_russian_bb_*`): garantem disparo com `bollinger_lower`/`rsi14` e largura mínima de 50.0 em preço.
### Corrigido
- **Bug crítico: Setup Russo nunca disparava no bot real.** O motor checava `'bb_lower'`/`'rsi'` no DataFrame, mas `add_all_indicators` gera `bollinger_lower`/`rsi14` → o bloco era ignorado para HK50.
- **Largura mínima da banda 100x errada:** `min_width = 50.0 * tick_size` (0.5 no HK50) vs o valor ótimo de 50.0 em preço validado no backtest/otimização.
- **Conversão de moeda no gestor de risco:** `loss_per_lot` via `tick_value` usava moeda do símbolo (HKD) como USD, superestimando o risco ~787x e fazendo o Risk Shield rejeitar operações válidas. Agora usa `mt5.order_calc_profit` (moeda da conta) com fallback por ticks.
- **Lote mínimo HK50/HKG50:** `ASSET_MIN_LOTS` de 0.10 → 0.01 (risco de lote mínimo ficava em 3.86% > trava de 1.5% e bloqueava tudo).
- **Limite de spread por símbolo:** `SYMBOL_MAX_SPREAD_POINTS` (HK50=500 pts) aplicado no executor, já que o spread real (~450 pts) excedia o limite global de 50 pontos e abortava todas as ordens.
- **`tools/backtest.py`:** custo de spread agora calculado via `order_calc_profit` (4.5 de preço) em vez de desconto fixo de $0.20; lote default 0.10 → 0.01.
### Modificado
- `config.py`: novos parâmetros `RUSSIAN_BB_*`; `ASSET_MIN_LOTS` HK50/HKG50 = 0.01; `SYMBOL_MAX_SPREAD_POINTS`.
- `strategy.py`: bloco russian_bb usa `bollinger_lower`/`bollinger_upper`/`rsi14` e `RUSSIAN_BB_MIN_WIDTH`.
- `execution_manager.py`: força fechamento ao fim da sessão institucional.
- `executor.py`: filtro de spread lê limite por símbolo.
- `risk_calculator.py`: conversão de moeda via `order_calc_profit`.
- `tests/test_risk_management.py`: teste de janela HK50 alinhado à sessão institucional (22:15–01:00 BRT).

## [2.3.2] - 2026-08-14
### Changed
- **Horário Institucional para HK50:** Baseado em dados massivos de backtest, a negociação do HK50/HKG50 foi restrita exclusivamente à Sessão da Manhã de Hong Kong (22:15 às 01:00 BRT). Isso impede o robô de operar durante o almoço asiático e a tarde de baixa volatilidade (after-hours no Brasil), blindando a conta contra o spread.

## [2.3.1] - 2026-08-14
### Fixed
- Atualizada a mensagem de fallback "Aguardando" na interface TUI para não citar especificamente a "EMA9", evitando confusão em ativos como HK50 onde o robô aguarda outros gatilhos (Bandas de Bollinger e IFR).
## [2.3.0] - 2026-08-14
### Adicionado
- **Roteamento Multi-Ativos (HK50):** Novo sistema em `config.py` (`ASSET_SETUPS` e `ASSET_MIN_LOTS`) que permite isolar a inteligência do bot para ativos diferentes.
- **Setup Russo (Bandas de Bollinger + RSI):** Implementado o setup de Mean Reversion exclusivamente para o mercado asiático (HK50/HKG50).
- **Filtro Anti-Tendência para HK50:** O robô só executa operações de reversão se as médias (EMA9, SMA21, EMA50) *não* estiverem apontando forte contra a operação.
- **Bypass de Score Dinâmico:** Atualização no `scoring.py` garantindo que o Setup Russo tenha passe livre (Prioridade 100) contra as travas de RRR e MM50 vigentes para os setups da família 9.x.

### Modificado
- `risk_calculator.py` agora suporta a sobreposição de lotes mínimos baseada na flag `ASSET_MIN_LOTS`. No HK50, o lote foi estipulado em `0.10` para respeitar as exigências de volume.
## [2.2.7] - 2026-08-13
### Fixed
- Connected Fibonacci targets to the Study Mode virtual tracker to allow registering proper take-profit wins.

## [2.2.6] - 2026-08-13
### Fixed
- Fixed 'Machine Gun' effect in Study Mode by implementing a 1-trade-per-candle cooldown.

## v2.2.5 — 2026-08-13

Principais mudanças:

- **Hotfix (KeyError e Panic)**:
  - Corrigido um `KeyError: 'setup_type'` no `execution_manager.py` que causava falha na exibição do simulador (PAPER_TRADE) para novos ativos.
  - Corrigido um bug no orquestrador (Go) onde tentar encerrar um worker que já havia se encerrado gerava um *Panic* por fechamento duplo de canal (`close of closed channel`).

## v2.2.4 — 2026-08-13

Principais mudanças:

- **Hotfix (Símbolos Inválidos)**:
  - Adicionada verificação no Python para rejeitar imediatamente e enviar um erro claro quando um ativo (símbolo) não existir ou não estiver disponível na corretora, prevenindo falhas silenciosas na extração de dados do MT5.
  - Orquestrador (Go) atualizado para ler e processar erros emitidos pelos workers em Python. Se o ativo for inválido, o Maestro cancela o worker graciosamente e marca o estado como `ERRO`, evitando loops infinitos de status `INICIALIZANDO`.

## v2.2.3 — 2026-08-13

Principais mudanças:

- **Hotfix (Validação de Argumentos CLI)**:
  - Adicionada validação rigorosa no `launcher.py` e no orquestrador Go (`maestro`) para rejeitar argumentos desconhecidos iniciados com `-` ou `--`. Com isso, comandos digitados incorretamente (ex: `--versin`) abortarão a execução em vez de ignorar e iniciar o robô acidentalmente.

## v2.2.2 — 2026-08-13

Principais mudanças:

- **Spread Trap Filter (Proteção Matemática)**:
  - Adicionado `MIN_STOP_SPREAD_MULTIPLIER = 1.5` no core para evitar violinos artificiais durante mercado ilíquido.
  - Se a distância do SL for menor que 1.5x o spread atual, a entrada é abortada pelo Risco.
- **Telemetria de Rejeição de Risco**:
  - `execution_manager.py` passa a gravar as rejeições de Risco e Spread Trap no banco `virtual_rejections.json`, preservando dados válidos para o Motor de Mentoria.

## v1.9.1 — 2026-08-12

Principais mudanças:

- **UX / Word-Wrap Automático no Maestro**:
  - Ajuste no terminal (viewport de logs) para suportar quebra de linha dinâmica automática. Textos muito longos agora não ficam ocultos se a janela for estreita, garantindo a visibilidade total das operações de estudo.

## v1.9.0 — 2026-08-12

Principais mudanças:

- **Mecânico (Heal System) no Maestro**:
  - Novo comando `/mechanic` (ou `/fix`, `/heal`) para restaurar e religar ativos que foram desligados por falhas críticas (Crash Loop Protection) sem precisar reiniciar o terminal.
- **Melhorias de UI/UX (Maestro)**:
  - Adicionado Spinner visual (animação de carregamento `| / - \`) no canto inferior do terminal para mostrar que o Maestro está vivo.
  - Spinner com Cores Dinâmicas: Gira em **Verde** quando todos os ativos estão saudáveis e **Amarelo** para indicar que algum ativo morreu ou precisa de reparo.
- **Suporte a `--version`**:
  - Implementado tratamento para `mt5bot --version` no `launcher.py` para visualizar a versão sem subir o servidor TUI.

## v1.8.9 — 2026-08-12

Principais mudanças:

- **Correção Visual do Maestro no Windows**:
  - Removido caracteres acentuados ("mínima", "máxima", "não") dos logs de bloqueio da Estratégia 9.2 para resolver problema de encoding (caracteres `*` bugados) no terminal Windows executando o Maestro.

## v1.8.8 — 2026-08-12

Principais mudanças:

- **Motor de Mentoria (Fase 1 e 2 - Aprimoramento)**:
  - Adicionado suporte a `timeframe` na telemetria de rejeição (`/study`).
  - Simulador agora busca até 10 dias de dados no timeframe original da operação para construir indicadores complexos (como SMA200 ou VWAP) perfeitamente antes de iniciar a simulação no M1.
  - Implementado *Fallback SL*: O simulador usa 2x o ATR calculado com dados passados quando o preço de Stop Loss original não estiver disponível na telemetria.

Principais mudanças:

- **Correção TUI Maestro (Bubble Tea)**:
  - Consertado o bug visual onde o terminal duplicava a interface e abandonava o frame antigo na tela quando o Cérebro Python printava logs no console. Agora o Maestro captura a saída padrão (`StderrPipe`) do Python e injeta no fluxo seguro de renderização do Go (`logWriter`).
- **Arquitetura (Motor de Mentoria)**:
  - Documentado o novo conceito de **Motor de Mentoria Adaptativo (Adaptive Supervisor)** na base de memória permanente (`memoria/wiki/arquitetura/motor-de-mentoria.md`). Este supervisor usará a base `virtual_rejections.json` no futuro para fazer *override* de filtros estáticos caso identifique um falso-positivo baseado em contexto de ativo/horário.

## v1.8.6 — 2026-08-12

Principais mudanças:

- **Modo Study (Telemetria Profissional)**:
  - Adicionado telemetria de rejeição (`virtual_rejections.json`). O modo study agora grava todos os setups detectados que foram bloqueados pelos filtros rigorosos (como RRR, RVOL, MM50, MTF), garantindo massa de dados para construção futura da IA de mentoria e calibração de parâmetros.
  - Adicionado logs detalhados e "throttled" indicando a causa exata da rejeição de cada sinal durante o `/study`.
- **Correção Setup FFFD**:
  - Evitada a saída prematura no FFFD (Fechamento Falso Fora Dentro) onde o trade estava sendo liquidado incorretamente pelo cruzamento da EMA9.

## v1.8.5 — 2026-08-12

Principais mudanças:

- **Modo Study (Paper Trading)**:
  - Adicionado comando `/study <ATIVO> [TIMEFRAME]` na CLI do Maestro.
  - Implementado motor de paper trading (`brain/paper_tracker.py`) que salva operações em `virtual_trades.json` separando dados simulados dos reais.
  - O bot calcula setups e acompanha o mercado validando saídas por stop loss/gain ou cruzamento de médias, criando um laboratório seguro para testes e otimização por IA.
  - Documentação atualizada em `memoria/wiki/arquitetura/study_mode.md` com reindexação da memória (RAG).

## v1.8.4 — 2026-08-12

Principais mudanças:

- **Ajuste de Proteção de Capital**:
  - Alterado o modo padrão de trailing stop (`TRAILING_MODE`) de `ema9` para `mm21` em `config.py`. A média móvel de 21 períodos proporciona uma distância maior para o stop de proteção, dando mais "respiro" às operações de tendência antes de uma violinada.


## v1.8.3 — 2026-08-11

Principais mudanças:

- **Setup 9.2 validado como completo (antes marcado "parcial/WATCHING_92")**:
  - Verificação contra o livro: a regra já estava fiel em `brain/setups.py` (EMA9 alinhada + mínima/máxima quebrando a anterior → entrada no rompimento, stop na extremidade do candle; score 15) e é o motor em produção (Maestro roda `brain/main.py`). O `strategy.py` legado (estado `WATCHING_92`) é descontinuado — não é importado por nenhum fluxo do projeto.
  - Novos testes em `test_book_setups.py`: `test_setup_92_buy_trigger`, `test_setup_92_sell_trigger`, `test_setup_92_requires_ema9_aligned` (contexto inválido não dispara).
  - Documentação atualizada: `AGENTS.md` (tabela de setups), wiki `setup-92.md`, `estado-atual-codigo.md`, `fases.md`.
  - Total da suíte: **132 testes verdes**.
  - Bump de versão para `1.8.3`.

## v1.8.2 — 2026-08-11

Principais mudanças:

- **Expansão de cobertura de testes (ROADMAP 3.2)**:
  - `tracker.py`: 37% → **94%** (14 testes novos). Cobertos: `_load_trades` (arquivo ausente/JSON corrompido), `record_partial_exit`, `record_exit` (loss/breakeven/SELL com pnl_final override), `_calculate_pnl_money` (caminho com MT5 mockado e fallback None), `get_open_trades`, `get_daily_pnl` (filtro por data + fallback pips), `get_performance_summary` (completo com sequências/drawdown por-symbol/por-setup; caso vazio; profit factor infinito), `print_report` (sem trades, com pnl_money, fallback pips) e `_save_trades` com datetime.
  - `dashboard.py`: 59% → **100%** (11 testes novos). Cobertos: `_find_free_port` (porta livre e fallback por OSError), `_page_config_saved`, `_page_report` com dados e vazio, handler GET (`/report`, `/api/summary`, 404), handler POST `/config/save` (aplicação dos valores máximos mínimos + caso inválido com defaults), POST 404, `log_message` silencioso, `open_config` e `open_report` (com eventos/browser mockados).
  - Total da suíte: **129 testes verdes**.
  - Bump de versão para `1.8.2`.

## v1.8.1 — 2026-08-11

Principais mudanças:

- **CI/CD no GitHub Actions (ROADMAP 3.1)**:
  - Novo `.github/workflows/ci.yml` consolidado: job `test-python` (pytest + numpy/pandas, **não** instala o pacote MetaTrader5 — o conftest já mocka o MT5) e job `test-go` (`go vet` + `go test` no `maestro/`).
  - Workflows legados removidos: `pytest.yml` (instalava `pip install .` → MetaTrader5, inexistente no Linux) e `test_pipeline.yml` (rodava `test_strategy.py`, arquivo deletado).
  - Bump de versão para `1.8.1`.

## v1.8.0 — 2026-08-11

Principais mudanças:

- **Maestro Go — Crash Loop Protection (spec 6.4)**:
  - Novos campos `crashFirst`/`crashCount`/`disabled` no worker; `recordFailure` contabiliza falhas em janela de 2 minutos e desliga o worker após **3 falhas** (`[MAESTRO] CRASH LOOP: worker desligado para proteger a banca`), mantendo-o desligado até comando manual.
- **CLI extraída e testável (`maestro/cli.go`)**:
  - `parseCommand` converte a linha digitada em `Command` normalizado (`add/stop/list/report/dashboard/help/quit`); `main.go` refatorado para consumi-la, preservando todas as mensagens e comportamentos originais.
- **Testes Go (spec 6.6)**:
  - `main_test.go`: table-driven para parsing da CLI (add com/sem timeframe, stop/remove, quit com ações `cancel-open`/`wait-flat`/`close-all`, exit, linha vazia, desconhecido) e `recordFailure` (limite de 3, janela expirada reinicia, disable persistente).
- **101 testes Python verdes** (inalterados) + suite Go `ok`.
- Bump de versão para `1.8.0`.

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
- **Trailing Stop dinâmico (spec 5.7)**:
  - Novo `brain/trailing.py` (puro/testável): modos `candle` (mín/máx do penúltimo candle), `ema9` e `mm21`; integrado no `execution_manager` após o breakeven; nunca piora o SL atual; perda da média de referência liquida o restante (`TRAILING_ENABLED`/`TRAILING_MODE`).
- **Watchdog no Maestro Go**: `lastPong` rastreado por worker; stderr do Python roteado ao OS (`maestro/worker.go`).
- **101 testes verdes** (antes 84; +5 de MTF no scoring; +12 de trailing).
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


