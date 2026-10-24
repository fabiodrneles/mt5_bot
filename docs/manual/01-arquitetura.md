# 1. Visão geral e arquitetura

## 1.1 Problema e restrições

O MT5Bot automatiza decisões de compra e venda num terminal **MetaTrader 5** (MT5) a partir de regras técnicas e quantitativas. As restrições de projeto, registradas na [constituição](../../specs/constitution.md), moldam toda a arquitetura:

1. **Capital primeiro:** toda posição tem stop gravado no servidor da corretora, e o robô só mexe no que identifica como seu (*magic number*).
2. **Só opera ao vivo o que foi validado** fora da amostra (cap. 8).
3. **Hardware modesto:** i3 de 4ª geração com 4 GB de RAM.
4. **Instalável por leigos:** sem git, Python ou Go no caminho principal (cap. 10).
5. **Integração única e oficial com o MT5:** a biblioteca `MetaTrader5` para Python, que existe só para Windows.

## 1.2 Componentes

```
                ┌─────────────────────────────────────────────────────────────┐
  Usuário ─────▶│  Interfaces: Maestro (TUI Go) · Painel Quant · Dashboard web │
                └───────────────┬──────────────────────────┬──────────────────┘
                                │ JSON por stdin/stdout    │ lê telemetria
                ┌───────────────▼──────────────┐   ┌───────▼─────────────────┐
                │ Cérebro: brain_worker (1 por │   │ telemetry.py (conta,     │
                │ ativo) → execution_manager   │   │ posições, risco, relógio)│
                │   ├─ rota quant → quant_mgr  │   └───────┬─────────────────┘
                │   └─ clássico → strategy +   │           │
                │      scoring + ML + risco    │           │
                └───────────────┬──────────────┘           │
                                │ executor (ordens)        │
                ┌───────────────▼──────────────────────────▼──────────────────┐
                │ Biblioteca MetaTrader5 (IPC com o terminal) → corretora      │
                └─────────────────────────────────────────────────────────────┘
```

| Camada | Responsabilidade | Código |
|---|---|---|
| Orquestração | Ciclo de vida dos trabalhadores, interface interativa | `maestro/` |
| Cérebro | Um processo por ativo: lê candles, decide, executa | `interfaces/brain_worker.py`, `mt5bot/execution/` |
| Estratégia | Indicadores, sinais, priorização | `mt5bot/engine/` |
| Risco | Tamanho da posição e travas | `mt5bot/risk/`, `quant_manager.py` |
| Aprendizado | Filtro XGBoost e supervisor adaptativo | `mt5bot/mentorship/` |
| Dados | Histórico de trades, estado, configuração do usuário | `mt5bot/data/`, `mt5bot/core/` |
| Observação | Telemetria e as três interfaces | `mt5bot/core/telemetry.py`, `tools/quant_runner.py`, `interfaces/dashboard.py` |

## 1.3 Modelo de processos e comunicação

O Maestro (Go) inicia **um processo Python por ativo/timeframe** (`maestro/worker.go:runProcess`) e conversa com ele por **linhas JSON** em stdin/stdout: um objeto por linha, no estilo JSON Lines. A cada segundo envia `{"ping": true}` e `{"symbol", "action", "timeframe"}`; o trabalhador responde `{"pong": true}` e `{"symbol", "state_text", "telemetry"}`. Os logs do Python vão para stderr, que o Maestro mostra no painel de eventos.

**Por que processos separados, e não threads ou um processo único?**
- **Isolamento de falhas:** um erro num ativo (dados corrompidos, exceção) derruba só aquele trabalhador, e o supervisor o reinicia (cap. 2). É o princípio do *let it crash* com supervisão, da tradição Erlang/OTP [Armstrong 2003].
- **Paralelismo real:** o GIL do CPython impede paralelismo de CPU entre threads; processos contornam isso.
- **Linguagem certa para cada papel:** Go oferece concorrência leve (goroutines) e um binário único para a TUI; Python concentra o ecossistema numérico (pandas, NumPy, XGBoost) e a única biblioteca oficial do MT5.

**Por que JSON por stdin/stdout, e não HTTP, gRPC ou filas?** O canal é local, ponto a ponto e com uma mensagem por vez: o *pipes and filters* clássico [Hohpe & Woolf 2003] já basta, sem portas abertas, sem dependências e com depuração trivial (dá para "conversar" com o trabalhador digitando JSON no terminal; ver cap. 3 §3.1). gRPC traria contratos tipados ao custo de geração de código e de uma dependência pesada, sem benefício para um único consumidor.

## 1.4 Arquitetura *stateless*

Nenhum estado de negociação crítico vive só na memória. A cada ciclo o cérebro **relê do MT5** se há posição ou ordem pendente do robô e decide a partir disso (cap. 3 §3.3). Consequências:
- Reiniciar o computador ou o processo não perde nada: o estado verdadeiro está na corretora.
- O stop e o alvo ficam gravados **no servidor** (SL/TP da ordem): a proteção continua mesmo com o PC desligado.
- O histórico local (`trades.json`) é reconciliado com os *deals* reais do MT5, que são a fonte da verdade do lucro (cap. 9).

A ideia é tratar o sistema externo como a fonte da verdade e o estado local como cache derivável, a mesma lógica de sistemas orientados a log e de *event sourcing* discutida em [Kleppmann 2017].

## 1.5 Dois caminhos de decisão

O `execution_manager.manage_cycle` despacha cada ciclo para um de dois caminhos (cap. 3):

| | Caminho **quant** | Caminho **clássico** |
|---|---|---|
| Quando | O par (ativo, timeframe) está em `config.QUANT_ROUTES` | Os demais |
| Regras | Validadas fora da amostra (cap. 8) | Setups dos livros-fonte (cap. 5) |
| Filtros | Nenhum além da regra validada | MTF, RVOL, *scoring*, XGBoost |
| Ao vivo | Sim (com confirmação de conta real) | Só com `allow_unvalidated_live = true` (decisão D5) |

A separação existe porque **um resultado validado só vale para a regra exata que foi testada**: acrescentar filtros não testados a uma regra validada produz outra estratégia, sem validação. Esse cuidado é central na literatura de *backtest overfitting* [Bailey et al. 2014].

## 1.6 Decisões arquiteturais (registro)

As decisões estão em [`specs/ANALYSIS.md` §7](../../specs/ANALYSIS.md). As que afetam a arquitetura:

| Decisão | Escolha | Alternativas | Razão |
|---|---|---|---|
| Integração com MT5 | Lib Python oficial | MQL5 nativo; ponte via sockets | Ecossistema de dados do Python; MQL5 isola o código do resto das ferramentas |
| Orquestrador | Go + Bubble Tea | Python (curses/Textual) | Binário único, concorrência simples, TUI madura |
| macOS/Linux (D1) | Rodar tudo dentro do Wine | Nativo (impossível: a lib não existe); só dashboard | Único caminho que opera de verdade |
| Instalador (D2) | Inno Setup + Python embutido | PyInstaller; MSIX | Atalhos e desinstalador nativos; o Python embutido não conflita com o do usuário |
| Setups não validados (D5) | Só simulação por padrão | Ao vivo | Histórico real negativo (−$33,18 em 7 trades) |

## 1.7 Referencial teórico

- Isolamento por processos e supervisão: [Armstrong 2003].
- Integração por mensagens e *pipes and filters*: [Hohpe & Woolf 2003].
- Estado derivado de uma fonte da verdade externa: [Kleppmann 2017].
- Atributos de qualidade e decisões arquiteturais: [Bass, Clements & Kazman 2012].
