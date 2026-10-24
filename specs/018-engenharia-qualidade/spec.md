# 018 — Engenharia de qualidade avançada

- **Prioridade:** P1
- **Status:** Draft
- **Código afetado:** `pyproject.toml`, `.github/workflows/ci.yml`, `tests/`, `maestro/*_test.go`, novo `tools/perf_budget.py`
- **Resolve:** G20, G21 · R14

## Contexto

Os 60% de cobertura dizem quanto código roda nos testes, não se os testes pegam erros. No módulo que calcula o tamanho da posição, um sinal trocado custa dinheiro. Acima da média é medir a **força** dos testes onde o erro é caro e garantir que o produto continua leve no hardware-alvo (princípio 7).

## Requisitos funcionais

- **FR-1** O piso de cobertura MUST subir para 75% no total e 90% em `mt5bot/risk/` e `mt5bot/execution/quant_manager.py` (gate separado).
- **FR-2** Testes de **propriedade** (`hypothesis`, só em `dev`) MUST cobrir o dimensionamento: o volume nunca passa do máximo do símbolo, nunca é negativo, respeita o passo, e a perda até o SL nunca passa do limite de risco.
- **FR-3** Testes de **mutação** (`mutmut`) MUST rodar semanalmente (não a cada PR) sobre `mt5bot/risk/`, com meta de 80% de mutantes mortos e relatório como artefato.
- **FR-4** A checagem de tipos (`mypy --strict`) MUST cobrir `mt5bot/risk/`, `mt5bot/core/` e `mt5bot/sim/`, como gate.
- **FR-5** *Fuzzing* Go (`go test -fuzz`) SHOULD cobrir o *parser* das linhas JSON que o Maestro lê do Python.
- **FR-6** `tools/perf_budget.py` MUST medir, com o MT5 simulado e as rotas atuais: memória residente do Python (< 300 MB), memória do Maestro (< 50 MB) e tempo de um ciclo quant (< 200 ms). O CI falha se o orçamento estourar em mais de 20%.
- **FR-7** Testes de ponta a ponta MUST simular um dia de operação (abrir, gerir, fechar, kill switch, reconexão) contra o mock do MT5 com relógio controlado.

## Critérios de aceite

- **AC-1** Trocar `>` por `>=` na comparação de risco máximo é detectado pelos testes (mutante morto).
- **AC-2** O teste de propriedade encontra um contraexemplo quando se remove o arredondamento para o passo do volume.
- **AC-3** O CI publica o resultado do orçamento de desempenho no resumo do job.
- **AC-4** `mypy --strict mt5bot/risk` passa sem `# type: ignore` novos.

## Fora de escopo

- Testes contra corretora real no CI.

## Decisões

- —
