# 015 — Risco de carteira e novas rotas

- **Prioridade:** P2
- **Status:** Draft
- **Código afetado:** novo `mt5bot/risk/portfolio.py`, `mt5bot/execution/quant_manager.py`, `mt5bot/core/config.py`, `tools/quant_research/portfolio.py`
- **Resolve:** G15 · R11

## Contexto

Com uma rota, o risco é o risco da rota. Com várias, índices de ações tendem a cair juntos nas crises, e duas posições "de 2%" viram uma de quase 4%. A média do varejo ignora isso. Esta spec põe um teto no risco **agregado**, ajustado pela correlação, e define o caminho para adicionar rotas sem violar o princípio 2.

## Requisitos funcionais

- **FR-1** Antes de cada entrada, MUST ser calculado o risco aberto agregado (soma das perdas até o SL de todas as posições do MAGIC, mais a nova).
- **FR-2** (D13) A entrada MUST ser recusada se o risco agregado passar de `max_portfolio_risk_pct` (padrão: 2× o maior `max_risk_pct` entre as rotas).
- **FR-3** O risco agregado SHOULD considerar a correlação dos retornos diários dos últimos 250 dias entre os símbolos com posição (risco de carteira $\sqrt{w^\top \Sigma w}$), com a correlação recalculada no máximo uma vez por dia.
- **FR-4** O dimensionamento MAY usar **volatilidade-alvo** por rota (risco proporcional ao inverso da volatilidade recente), desligado por padrão.
- **FR-5** Uma rota nova MUST seguir o *pipeline*: pesquisa → `validate.py` aprovado (009) → `/study` por no mínimo 20 trades com *tracking error* dentro do esperado (011) → modo ao vivo com o risco mínimo. Cada etapa fica registrada na wiki.

## Critérios de aceite

- **AC-1** Dadas duas posições abertas somando 3% e o limite de 4%, uma nova entrada de 1,5% é recusada com o estado `🔴 RISCO DE CARTEIRA`.
- **AC-2** Dados dois símbolos com correlação 1, o risco de carteira é a soma; com correlação 0, é a raiz da soma dos quadrados (teste numérico).
- **AC-3** Sem posições abertas, a regra não altera o comportamento atual.
- **AC-4** O relatório da pesquisa de carteira (`tools/quant_research/portfolio.py`) mostra o *drawdown* combinado das rotas atuais.

## Fora de escopo

- Otimização de média-variância (Markowitz) e *hedge* automático.

## Decisões

- D13 — teto inicial de 2× o maior limite por rota.

## Referências

[Markowitz 1952] carteira e correlação; [López de Prado 2018] cap. 16, alocação.
