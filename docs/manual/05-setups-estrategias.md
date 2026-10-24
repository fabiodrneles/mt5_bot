# 5. Setups e estratégias

Um **setup** é uma regra que, olhando o último candle fechado, diz se há uma oportunidade e com que entrada, stop e alvo. O projeto tem dois grupos com status muito diferentes:

| Grupo | Validação | Ao vivo por padrão | Código |
|---|---|---|---|
| **Rotas quant** (PULLB, RSI2MR) | Fora da amostra, com custos reais e teste de sorte (cap. 8) | Sim | `mt5bot/engine/quant_setups.py` |
| **Setups clássicos** (9.x, PC, FFFD, GAP, russian_bb, judas, DiNapoli, IFR2, SAR, RompFalso) | Livros-fonte; sem validação fora da amostra no projeto | Não (só simulação, decisão D5) | `mt5bot/engine/strategy.py` |

## 5.1 Rotas quant

### PULLB: *pullback* na EMA20 a favor da tendência (HK50 H4)

`quant_setups.signal_pullb`. Com o candle $t$ fechado:

- **Compra:** $EMA_{20} > EMA_{50}$, $L_t \le EMA_{20} < C_t$ e $C_t > SMA_{200}$.
- **Venda:** $EMA_{20} < EMA_{50}$, $H_t \ge EMA_{20} > C_t$ e $C_t < SMA_{200}$.
- **Stop:** 1 × ATR(14); **alvo:** 2 × ATR(14), uma razão risco-retorno de 2:1. Sai **só** por SL ou TP.

A regra inteira cabe em poucas linhas, e é exatamente a mesma que a pesquisa testou (ver "Execução idêntica ao teste", adiante):

```python
# Listagem 5.1 — mt5bot/engine/quant_setups.py
    k = params.get("sl_atr", 1.0); r = params.get("tp_r", 2.0)
    if e20.iloc[last] > e50.iloc[last] and df['low'].iloc[last] <= e20.iloc[last] < cl and cl > s200.iloc[last]:
        return {"setup": "PULLB", "action": "buy", "sl_dist": k * a, "tp_dist": r * k * a}
    if e20.iloc[last] < e50.iloc[last] and df['high'].iloc[last] >= e20.iloc[last] > cl and cl < s200.iloc[last]:
        return {"setup": "PULLB", "action": "sell", "sl_dist": k * a, "tp_dist": r * k * a}
    return None
```

**Lógica econômica.** O alinhamento EMA20 > EMA50 > SMA200 define uma tendência em três escalas. O toque na EMA20, com fechamento acima dela, é um recuo **absorvido**: o preço testou o suporte dinâmico e voltou. É a forma clássica de "comprar a correção na tendência" [Murphy 1999; Kaufman 2013]. O alvo de 2 ATR contra um stop de 1 ATR exige taxa de acerto acima de 1/3 (mais os custos) para dar lucro.

**Evidência (cap. 8):**
- 277 trades em 4,8 anos, fator de lucro 1,24 e +$9,96 no lote mínimo.
- 100% das 12 variações de parâmetros da família lucram nos dois períodos.
- Venceu as 300 carteiras aleatórias com o mesmo SL/TP.
- **Não generaliza:** a mesma regra perde em 8 de 9 outros índices, e a estatística t é 1,65. Deve ser tratada como **experimento ao vivo**.

### RSI2MR: reversão de curto prazo com IFR(2) (US500 D1)

`quant_setups.signal_rsi2mr` / `exit_rsi2mr`:

- **Compra:** $RSI_2 < 5$ e $C_t > SMA_{200}$. **Venda:** $RSI_2 > 95$ e $C_t < SMA_{200}$.
- **Stop:** 2 × ATR(14). **Saída:** o fechamento cruza a SMA5 a favor, ou após 15 candles.

```python
# Listagem 5.2 — mt5bot/engine/quant_setups.py
    lvl = params.get("rsi_level", 5.0); k = params.get("sl_atr", 2.0)
    if rsi2.iloc[last] < lvl and cl > s200.iloc[last]:
        return {"setup": "RSI2MR", "action": "buy", "sl_dist": k * a, "tp_dist": None}
    if not params.get("long_only", False) and rsi2.iloc[last] > 100 - lvl and cl < s200.iloc[last]:
        return {"setup": "RSI2MR", "action": "sell", "sl_dist": k * a, "tp_dist": None}
```

`tp_dist = None` indica que a saída não é por alvo fixo, e sim pela regra `exit_rsi2mr` (cruzamento da SMA5) ou pelo limite de candles.

**Lógica econômica.** Em índices de ações há uma tendência de longo prazo positiva, e quedas fortes de curtíssimo prazo tendem a se reverter parcialmente. O IFR com período 2 é um medidor extremo de sobrevenda de 2 a 3 dias. A estratégia foi popularizada por [Connors & Alvarez 2009], e o efeito de reversão de curto prazo em índices é documentado na literatura [Lo & MacKinlay 1990]. A saída na SMA5 captura a "volta à média" sem exigir um alvo fixo.

**Evidência (cap. 8):**
- 54 trades em 9,5 anos, fator de lucro 2,40 e +$13,19.
- Estatística t de 2,57.
- Lucra em 6 de 8 índices com o mesmo parâmetro, e em qualquer stop de 0,5 a 3 ATR. É a rota com **a evidência mais forte**.

### Execução idêntica ao teste

As rotas quant usam **lote mínimo fixo**, entrada a mercado na abertura do candle seguinte e SL/TP gravados na ordem (cap. 3 §3.5). A equivalência foi verificada executando `quant_setups.evaluate` vela a vela, com janela de 400 candles, contra os sinais vetorizados da pesquisa: **0 divergências** em 2.500 candles (HK50 H4) e 2.126 (US500 D1).

## 5.2 Setups clássicos

Baseados na família 9.x, atribuída a Larry Williams e difundida no Brasil pelos livros-fonte do projeto, de Alexandre Fernandes (Palex) [Fernandes, Estratégias Operacionais; Fernandes, Fundamentos], e em autores citados em cada linha. "Offset" é 1 tick além da máxima/mínima.

| Setup | Condição (compra; venda espelhada) | Entrada | Stop | Referência |
|---|---|---|---|---|
| **9.1** | EMA9 vira para cima ($EMA9_{t-1}$ caindo, $EMA9_t$ subindo) | STOP na máxima + offset | Mínima do candle | Palex; Williams |
| **9.2** | EMA9 subindo em $t-1$ e $t$, e $L_t < L_{t-1}$ (correção leve) | Máxima + offset | Mínima | Palex |
| **9.3** | EMA9 subindo; candle de referência fecha abaixo da mínima anterior e os 2 seguintes fecham abaixo dele (recuo profundo) | Máxima + offset | Menor mínima dos 2 | Palex |
| **9.4** | EMA9 sobe, cai e volta a subir (falso recuo), mínima preservada | Máxima + offset | Mínima de $t-1$ | Palex |
| **PC** (Ponto Contínuo) | SMA21 subindo há 2 candles e mínima até 0,3 ATR acima da SMA21 | Máxima + offset | Mínima | Palex |
| **FFFD** | Fecha fora (abaixo da banda inferior) e depois fecha dentro | Máxima + offset | Menor mínima dos 2 | [Bollinger 2001] |
| **GAP** | Primeiro candle do dia com *gap* > 0,5% e candle contra o *gap* | Rompimento | Extremo do candle | Fechamento de *gap* |
| **russian_bb** | Mínima abaixo da banda inferior, IFR14 < limiar, largura mínima da banda e sem tendência de baixa alinhada | A mercado | Fechamento − meia banda | Reversão à média |
| **judas** | Candle nos horários-alvo; opera contra o corpo | A mercado | Pontos fixos | "Fading the open" |
| **DiNapoli** | Segundo fundo acima do primeiro, fechando acima da EMA12 deslocada | Máxima + offset | Mínima | [DiNapoli 1998] |
| **IFR2** | $RSI_2 \le 5$, EMA50 subindo, $C > EMA_{50}$ e $C > SMA_{13}$ | Máxima + offset | Mínima | [Connors & Alvarez 2009] |
| **SAR** | SAR abaixo da mínima, IFR14 > 50 e $C > SMA_{13}$ | Máxima + offset | Mínima | [Wilder 1978] |
| **RompFalso** | Perde o suporte (mínima de $t-3$) e volta para dentro | Máxima + offset | Menor mínima | [Farley 2000] |

**Filtro de longo prazo.** Ao final, `evaluate_all` só mantém compras com $C > SMA_{200}$ e vendas com $C < SMA_{200}$ (o GAP é exceção). É a regra mais usada para separar regimes de alta e baixa [Faber 2007].

**Por que estão em simulação por padrão?** Porque o projeto não tem evidência fora da amostra de que eles cubram os custos. A pesquisa da Fase 1 encontrou combinações 9.x com fator de lucro 0,45 no EURUSD, e o histórico real da conta foi de −$33,18 em 7 trades. Pela constituição (princípio 2), só opera ao vivo o que foi validado. Liberar exige `allow_unvalidated_live = true` no `config.toml`.

## 5.3 Roteamento por ativo

`config.ASSET_SETUPS` define quais setups clássicos rodam em cada ativo: por exemplo, HK50 só `russian_bb`, EURUSD `russian_bb` + `judas`, e o padrão é todos. As rotas quant (`QUANT_ROUTES`) têm precedência quando o par (ativo, timeframe) coincide.

## 5.4 Motor de *scoring* (caminho clássico)

Quando mais de um setup dispara no mesmo candle, `mt5bot/engine/scoring.py` escolhe um, seguindo a fórmula registrada no documento de aprofundamento do projeto (`memoria/raw/aprofundamento.md`), derivada dos livros-fonte [Fernandes, Estratégias Operacionais]:

$$\text{score} = 30\cdot RRR + 25\cdot\mathbb{1}_{\text{congruência}} + 20\,(1 - \text{proximidade}) + 25\cdot\mathbb{1}_{RVOL \ge 1{,}15} + 10\cdot\mathbb{1}_{IFR9} + 10\cdot\mathbb{1}_{\text{toque VWAP}}$$

- $RRR = |\text{alvo} - \text{entrada}| / |\text{entrada} - \text{stop}|$. Sem alvo próprio, o setup recebe o **alvo padrão de 1 risco** ($RRR = 1$).
- **Gate:** $RRR < 1$ vale score 0, ou seja, veto.
- **Congruência:** $C > EMA9 > SMA21 > EMA50$ (compra).
- **Proximidade:** $\min(|C - SMA21|/ATR,\, 1)$; perto da média vale mais.
- **Vetos:** MM50, VWAP esticada e multi-timeframe contra zeram o score.
- **Exceções:** `russian_bb` = 100 e `judas` = 90 (prioridade fixa).
- Os pesos são configuráveis em `config.SCORE_WEIGHTS`.

**Análise crítica.** É um modelo aditivo de pontuação com pesos definidos por especialista, uma forma de decisão multicritério (MCDM) de soma ponderada [Triantaphyllou 2000]. Ele é transparente e auditável, mas **os pesos não foram estimados a partir de dados**: não há garantia de que um score maior implique retorno esperado maior. Uma evolução natural seria calibrar os pesos por regressão logística ou *ranking* fora da amostra, ou substituí-los pela probabilidade estimada do modelo de ML (cap. 7).

## 5.5 Referencial teórico

[Connors & Alvarez 2009] IFR2; [Lo & MacKinlay 1990] reversão de curto prazo; [Faber 2007] filtro de média longa; [Murphy 1999; Kaufman 2013] seguimento de tendência e *pullbacks*; [Bollinger 2001]; [DiNapoli 1998]; [Farley 2000] falsos rompimentos; [Wilder 1978]; [Triantaphyllou 2000] decisão multicritério; livros-fonte de Alexandre Fernandes (Palex) em `memoria/raw/`.
