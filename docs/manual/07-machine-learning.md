# 7. Aprendizado de máquina

O ML entra como **filtro de veto** sobre setups já sinalizados, e não como gerador de sinais. Essa escolha limita o estrago de um modelo ruim: no pior caso ele deixa passar ou bloqueia um sinal que as regras já haviam encontrado.

## 7.1 Modelo: XGBoost

`mt5bot/mentorship/ml_xgboost.py:MLSupervisor` carrega um classificador por ativo (`models/mt5bot_xgboost_<ATIVO>_v2.json`) e estima $p = P(\text{trade vencedor} \mid x)$.

**XGBoost** [Chen & Guestrin 2016] é *gradient boosting* de árvores de decisão [Friedman 2001]: o modelo é uma soma de árvores $\hat y = \sum_{k=1}^K f_k(x)$, em que cada nova árvore ajusta o gradiente da perda das anteriores. A função objetivo inclui regularização da complexidade das árvores, $\Omega(f) = \gamma T + \tfrac{1}{2}\lambda\lVert w\rVert^2$.

**Por que XGBoost?**
- **Dados tabulares pequenos e heterogêneos:** em dados tabulares, árvores com *boosting* costumam superar redes neurais e exigem pouco pré-processamento (não precisam de normalização e lidam com escalas diferentes) [Grinsztajn et al. 2022].
- **Não linearidade e interações:** combinações como "ADX alto e longe da VWAP" são capturadas sem engenharia manual.
- **Leve na inferência:** 100 árvores rasas avaliam em microssegundos, o que serve para um i3. O instalador usa o `xgboost-cpu`, 2 MB contra mais de 100 MB do pacote com GPU.

## 7.2 *Features* (18)

Montadas em `strategy.py` (contexto do sinal) e consumidas na mesma ordem do treino:

| Grupo | *Features* |
|---|---|
| Microestrutura do candle | `body_size`, `upper_wick`, `lower_wick` |
| Tendência e regime | `adx`, `z_score` (21) |
| Volatilidade | `atr`, `bollinger_bandwidth` = (banda sup. − inf.)/média |
| Momento | `rsi14` |
| Distâncias relativas | `dist_ema9`, `dist_sma21`, `dist_sma200`, `dist_vwap` = (C − média)/média |
| Tempo | `hour`, `day_of_week` |
| Padrões de [Hilpisch 2018] | `dir_lag1..3` (sinal do retorno log defasado), `rolling_vol_10` |

As distâncias **relativas** (em %) tornam as *features* comparáveis entre níveis de preço diferentes, o que é necessário para um modelo que atravessa anos de dados.

## 7.3 Decisão

- Se $p < 0{,}40$ (`ML_MIN_WIN_PROB`), o setup é **vetado**.
- O ML só avalia `russian_bb`, `judas` e `PC`; os demais setups passam direto.
- Qualquer erro na inferência (modelo ausente, xgboost ausente, exceção) **aprova** o trade, o *fail-open*. A escolha prioriza disponibilidade, mas significa que um modelo quebrado em silêncio vira "sem filtro".
- Com o alvo definido, $p$ alimenta o Half-Kelly (cap. 6 §6.2).

**Por que 0,40 e não 0,50?** O limiar está abaixo de 0,5 porque setups com RRR > 1 são lucrativos com taxa de acerto abaixo de 50%: o ponto de equilíbrio é $p^* = 1/(1+b)$, ou seja, 0,33 com $b = 2$.

## 7.4 Treinamento

`tools/train_xgboost.py`: `XGBClassifier(n_estimators=100, learning_rate=0.05, max_depth=4)`, com perda logística. Mínimo de 50 amostras por ativo. Avaliação por acurácia e `classification_report` numa separação de 80/20.

Desde a v2.14, o treino roda **só sob demanda** (`workflow_dispatch`) e publica os modelos como artefato, sem gravar direto no repositório (spec 005).

### Análise crítica (importante para estudo)

1. **Vazamento temporal.** A separação usa `train_test_split(..., random_state=42, stratify=y)`, que é **aleatória**. Em séries temporais, isso põe amostras do futuro no treino e do passado no teste, e infla a acurácia medida. O correto seria uma separação cronológica ou validação cruzada **purgada com embargo** [López de Prado 2018, cap. 7].
2. **Métrica inadequada.** Acurácia ignora o retorno: um modelo que acerta muitos trades pequenos e erra os grandes pode ter boa acurácia e expectativa negativa. Para filtros de trading, métricas como expectativa por trade aprovado ou fator de lucro dos aprovados são mais informativas.
3. **Rótulos e tamanho da amostra.** Com poucas centenas de trades, 18 *features* e 100 árvores, o risco de sobreajuste é alto; a regularização ajuda, mas não substitui validação fora da amostra.
4. **Probabilidade não calibrada.** A saída do *boosting* não é necessariamente uma probabilidade calibrada; usá-la no Kelly pede calibração prévia (Platt ou isotônica) [Niculescu-Mizil & Caruana 2005].

Esses pontos explicam por que as **rotas quant não usam ML**: elas foram validadas sem o filtro, e acrescentá-lo mudaria a estratégia (cap. 1 §1.5).

## 7.5 *Data flywheel*: simulador, otimizador e supervisor adaptativo

Fluxo de aprendizado contínuo sobre os sinais **rejeitados**:

```
sinal vetado (RVOL, scoring, ML) ─▶ virtual_rejections.json
        │
        ▼  simulator.py: refaz o trade no M1 (sai no SL ou quando a EMA9 vira)
virtual_rejections_enriched.json (resultado hipotético de cada veto)
        │
        ▼  optimizer.py: expectativa por (ativo, sessão Ásia/Londres/NY)
calibrations.json  ──▶  AdaptiveSupervisor.check_override()
                         libera um veto quando a sessão tem expectativa > 0
```

- **Expectativa** (`optimizer.py`): $E = p_w \bar G - (1-p_w)\bar P$, em pips, por ativo e sessão.
- **Regra:** se $E > 0$ com pelo menos **3 amostras**, a sessão ganha uma calibração: RVOL mínimo reduzido para 1,05 e/ou `MACRO_OVERRIDE`.
- **Supervisor:** quando um filtro veta, `check_override` consulta a sessão atual (pelo horário UTC) e pode liberar.

**Fundamentação.** A ideia de medir o custo de oportunidade dos vetos, isto é, o que teria acontecido com os trades bloqueados, é sólida: filtros têm custo, e ele deve ser medido.

**Análise crítica.** Três amostras não sustentam inferência alguma. A probabilidade de uma estratégia aleatória com acerto de 50% mostrar expectativa positiva em 3 trades é de cerca de 50%. O processo testa muitas combinações (ativo × sessão × filtro) e libera as que "deram certo", o que é exatamente o problema de **comparações múltiplas** e *data snooping* [White 2000; Harvey, Liu & Zhu 2016]. Uma versão estatisticamente defensável exigiria amostra mínima muito maior, correção para múltiplos testes (por exemplo, Benjamini-Hochberg) e validação temporal.

## 7.6 Referencial teórico

[Chen & Guestrin 2016] XGBoost; [Friedman 2001] *gradient boosting*; [Grinsztajn et al. 2022] árvores × redes em dados tabulares; [López de Prado 2018] validação purgada e vazamento; [Niculescu-Mizil & Caruana 2005] calibração; [White 2000; Harvey, Liu & Zhu 2016] *data snooping*; [Hilpisch 2018] *features* de retorno.
