# Manual técnico do MT5Bot

> Versão do software documentada: **3.1.0**. Escrito para estudo acadêmico: cada capítulo descreve **como** o módulo funciona, com referência ao código, **por que** foi projetado assim, com as alternativas consideradas e as limitações conhecidas, e o **referencial teórico** que o sustenta.

## Como ler este manual

O capítulo 0 apresenta a teoria de mercado e de risco que o resto pressupõe. Os capítulos 1 a 11 seguem a ordem em que um dado atravessa o sistema: do candle que chega do MetaTrader 5 até a ordem enviada à corretora, passando pelas camadas de risco e pela observação humana. O capítulo 12 junta tudo numa visão de motores, e o 13 discute validade, limitações e ética. Os capítulos são independentes; as referências cruzadas usam o formato `capítulo §seção`. Para escolher o que ler conforme a área de estudo, veja o [Apêndice C](apendice-c-uso-academico.md).

Convenções:
- `arquivo.py:função` aponta para o código-fonte, e os caminhos são relativos à raiz do repositório.
- Fórmulas em notação matemática; $t$ indexa candles **fechados**, e $t+1$ é o candle seguinte.
- **Limitação** destaca uma fraqueza conhecida do desenho atual, com sugestão de evolução.
- As citações entre colchetes, como [Wilder 1978], remetem a [referencias.md](referencias.md).
- **Listagens** ("Listagem N.M — arquivo") são trechos reais do código, conferidos automaticamente contra o arquivo de origem; `...` marca linhas omitidas.
- **Figuras** mostram as interfaces reais renderizadas com **dados de demonstração** (conta fictícia), geradas por `tools/manual_screenshots.py`.

## Capítulos

| # | Capítulo | O que cobre |
|---|---|---|
| 0 | [Fundamentos teóricos](00-fundamentos.md) | Microestrutura, eficiência de mercado, anomalias, expectativa matemática, Kelly e ruína; da teoria às decisões |
| 1 | [Visão geral e arquitetura](01-arquitetura.md) | Contexto, componentes, processos, comunicação Go↔Python, decisões arquiteturais |
| 2 | [Maestro (orquestrador em Go)](02-maestro.md) | Elm Architecture, supervisão de workers, watchdog, crash loop, TUI |
| 3 | [Cérebro e motor de execução](03-cerebro-execucao.md) | Protocolo do worker, candles fechados, máquina de estados *stateless*, rotas quant × clássicas |
| 4 | [Indicadores técnicos](04-indicadores.md) | EMA, SMA, IFR de Wilder, ATR, Bollinger, ADX, SAR, VWAP, RVOL, Fibonacci: fórmulas e implementação |
| 5 | [Setups e estratégias](05-setups-estrategias.md) | Rotas quant (PULLB, RSI2MR), família 9.x e demais setups, filtro SMA200, motor de *scoring* |
| 6 | [Gestão de risco](06-gestao-risco.md) | Dimensionamento de posição, Kelly, travas em camadas, breakeven, trailing, confirmação de conta real |
| 7 | [Aprendizado de máquina](07-machine-learning.md) | XGBoost como filtro, *features*, *data flywheel*, supervisor adaptativo, análise crítica |
| 8 | [Metodologia de pesquisa quantitativa](08-metodologia-pesquisa.md) | Modelo de custos, simulação, dentro × fora da amostra, significância, *overfitting*, resultados |
| 9 | [Dados, telemetria e interfaces](09-dados-telemetria-interfaces.md) | Persistência, pasta do usuário, `config.toml`, telemetria, painel Quant, dashboard web |
| 10 | [Qualidade, testes e entrega](10-qualidade-entrega.md) | *Test doubles*, mutação, cobertura, CI, empacotamento, instalador, release, SDD |
| 11 | [Memória do projeto (RAG com BM25)](11-memoria-rag.md) | Recuperação lexical, parâmetros do BM25, *chunking*, por que não *embeddings* |
| 12 | [Os motores do sistema](12-motores.md) | Inventário dos motores, a vida de um trade, contratos, princípios de projeto, simuladores |
| 13 | [Validade, limitações, ética e trabalhos futuros](13-validade-limitacoes.md) | Ameaças à validade, limitações técnicas, regulação, agenda de pesquisa |
| 14 | [Pesquisa ampla de padrões](14-pesquisa-ampla.md) | 128 mil configurações em 5 timeframes, calendário, *lead-lag*, pares; artefatos de dados; FDR e DSR; engenharia da pesquisa |
| A | [Glossário](apendice-a-glossario.md) | Termos de mercado, estatística e engenharia |
| B | [Reprodutibilidade](apendice-b-reprodutibilidade.md) | Como refazer cada resultado: testes, instalador, pesquisa, RAG |
| C | [Uso acadêmico](apendice-c-uso-academico.md) | Roteiros por área, perguntas de pesquisa, estrutura de trabalho, como citar |
| — | [Referências](referencias.md) | Bibliografia |

## Arquivo único

`python tools/build_manual.py` junta todos os capítulos em `dist/MT5Bot-Guia-Tecnico-<versão>.md`, com os links entre capítulos convertidos em âncoras. Cada *release* publica esse arquivo junto com o instalador.

## Mapa rápido do código

```
maestro/                 Go: orquestrador, TUI (cap. 2)
interfaces/brain_worker  Python: processo-trabalhador por ativo (cap. 3)
mt5bot/engine/           indicadores, setups clássicos, setups quant, scoring, trailing (cap. 4-5)
mt5bot/execution/        execution_manager (clássico), quant_manager (quant), executor (ordens) (cap. 3, 6)
mt5bot/risk/             dimensionamento e travas (cap. 6)
mt5bot/mentorship/       XGBoost, simulador, otimizador, supervisor adaptativo (cap. 7)
mt5bot/data/             trades reais e virtuais, estado (cap. 9)
mt5bot/core/             config, config.toml, caminhos, telemetria, logger, shutdown (cap. 9)
tools/quant_research/    pesquisa de estratégias (cap. 8)
tools/                   quant_runner, setup_wizard, dashboard e utilitários (cap. 9)
packaging/, .github/     instalador, CI e release (cap. 10)
memoria/                 base de conhecimento com BM25 (cap. 11)
specs/                   requisitos (SDD) (cap. 10)
```

> **Aviso.** Este material tem fins educacionais. Nada aqui é recomendação de investimento; resultados de backtest não garantem resultados futuros.
