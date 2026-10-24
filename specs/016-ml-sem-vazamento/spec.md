# 016 — ML sem vazamento e com falha visível

- **Prioridade:** P2
- **Status:** Draft
- **Código afetado:** `tools/train_xgboost.py`, `tools/generate_ml_dataset.py`, `mt5bot/mentorship/ml_xgboost.py`, `.github/workflows/ml_training.yml`, `models/`
- **Resolve:** G16 · R12

## Contexto

O filtro XGBoost não está nas rotas quant, mas existe, é documentado no guia (cap. 7) e foi criticado no cap. 13: separação aleatória (vazamento temporal), métrica de acurácia e falha silenciosa. Ou o ML é feito direito, ou deve ser claramente rotulado como experimento. Esta spec faz direito.

## Estado atual (verificado)

- `train_xgboost.py:47`: `train_test_split(..., random_state=42, stratify=y)`, separação aleatória entre trades de datas misturadas.
- `ml_xgboost.py:59-134`: cinco caminhos devolvem `(True, 1.0, ...)` (aprovar) quando o ML está desligado, sem modelo, sem xgboost, sem avaliação do setup ou com erro de inferência.

## Requisitos funcionais

- **FR-1** O treino MUST usar validação **purgada com embargo** (*purged k-fold*) ou separação cronológica, nunca aleatória.
- **FR-2** O modelo MUST ser avaliado pela **expectativa dos trades aprovados** × todos os trades, além de AUC e calibração (Brier e curva de confiabilidade). O modelo só é publicado se a expectativa dos aprovados for maior com IC de 95% (bootstrap).
- **FR-3** As probabilidades MUST ser calibradas (isotônica ou Platt) antes de alimentar o Kelly (007).
- **FR-4** Cada modelo MUST ter um *model card* (`models/<nome>.md`): dados, período, métricas, data e limitações.
- **FR-5** (D14) Os caminhos de falha MUST ser distinguíveis: "ML desligado" continua aprovando sem alerta; "modelo ausente" e "erro de inferência" aprovam **com alerta visível** (painel, dashboard e 012) no modo padrão, ou **recusam** com `ml_fail_closed = true`.
- **FR-6** O status do ML por símbolo (ativo, ausente, erro, desligado) MUST aparecer na telemetria.

## Critérios de aceite

- **AC-1** Dado um *dataset* sintético com rótulo que depende do futuro de trades vizinhos, a validação purgada mostra AUC ≈ 0,5, enquanto a separação aleatória mostraria AUC alto (teste que documenta o vazamento).
- **AC-2** Dado um erro de inferência com `ml_fail_closed = false`, o trade é aprovado e o estado mostra `⚠ ML COM ERRO`.
- **AC-3** Dado o mesmo erro com `ml_fail_closed = true`, o trade é recusado.
- **AC-4** Um modelo cuja expectativa dos aprovados não é maior que a de todos os trades não é publicado pelo workflow.

## Fora de escopo

- Modelos profundos (pesados para o hardware-alvo).

## Decisões

- D14 — *fail-open* com alerta por padrão; *fail-closed* configurável.

## Referências

[López de Prado 2018] cap. 7, validação purgada; [Niculescu-Mizil & Caruana 2005] calibração; [Brier 1950] escore de Brier.
