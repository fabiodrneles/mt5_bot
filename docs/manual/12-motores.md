# 12. Os motores do sistema: visão integrada

Os capítulos 2 a 11 descrevem cada parte em profundidade. Este capítulo faz o caminho inverso: apresenta o sistema como um conjunto de **motores**, isto é, componentes com uma responsabilidade única, uma entrada e uma saída bem definidas, e mostra como um trade atravessa todos eles. É o capítulo indicado para quem precisa explicar a arquitetura inteira numa apresentação ou num capítulo de metodologia.

## 12.1 Inventário dos motores

| # | Motor | Responsabilidade | Entrada → saída | Código | Detalhe |
|---|---|---|---|---|---|
| M1 | **Orquestração** | Criar, vigiar e reiniciar trabalhadores; interface | comandos do usuário → processos vivos | `maestro/worker.go`, `maestro/main.go` | cap. 2 |
| M2 | **Dados de mercado** | Buscar os 400 últimos candles **fechados** | (ativo, timeframe) → `DataFrame` OHLC | `interfaces/brain_worker.py` | cap. 3 §3.2 |
| M3 | **Indicadores** | Calcular médias, IFR, ATR, bandas, VWAP etc. de forma vetorizada | OHLC → colunas de indicadores | `mt5bot/engine/indicators.py` | cap. 4 |
| M4a | **Sinais quant** | Avaliar a regra validada da rota | `DataFrame` → `{setup, action, sl_dist, tp_dist}` ou nada | `mt5bot/engine/quant_setups.py` | cap. 5 §5.1 |
| M4b | **Sinais clássicos** | Avaliar os setups dos livros-fonte | `DataFrame` → lista de candidatos | `mt5bot/engine/strategy.py` | cap. 5 §5.2 |
| M5 | **Scoring** | Vetar por risco-retorno e ordenar candidatos | candidatos + contexto → lista ordenada | `mt5bot/engine/scoring.py` | cap. 5 §5.4 |
| M6 | **Aprendizado de máquina** | Estimar $P(\text{ganho})$ e vetar; liberar vetos por sessão | *features* → probabilidade / decisão | `mt5bot/mentorship/ml_xgboost.py`, `mt5bot/mentorship/supervisor.py` | cap. 7 |
| M7 | **Risco** | Dimensionar o lote e aplicar travas | sinal + conta → lote ou rejeição | `mt5bot/risk/risk_calculator.py`, `mt5bot/execution/quant_manager.py` | cap. 6 |
| M8 | **Execução** | Enviar, modificar e encerrar ordens; gerir a posição | decisão → ordem no MT5 | `mt5bot/execution/executor.py`, `mt5bot/execution/execution_manager.py`, `mt5bot/engine/trailing.py` | cap. 3, 6 |
| M9 | **Persistência e reconciliação** | Registrar trades e conciliá-los com os *deals* reais | eventos + MT5 → histórico | `mt5bot/data/tracker.py`, `mt5bot/data/persistence.py` | cap. 9 |
| M10 | **Simulação** | Reproduzir decisões sem dinheiro real | histórico → trades hipotéticos | `tools/quant_research/research.py`, `mt5bot/data/paper_tracker.py`, `mt5bot/mentorship/simulator.py` | cap. 7, 8 |
| M11 | **Telemetria** | Expor conta, posições, risco e relógio às interfaces | MT5 → JSON de estado | `mt5bot/core/telemetry.py` | cap. 9 |
| M12 | **Conhecimento (RAG)** | Recuperar trechos dos livros e das decisões | pergunta → blocos ranqueados | `memoria/scripts/query_memory.py` | cap. 11 |

## 12.2 A vida de um trade

O diagrama mostra um ciclo do caminho quant (HK50 H4) do começo ao fim. O caminho clássico difere nos passos 4 a 6.

```
 Maestro (M1)            Trabalhador Python                                   MT5 / corretora
 ───────────             ─────────────────────────────────────────────        ───────────────
 tick de 1 s ──ping+scan──▶ brain_worker
                           │ 1. copy_rates_from_pos(…, 1, 400)   (M2) ───────▶ histórico
                           │ 2. manage_cycle: rota quant?        (M8)
                           │ 3. há posição com o magic do robô?  (M8) ───────▶ positions_get
                           │      sim → regra de saída / nada a fazer
                           │      não ↓
                           │ 4. quant_setups.evaluate            (M3, M4a)
                           │ 5. travas: conta REAL confirmada?, perda diária,
                           │    risco no lote mínimo ≤ limite da rota,
                           │    reserva de margem 3×, stops level  (M7)
                           │ 6. place_market_order com SL/TP     (M8) ───────▶ order_send
                           │ 7. registra o trade                 (M9)
 selo "IN_POSITION" ◀─JSON─┘ 8. state_text + telemetria          (M11)
```

No caminho clássico, o passo 4 vira `StrategyScorer.evaluate_all` (M4b), seguido de `aplicar_scoring` (M5) e do veto de ML (M6); o passo 5 usa `calculate_position_size` com risco fracionário ou meio Kelly (M7); e o passo 6 envia uma ordem *stop* pendente, gerida depois com breakeven e *trailing* (M8).

**Propriedade importante:** entre um ciclo e outro, **nada** do que foi decidido fica só na memória. O ciclo seguinte redescobre a posição no passo 3. Se o processo morrer entre os passos 6 e 7, a posição continua protegida pelo SL/TP gravado no servidor, e o próximo ciclo a encontra no passo 3 e segue gerindo-a. O que pode ficar incompleto é só o registro local; o resultado real continua nos *deals* do MT5, que são a fonte da verdade (cap. 1 §1.4, cap. 3 §3.3).

## 12.3 Contratos entre motores

Motores bem separados conversam por **contratos pequenos**. Os principais:

| Fronteira | Contrato | Observação |
|---|---|---|
| M1 ↔ trabalhador | Linhas JSON: `{"ping"}`/`{"pong"}`, `{"symbol","timeframe","action"}` → `{"state_text","telemetry"}` | Testável digitando JSON no terminal (cap. 3 §3.1) |
| M2 → M3/M4 | `DataFrame` com `open, high, low, close, tick_volume, spread`, só candles fechados | A última linha é sempre o candle $t$ já fechado |
| M4a → M7/M8 | `{"setup", "action", "sl_dist", "tp_dist"}` em **distâncias** de preço | A entrada é o preço de mercado no envio; `tp_dist = None` quando a saída é por regra (RSI2MR) |
| M4b → M5 | `{"action", "trigger_price", "stop_loss", "target"?}` em **preços absolutos** | Sem `target`, o scoring projeta 1R |
| M7 → M8 | Volume normalizado ao passo do ativo, ou rejeição com motivo | A rejeição vira texto no selo do Maestro |

A diferença entre os contratos de M4a (distâncias) e M4b (preços) é deliberada: a rota quant entra **a mercado** na abertura do candle seguinte, então o preço de entrada só é conhecido no envio; os setups clássicos entram **por rompimento** de um preço conhecido no fechamento do candle.

## 12.4 Princípios de projeto que atravessam os motores

### Núcleo funcional, casca imperativa

Os motores de decisão (M3, M4, M5, `trailing.py`) são **funções puras**: recebem um `DataFrame` e devolvem um valor, sem chamar o MT5 nem gravar arquivos. Os efeitos colaterais (ler o MT5, enviar ordens, gravar JSON) ficam concentrados em poucos módulos de borda (M2, M8, M9). Isso torna o núcleo testável com dados sintéticos, sem corretora, e é o que permite a verificação de equivalência entre pesquisa e código ao vivo (cap. 8 §8.8). É a separação entre decisão e efeito defendida na literatura de projeto modular [Parnas 1972; Ousterhout 2018].

### Estratégias intercambiáveis

`quant_setups.SIGNALS` é um dicionário de nome → função com a mesma assinatura. Acrescentar uma rota é escrever uma função e registrá-la, sem mexer no motor de execução. É o padrão *Strategy* [Gamma et al. 1994] na sua forma mais simples, sem hierarquia de classes.

```python
# Listagem 12.1 — mt5bot/engine/quant_setups.py
SIGNALS = {"PULLB": signal_pullb, "RSI2MR": signal_rsi2mr}
EXITS = {"RSI2MR": exit_rsi2mr}


def evaluate(setup: str, df: pd.DataFrame, params: dict) -> Optional[dict]:
    fn = SIGNALS.get(setup)
    return fn(df, params or {}) if fn else None
```

### Ocultação de informação

O motor de risco esconde de onde vem o valor do ponto (`order_calc_profit` ou `tick_value`), a moeda da conta e o arredondamento do lote; quem chama só pergunta "quanto posso comprar?". Esse é o critério de decomposição de [Parnas 1972]: cada módulo esconde uma decisão de projeto que pode mudar.

### Falhar de forma segura, mas consciente

Cada motor tem uma política explícita para erro:

| Motor | Em caso de erro | Justificativa |
|---|---|---|
| M1 | Reinicia o trabalhador; após 3 falhas, desliga | *Let it crash* + disjuntor [Armstrong 2003; Nygard 2018] |
| M4/M5 | Sem sinal | Não operar é sempre seguro |
| M6 | **Aprova** o trade (*fail-open*) | Disponibilidade; ver crítica no cap. 7 §7.3 |
| M7 | **Rejeita** o trade (*fail-closed*) | Na dúvida sobre o risco, não opera |
| M8 | Aborta a ordem e registra o motivo | A corretora recusaria; repetir não resolve |

A assimetria entre M6 (*fail-open*) e M7 (*fail-closed*) é intencional: o ML é um refinamento opcional, enquanto o risco é uma restrição de segurança [Leveson 2011].

## 12.5 Por que tantos motores de simulação?

O repositório tem mais de um simulador, o que merece explicação e crítica:

| Simulador | Papel | Status |
|---|---|---|
| `tools/quant_research/research.py:simulate` | Pesquisa das rotas quant, com custos completos (cap. 8) | **Referência**: é o que validou as rotas |
| `mt5bot/data/paper_tracker.py` | Modo de estudo: acompanha trades virtuais em tempo real | Usado para setups não validados (D5) |
| `mt5bot/mentorship/simulator.py` | Refaz os trades **vetados** no M1 para medir o custo dos filtros | Alimenta o supervisor adaptativo (cap. 7 §7.5) |
| `tools/backtest.py`, `tools/vectorized_backtester.py`, `tools/backtest_wfo.py` | Backtests históricos dos setups clássicos | Ferramentas exploratórias anteriores à pesquisa quant |

**Análise crítica.** Simuladores diferentes podem divergir em detalhes (custos, ordem de SL e TP no mesmo candle, *gaps*), e uma estratégia "lucrativa" num pode não ser no outro. O projeto mitiga isso tratando **um único** simulador como referência para decisões de ir ao vivo, e verificando a equivalência entre ele e o código de produção. Uma evolução natural seria consolidar os simuladores exploratórios sobre o mesmo núcleo de `research.py`.

## 12.6 Referencial teórico

[Parnas 1972] decomposição por ocultação de informação; [Ousterhout 2018] módulos profundos e interfaces pequenas; [Gamma et al. 1994] padrão *Strategy*; [Armstrong 2003] supervisão; [Nygard 2018] disjuntor; [Leveson 2011] restrições de segurança; [Bass, Clements & Kazman 2012] arquitetura e atributos de qualidade.
