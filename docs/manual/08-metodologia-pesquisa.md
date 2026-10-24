# 8. Metodologia de pesquisa quantitativa

Este capítulo descreve como as rotas quant foram escolhidas (`tools/quant_research/`) e, principalmente, como o projeto tentou **não se enganar**. O risco central de qualquer pesquisa de estratégias é o *backtest overfitting*: com tentativas suficientes, sempre aparece uma regra que "funcionou" no passado por acaso [Bailey et al. 2014; White 2000; Aronson 2006].

## 8.1 Universo e dados

- **Ativos:** 15 instrumentos com margem baixa no lote mínimo (índices HK50, JP225, US500, FR40, AU200, EU50, UK100, CN50; petróleo; criptos ETH, SOL, XRP, LTC, BTC), escolhidos pelo critério de viabilidade com saldo de cerca de $16.
- **Timeframes:** M15, H1, H4 (reamostrado do H1, depois conferido contra o H4 nativo: OHLC idêntico) e D1.
- **Fonte:** histórico da própria corretora via `copy_rates_from_pos` (`fetch.py`); de 1 a 9 anos, conforme o timeframe.

## 8.2 Modelo de custos

Backtest sem custos é a fonte mais comum de resultados ilusórios em estratégias de alta frequência relativa [Kaufman 2013]. O simulador (`research.py:simulate`) cobra:

| Custo | Modelo |
|---|---|
| Spread | O **spread registrado em cada candle** (coluna `spread` do MT5), pago na entrada. Candles com spread 0 recebem a mediana. Na compra, entra pelo *ask* = *bid* + spread; na venda, o stop e o alvo são avaliados pelo *ask* |
| Comissão | US$ 1/lote na entrada, observado nos *deals* reais da conta (zero em HK50, JP225 e petróleo) |
| Swap | Por noite mantida (diferença de dias entre entrada e saída), em pontos por lote ou % anual sobre o preço, conforme o `swap_mode` do símbolo |
| Valor do ponto | `order_calc_profit` com o lote mínimo, já na moeda da conta |

## 8.3 Regras de simulação

- Sinal no fechamento de $t$; **entrada na abertura de $t+1$**: nenhuma informação de $t+1$ é usada para decidir.
- **Stop antes do alvo** quando os dois cabem no mesmo candle, porque o OHLC não diz qual veio primeiro. É a hipótese pessimista.
- **Gap através do stop:** a saída é na abertura, se ela for pior que o stop (`min(o[j], sl)`).
- Uma posição por vez por estratégia; o próximo sinal só vale depois da saída.

O núcleo do simulador para uma compra (a venda é espelhada e avaliada pelo *ask*):

```python
# Listagem 8.1 — tools/quant_research/research.py
        entry = o[e]
        sl = entry - dr * sd
        tp = entry + dr * tgt[i] if np.isfinite(tgt[i]) else np.nan
        exit_p = None; j = e
        while j < n:
            # stop / alvo intrabar (stop primeiro: conservador)
            if dr > 0:
                if l[j] <= sl: exit_p = min(o[j], sl) if j > e else sl; break
                if np.isfinite(tp) and h[j] >= tp: exit_p = max(o[j], tp) if j > e else tp; break
    ...
        pnl_price = dr * (exit_p - entry) - spr[e]
```

`entry = o[e]`, com `e = i + 1`, é a entrada na abertura do candle seguinte; o teste do *stop* vem antes do teste do alvo; e `min(o[j], sl)` cobra o *gap* quando o candle já abre além do *stop*.

Essas escolhas tornam o backtest **conservador**: a execução real tende a ser igual ou melhor do que a simulada, nunca sistematicamente pior por construção.

## 8.4 Espaço de busca

Quatro famílias clássicas, com **poucos parâmetros cada** (menos graus de liberdade, menos chance de sobreajuste):

| Família | Ideia | Parâmetros testados |
|---|---|---|
| RSI2 | Reversão de curto prazo [Connors & Alvarez 2009] | limiar 5/10/20, stop 2/3 ATR, só compra/ambos, intradiário/não |
| BBMR | Reversão às bandas de Bollinger | 2/2,5 desvios, stop 1,5/2,5 ATR, filtro SMA200, intradiário |
| DONCH | Rompimento de Donchian (tendência) [Kaufman 2013] | canal 20/55, stop 2/3 ATR, intradiário |
| PULLB | *Pullback* na EMA20 | stop 1/1,5 ATR, alvo 1,5/2/3 R, intradiário |

Total: **3.150 combinações** (ativo × timeframe × família × parâmetros).

## 8.5 Protocolo de validação

1. **Dentro × fora da amostra:** os primeiros 60% do histórico (*in-sample*, IS) servem para escolher; os últimos 40% (*out-of-sample*, OOS) só para conferir. É a separação temporal mínima, um caso particular do *walk-forward* [Pardo 2008].
2. **Robustez da família, não do melhor ponto:** uma família só é aceita se a **maioria das variações** lucra em IS **e** OOS. O melhor parâmetro isolado de uma grade é quase sempre sorte; uma região inteira lucrativa é evidência de um efeito real [Aronson 2006].
3. **Ano a ano:** quantos anos foram positivos, para expor dependência de um único período.
4. **Estresse de custos:** spread multiplicado por 1,5.
5. **Viabilidade de capital:** a pior queda e o pior trade precisam caber no saldo. Por isso a pesquisa descartou as criptos em D1, que pareciam lucrativas mas tinham quedas de $50 a $160 no lote mínimo.

## 8.6 Teste de sorte (segunda rodada)

Com 3.150 tentativas, até um resultado que passa no protocolo pode ser sorte. A segunda rodada (`portfolio.py`, `robustness.py`) aplicou três testes:

**(a) Estatística t do lucro médio por trade:**
$$t = \frac{\bar x}{s/\sqrt n}$$
Valores acima de cerca de 2 indicam média improvável sob a hipótese nula de média zero. Mas, com muitas tentativas, o limiar correto sobe: [Harvey, Liu & Zhu 2016] defendem $t > 3$ para descobertas em finanças, por causa das comparações múltiplas. Resultado: **US500 RSI2 t = 2,57; HK50 PULLB t = 1,65.**

**(b) Linha de base aleatória (teste de permutação):** 300 carteiras com entradas sorteadas entre os candles "a favor da tendência", com o **mesmo SL/TP** do PULLB no HK50. Se a regra de entrada não acrescentasse nada, o PULLB cairia no meio dessa distribuição. Resultado: mediana aleatória de −$5,96, percentil 95 de +$2,67, PULLB **+$9,96**, ou seja, acima de todas as 300. Isso isola o valor do **sinal de entrada**, separando-o do valor do ativo e do esquema de saída, na linha dos testes de *bootstrap* de regras técnicas [White 2000; Aronson 2006].

**(c) Generalização entre ativos** com os **mesmos parâmetros**, sem otimizar de novo:
- PULLB H4: lucra só no HK50, e **perde em 8 de 9** outros índices;
- RSI2 D1 (L=5, k=2): **lucra em 6 de 8** índices.

Um efeito econômico real tende a aparecer em mercados parecidos; um artefato estatístico, não.

**(d) Sensibilidade do stop (RSI2 no US500):** lucro em todos os stops de 0,5 a 3 ATR (fator de lucro de 1,40 a 2,40). A rentabilidade não depende de um parâmetro "mágico".

## 8.7 Resultados e decisões

| Rota | Trades | Fator de lucro | Lucro (lote mín.) | Pior queda | t | Generaliza? | Leitura |
|---|---|---|---|---|---|---|---|
| US500 D1 RSI2MR | 54 / 9,5 anos | 2,40 | +$13,19 | $3,04 | 2,57 | Sim (6/8) | Evidência mais forte |
| HK50 H4 PULLB | 277 / 4,8 anos | 1,24 | +$9,96 | $4,30 | 1,65 | Não (1/9) | Experimento ao vivo |

**Decisão metodológica registrada:** o stop do RSI2 **não** foi encurtado para caber no limite de risco de uma conta de $16. Isso seria escolher um parâmetro depois de ver o resultado, que é justamente a forma de sobreajuste que o protocolo tenta evitar. O limite de risco foi tratado como decisão do dono (12% para a rota), não como otimização.

## 8.8 Verificação da implementação

Uma estratégia validada só vale se o código ao vivo for **a mesma** estratégia. O projeto verificou isso de três formas:
1. **Equivalência de sinais:** `quant_setups.evaluate` rodado vela a vela (janela de 400) contra os sinais vetorizados da pesquisa, com **0 divergências** em 4.626 candles.
2. **Mesmo H4:** o H4 reamostrado da pesquisa e o H4 nativo do MT5 têm OHLC idênticos.
3. **Mesmas regras de entrada e saída:** a mercado na abertura de $t+1$, SL/TP na ordem, saída da regra só depois que o candle de entrada fecha (cap. 3 §3.5).

## 8.9 Limitações

- **Uma separação IS/OOS** é menos robusta que *walk-forward* com várias janelas ou validação cruzada combinatória purgada [López de Prado 2018; Bailey et al. 2017].
- **Não se calculou o *Deflated Sharpe Ratio*** [Bailey & López de Prado 2014], que corrige o Sharpe pelo número de tentativas. Seria o próximo passo natural.
- **Amostras pequenas** (54 trades no RSI2) dão intervalos de confiança largos.
- **Swap aproximado:** o simulador conta noites por dia de calendário (de sexta para segunda = 3 noites), o que aproxima o swap triplo, mas não reproduz o dia exato em que cada corretora cobra a rolagem tripla (quarta ou sexta). O erro afeta o momento do custo, não o total ao longo de uma semana.
- **Sobrevivência e mudança de regime:** custos e spreads de 2021 não são os de hoje, e a corretora pode mudar condições.

## 8.10 Referencial teórico

[Bailey et al. 2014; Bailey et al. 2017] *backtest overfitting*; [Bailey & López de Prado 2014] *Deflated Sharpe*; [White 2000] *Reality Check* e *data snooping*; [Harvey, Liu & Zhu 2016] limiar t > 3; [Aronson 2006] análise técnica baseada em evidência; [Lo, Mamaysky & Wang 2000] fundamentos estatísticos da análise técnica; [Pardo 2008] *walk-forward*; [López de Prado 2018] validação purgada; [Kaufman 2013] custos e sistemas; [Connors & Alvarez 2009].
