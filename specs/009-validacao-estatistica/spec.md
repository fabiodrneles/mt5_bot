# 009 — Validação estatística robusta

- **Prioridade:** P1
- **Status:** Draft
- **Código afetado:** `tools/quant_research/` (novo `validate.py`), `memoria/wiki/estrategias/`, `docs/manual/08-*.md`
- **Resolve:** G6 · R5

## Contexto

As rotas foram aprovadas com um corte IS/OOS, teste de permutação e sensibilidade de parâmetros. Isso já é mais que a média, mas três críticas do guia (cap. 13 §13.1) continuam abertas: um só corte, 3.150 combinações sem correção, e nenhum intervalo de confiança. Esta spec transforma a validação num **relatório reprodutível**, que vira o "portão" do princípio 2 da constituição.

## Requisitos funcionais

- **FR-1** `python tools/quant_research/validate.py ROTA` MUST rodar sobre o simulador de referência (spec 010) e gerar `docs/validacao/<ROTA>.md` com:
  - **Walk-forward ancorado** com no mínimo 5 janelas OOS, reotimizando só na janela IS;
  - **Deflated Sharpe Ratio** usando o número de combinações testadas na pesquisa;
  - **Probabilidade de overfitting (PBO)** por CSCV;
  - **Bootstrap** (10.000 reamostragens, semente fixa) da expectativa por trade, com intervalo de 95%;
  - **Monte Carlo** da ordem dos trades: distribuição do *drawdown* máximo (percentis 50, 95, 99);
  - Estresse de custos (1,5× e 2×) e de atraso de entrada (+1 candle).
- **FR-2** O relatório MUST terminar num veredito com critérios fixos: DSR > 0,95, PBO < 0,5, limite inferior do IC da expectativa > 0 e lucro no estresse 1,5×. Falhar um critério = **reprovada** para o modo ao vivo.
- **FR-3** As rotas atuais (PULLB HK50 H4, RSI2MR US500 D1) MUST ser revalidadas. O resultado, aprovado ou não, MUST ir para a wiki e o guia, com o mesmo destaque (princípio 3).
- **FR-4** O CI MUST rodar `validate.py` sobre um conjunto de dados sintético pequeno (passeio aleatório, ou seja, sem vantagem), e o veredito esperado é **reprovada**: um teste de sanidade de que o portão não aprova ruído.
- **FR-5** O `/add` de rota nova no modo ao vivo SHOULD exigir um relatório aprovado em `docs/validacao/`.

## Requisitos não funcionais

- **NFR-1** Só numpy/pandas; roda em menos de 10 minutos por rota no i3 com 4 GB.
- **NFR-2** Resultados determinísticos com semente fixa.

## Critérios de aceite

- **AC-1** Dado um passeio aleatório com custos, o veredito é "reprovada" (DSR baixo ou IC cruzando zero).
- **AC-2** Dada uma série sintética com vantagem plantada (por exemplo, retorno médio positivo após RSI2 < 5), o veredito é "aprovada".
- **AC-3** Duas execuções com a mesma semente geram relatórios idênticos.
- **AC-4** O relatório das duas rotas atuais existe em `docs/validacao/` e está linkado no cap. 8 do guia.

## Fora de escopo

- Otimização bayesiana de parâmetros.

## Decisões

- Se uma rota atual for reprovada, ela passa para `/study` só com aprovação do dono (decisão a tomar com o relatório na mão).

## Referências

[Bailey & López de Prado 2014] DSR; [Bailey et al. 2017] PBO/CSCV; [López de Prado 2018] cap. 11–12, *walk-forward* e validação purgada; [Efron & Tibshirani 1993] *bootstrap*.
