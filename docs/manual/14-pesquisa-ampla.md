# 14. Pesquisa ampla de padrões: método, artefatos de dados e resultados

Este capítulo documenta a terceira rodada de pesquisa do projeto (outubro de 2026). Ela respondeu a uma pergunta direta do dono: *existe, no mercado acessível a uma conta de US$ 16, algum padrão — de horário, de data, de indicador, de volume ou de relação entre ativos — que se repita e deixe lucro depois dos custos, nem que seja de centavos?*

A pergunta é boa e a resposta negativa é informativa. Mas a contribuição principal do capítulo é outra: mostrar, com casos reais, **como um backtest engana** e quais técnicas de engenharia e de estatística separaram padrões reais de artefatos. Quatro "estratégias" que pareciam lucrar todos os dias eram defeitos dos dados históricos. Se tivessem virado motores, teriam perdido dinheiro real.

## 14.1 Pergunta, hipóteses e restrições

**Pergunta.** Entre todas as regras de uma biblioteca ampla (seção 14.2), aplicadas a todos os ativos operáveis com US$ 16, alguma tem expectativa positiva fora da amostra, depois de custos reais, com evidência que resista ao número de tentativas?

**Hipótese nula** para cada regra $r$: o lucro esperado por trade é $\mu_r \le 0$. Pela hipótese dos mercados eficientes [Fama 1970] e, na versão adaptativa [Lo 2004], vantagens simples tendem a desaparecer ou a ficar menores que o custo de transação. A hipótese alternativa é a do dono: existem padrões "escondidos" repetitivos.

**Restrições da conta.** No lote mínimo, cada ativo tem um custo fixo de oportunidade: a margem e a perda até o stop. O universo foi limitado a símbolos com margem no lote mínimo $\le 25\%$ de US$ 16 (`tools/quant_research/universe.py`): 337 de 465 negociáveis. A tabela abaixo mostra por que a classe de ativo importa tanto quanto a regra:

| Classe | Margem no lote mínimo | 1 ATR diário no lote mínimo |
|---|---|---|
| Índices (HK50, JP225, US500) | US$ 0,15–0,76 | US$ 0,3–1,9 |
| Forex principais (EURUSD, GBPUSD, USDJPY) | US$ 2,0–2,7 | **US$ 5,0–7,4** (30–45% da conta) |
| CFDs de ações baratas | US$ 0,04–0,7 | US$ 0,02–0,1 |
| Cripto (ETH, XRP) | US$ 0,6–1,2 | US$ 5,7–9,2 |

Com US$ 16, um stop de 1 ATR diário num par de forex principal custa um terço da conta. Isso não é detalhe de implementação: elimina, por viabilidade, a maioria das estratégias diárias de forex antes de qualquer estatística.

## 14.2 Desenho experimental

### Universo e dados

- **Ativos:** os 337 símbolos do filtro de margem, baixados por prioridade (forex, índices, commodities e cripto antes das ações): `tools/quant_research/fetch2.py`.
- **Timeframes:** H1 (até 30.000 candles), H4 (reamostrado do H1) e D1 (até 4.000 candles).
- **Volume:** volume de ticks do MT5 (não há volume real em CFDs e forex de balcão). É uma aproximação de atividade, não de fluxo de ordens.

### Biblioteca de regras (28 famílias)

| Grupo | Famílias | Ideia testada | Referência |
|---|---|---|---|
| Reversão à média | RSI2, RSIn, IBS, quedas seguidas, Double-7, Bollinger, z-score, *gap fade* | Excessos de curto prazo se corrigem | [Connors & Alvarez 2009; De Bondt & Thaler 1985] |
| Tendência e momento | Donchian, cruzamento de médias, TSMOM, MACD, Keltner, Supertrend, ADX + DI, pullback na EMA20 | Movimentos persistem | [Moskowitz, Ooi & Pedersen 2012; Brock, Lakonishok & LeBaron 1992] |
| Padrões de candle | NR7, *inside bar*, engolfo na banda, martelo/estrela | Formações de reversão/rompimento | [Nison 1991] |
| Volume e fluxo | Pico de volume (capitulação), rompimento com volume, OBV + IFR2, VWAP intradiário, faixa de abertura (ORB) | Atividade anormal antecede movimento | [Granville 1963] |
| Calendário | Virada do mês, dia da semana, hora do dia | Sazonalidades | [French 1980; Ariel 1987] |
| Estatística entre ativos | Pares cointegrados (z-score do spread log); *lead-lag* (A antecipa B) | Relações de equilíbrio e difusão de informação | [Engle & Granger 1987; Gatev, Goetzmann & Rouwenhorst 2006] |

Cada família tem de 2 a 12 variações de parâmetro. As regras de reversão rápida também rodam na versão intradiária (`_I`, fecha no fim do dia) no H1. A implementação é `tools/quant_research/research2.py` (grade), `pairs2.py` (pares), `seasonal2.py` (horário e data) e `leadlag2.py` (cruzamentos).

### Pré-registro

O protocolo de decisão (`tools/quant_research/PROTOCOLO2.md`) foi escrito e versionado **antes** de rodar a grade, à maneira do pré-registro de estudos científicos [Nosek et al. 2018]. O motivo é evitar o erro mais comum em pesquisa de estratégias: ajustar o critério depois de ver os números até que algo passe. Mudanças feitas durante a execução (seção 14.4) ficaram registradas no próprio protocolo, com data e motivo, e todas foram no sentido conservador.

## 14.3 Modelo de custos e simulador

O resultado de um trade comprado de um lote mínimo, em US$, é

$$
\pi = \big(P_{\text{saída}}^{\text{bid}} - P_{\text{entrada}}^{\text{ask}}\big)\cdot u \;-\; C \;+\; S,
\qquad P^{\text{ask}} = P^{\text{bid}} + s,
$$

onde $u$ é o valor em US$ de uma unidade de preço no lote mínimo (`order_calc_profit`), $s$ o spread, $C$ a comissão e $S$ o swap. Os candles do MT5 são de **bid**, então a compra paga o spread na entrada e a venda paga na recompra.

**Swap com rolagem tripla.** O swap é cobrado a cada virada de dia útil e em triplo no dia definido pela corretora (`swap_rollover3days`, em geral quarta-feira), que cobre o fim de semana:

$$
S = s_{\text{lado}} \cdot \sum_{d=d_e}^{d_s - 1} w(d), \qquad
w(d) = \begin{cases} 0 & d \in \{\text{sáb}, \text{dom}\} \\ 3 & d = d_{\text{triplo}} \\ 1 & \text{caso contrário} \end{cases}
$$

A pesquisa anterior contava noites de calendário; a diferença nas rotas atuais foi de US$ 0,01–0,03 (seção 14.6).

**Ordem dos eventos dentro do candle.** Quando um candle toca o stop e o alvo, assume-se o stop primeiro (hipótese pessimista). Um *gap* além do stop sai no preço de abertura, não no stop.

**Regras de entrada conservadoras.** A seção 14.4 explica de onde vieram; a Listagem 14.1 mostra como ficaram no código.

```python
# Listagem 14.1 — tools/quant_research/research2.py
if d.get("tf") == "D1":
spr = d["spr"] * cost
spr_close = spr
else:
spr = np.maximum(d["spr"], np.r_[d["spr"][:1], d["spr"][:-1]]) * cost
spr_close = np.maximum(d["spr"], np.r_[d["spr"][1:], d["spr"][-1:]]) * cost
...
pause = np.r_[False, np.diff(t) > bar * 1.5] if d.get("tf") != "D1" else np.r_[False, np.ones(n - 1, bool)]
rollover = (d["hour"] == 0) if d.get("tf") in INTRADAY_TFS and "hour" in d else np.zeros(n, bool)
...
if rollover[e]:
...
k += 1
continue
...
entry = o[e]
if pause[e]:
...
entry = max(o[e], c[e - 1]) if dr > 0 else min(o[e], c[e - 1])
```

O simulador reproduz a pesquisa anterior antes das correções (HK50 H4 PULLB: 277 trades e +US$ 9,93 contra +US$ 9,96 publicados; US500 D1 RSI2: 54 trades e +US$ 13,18 contra +US$ 13,19), o que valida a reimplementação. Os testes em `tests/test_research2.py` fixam as regras: rolagem tripla, stop antes do alvo, saída no *gap*, spread do rollover, entrada depois de pausa, nenhuma entrada na hora do rollover e **ausência de *look-ahead***. Este último altera o futuro de uma série sintética e exige que os sinais do passado não mudem, em todas as 28 famílias.

## 14.4 Artefatos de dados: quando o lucro é um defeito

Esta é a seção mais importante do capítulo. A cada rodada surgiram resultados "bons demais". Em vez de construir motores, cada um foi tratado como **suspeito de artefato** e investigado com uma fonte de dados independente (candles de 1 minuto ou ticks com bid e ask). Os seis casos abaixo explicam todas as "descobertas" das primeiras varreduras.

| # | Sintoma no backtest | Causa | Evidência | Correção |
|---|---|---|---|---|
| A1 | Ações perdendo US$ 1 por trade em qualquer regra | Comissão de US$ 1/lote aplicada a um lote de 1 ação | Sharpe por trade de −34 (todo trade perde só o custo) | Comissão de CFD de ações estimada em 0,1% do valor por lado. **Estimada**: a API não informa |
| A2 | Forex lucrando ao comprar na hora 1 e no "gap" da virada do dia | Spread do rollover subestimado | AUDCAD: 3 pts normalmente, 19 na hora 0, 6 na hora 1 | Entrada paga o maior spread entre o candle anterior e o de entrada |
| A3 | "Comprar AUD na segunda-feira": +US$ 411 fora da amostra | Spread da reabertura de domingo | Mediana de 62 pts no 1º candle depois do fim de semana (3 normalmente) | D1 paga o spread da hora de abertura e da reabertura |
| A4 | "Comprar ações na abertura de Nova York": t ≈ 30, lucro todo dia por anos | **Cotação de abertura irreal** no histórico H1 | LKQCorp 2023: o candle "sobe" +1,053 e a abertura vem −1,096 abaixo do fechamento anterior; em M1 recente, a 1ª hora sobe só US$ 0,018 | Entrada no 1º candle depois de pausa pelo **pior** entre abertura e fechamento anterior |
| A5 | "Comprar EURUSD/EURGBP na quinta à 0h" (3 sobreviventes do FDR) | O campo spread do candle guarda o **mínimo** da hora | Ticks reais do EURGBP 0h00–0h10 de quinta: spread de 82–224 pts contra ~30 no candle; o bid afunda e o ask fica parado | Nenhuma entrada na hora 0 do servidor (H1/H4) |
| A6 | "LKQCorp D1, comprar na sexta": DSR 0,92, walk-forward 5/5 positivo | O candle **diário** herda a abertura irreal de A4 | Todos os dias da semana "sobem" ~US$ 0,60, e a abertura vem ~US$ 0,60 abaixo; abertura D1 = 1ª abertura H1 em 1.943 de 1.943 dias; 37 de 72 CFDs têm o defeito, forex e cripto não | Entrada no D1 pelo pior entre abertura e fechamento anterior |

### O método de diagnóstico

Os seis casos foram detectados pelo mesmo raciocínio, que vale como receita:

1. **Desconfie do que é bom demais.** Um t de 30 numa regra de horário, ou um lucro diário de 1,5% de uma ação comum, contradiz tudo o que se sabe sobre mercados líquidos. A pergunta certa não é "como explorar", é "o que nos dados produz isso".
2. **Decomponha o retorno.** Em A4 e A6, separar o corpo do candle ($C_t - O_t$) do *gap* ($O_t - C_{t-1}$) mostrou que um desfaz o outro quase exatamente:
   $$\mathbb{E}[C_t - O_t] \approx -\,\mathbb{E}[O_t - C_{t-1}] .$$
   Um efeito real no corpo não precisaria de um *gap* negativo simétrico. Um preço de abertura falso produz exatamente essa assinatura.
3. **Teste a generalidade do efeito.** Em A6, todos os dias da semana tinham o mesmo "efeito", e a sexta só foi a escolhida pela seleção. Um padrão de calendário real é específico, e um artefato é geral.
4. **Confirme com uma fonte independente e mais fina.** Candles de 1 minuto (A4) e ticks com bid e ask (A5) mostram o preço executável. Em A5, o problema só aparece nos ticks: o candle de 1 minuto também guarda o spread mínimo.
5. **Corrija para o lado conservador, documente e teste.** Toda correção virou regra do simulador com teste automatizado e nota no protocolo.

A lição de engenharia é que **dados de mercado são entradas não confiáveis**, como qualquer entrada externa de um sistema. O campo `spread` de um candle do MT5 não é "o spread": é um resumo (o mínimo) que esconde exatamente os momentos em que o custo explode. Um backtest que ignora isso produz estratégias que só existem dentro do arquivo.

## 14.5 Controle de descobertas falsas

Com dezenas de milhares de regras, o problema central é estatístico. Se cada teste tem probabilidade $\alpha$ de falso positivo, o número esperado de "descobertas" sob a hipótese nula é $m\alpha$. Com $m = 68.134$ células de calendário e $\alpha = 2{,}5\%$ (t ≥ 2 unilateral), seriam cerca de 1.700 "padrões" puramente por acaso. O tema é conhecido em finanças como *data snooping* [Sullivan, Timmermann & White 1999; White 2000] e motivou a exigência de limiares bem maiores que t = 2 na literatura de fatores [Harvey, Liu & Zhu 2016]. A pesquisa aplica cinco defesas em camadas.

**1. Separação temporal (IS/OOS).** O parâmetro é escolhido pela estatística t do lucro por trade nos 60% iniciais (IS). O resultado que conta vem dos 40% finais (OOS), que a seleção nunca viu:
$$t = \frac{\bar\pi}{\hat\sigma_\pi/\sqrt{n}} .$$

**2. Robustez da família.** Pelo menos metade das variações de parâmetro tem de lucrar nos dois períodos. Um pico isolado numa grade é sinal de ajuste ao ruído.

**3. *Walk-forward* ancorado.** O histórico é dividido em 6 blocos; na dobra $f$ escolhe-se o parâmetro nos blocos $1..f$ e mede-se no bloco $f+1$, para $f = 1..5$. Exige-se soma positiva e pelo menos 3 de 5 dobras positivas. Isso repete a seleção cinco vezes, em vez de confiar em um corte só [López de Prado 2018].

**4. *Deflated Sharpe Ratio* (DSR).** Corrige o Sharpe pelo número de tentativas e pela não normalidade dos retornos [Bailey & López de Prado 2014]. O maior Sharpe esperado entre $N$ tentativas sem vantagem é aproximadamente
$$
SR_0 = \sqrt{V[\widehat{SR}]}\,\Big((1-\gamma)\,\Phi^{-1}\!\big(1 - \tfrac{1}{N}\big) + \gamma\,\Phi^{-1}\!\big(1 - \tfrac{1}{N e}\big)\Big),
$$
com $\gamma \approx 0{,}5772$ (constante de Euler–Mascheroni), e o DSR é a probabilidade de o Sharpe verdadeiro superar $SR_0$:
$$
DSR = \Phi\!\left(\frac{(\widehat{SR} - SR_0)\sqrt{n-1}}{\sqrt{1 - \hat\gamma_3\,\widehat{SR} + \frac{\hat\gamma_4 - 1}{4}\,\widehat{SR}^2}}\right),
$$
onde $\hat\gamma_3$ e $\hat\gamma_4$ são a assimetria e a curtose dos resultados por trade. A Listagem 14.2 é a implementação.

```python
# Listagem 14.2 — tools/quant_research/analyze2.py
def dsr(p, sr_var, n_trials):
...
sr = p.mean() / p.std(ddof=1)
g3 = float(((p - p.mean()) ** 3).mean() / p.std() ** 3)
g4 = float(((p - p.mean()) ** 4).mean() / p.std() ** 4)
sr0 = math.sqrt(sr_var) * ((1 - GAMMA) * N01.inv_cdf(1 - 1 / n_trials)
+ GAMMA * N01.inv_cdf(1 - 1 / (n_trials * math.e)))
den = math.sqrt(max(1e-12, 1 - g3 * sr + (g4 - 1) / 4 * sr ** 2))
return float(N01.cdf((sr - sr0) * math.sqrt(n - 1) / den))
```

Duas escolhas de implementação foram registradas no protocolo. **(a)** $V[\widehat{SR}]$ usa o estimador robusto $1{,}4826\cdot\mathrm{MAD}$, porque a variância bruta é dominada por configurações degeneradas (Sharpe de −97 em regras que só pagam custo). O robusto é **menos** rigoroso, e por isso o relatório mostra os dois. **(b)** $N$ é o número de configurações testadas no timeframe, a escolha mais conservadora: como as variações de uma família são correlacionadas, o $N$ efetivo é menor. No caso A6 o DSR ia de 0,86 ($N$ = configurações) a 0,99 ($N$ = células símbolo × família), e foi esse caso de fronteira que motivou a faixa experimental (seção 14.7).

**5. FDR de Benjamini–Hochberg (calendário e *lead-lag*).** Para varreduras com milhares de células homogêneas, controla-se a proporção esperada de falsas descobertas entre as rejeitadas [Benjamini & Hochberg 1995]. Com os p-valores ordenados $p_{(1)} \le \dots \le p_{(m)}$, rejeitam-se as hipóteses $1..k$ com
$$k = \max\{\, i : p_{(i)} \le \tfrac{i}{m}\,q \,\}, \qquad q = 5\% .$$
Os sobreviventes do FDR no IS ainda precisam de t ≥ 2 e lucro no OOS, lucro em ≥ 70% dos anos e lucro com custo 1,5×.

**Viabilidade com US$ 16 (Monte Carlo).** Os trades OOS são reamostrados com reposição [Efron & Tibshirani 1993] em 5.000 trajetórias de dois anos, no ritmo histórico de trades. Há ruína quando o patrimônio fica abaixo da margem mais um stop. Exige-se perda mediana no stop ≤ US$ 1,60 e probabilidade de ruína < 5%.

## 14.6 Resultados

> Números da execução de 2026-10-24 com 133–136 ativos em D1/H4/H1, depois das seis correções da seção 14.4. O relatório completo e atualizável é `tools/quant_research/RESULTADOS2.md` (gerado por `report2.py`). A extensão para M15 e M30 está em execução e, quando terminar, atualiza esse relatório.

### Funil da grade de 28 famílias

| TF | Ativos | Configurações | Células (ativo × família) | 1: OOS forte | 1+2: IS também | 1–3: família robusta | 1–7 |
|---|---|---|---|---|---|---|---|
| D1 | 133 | 10.590 | 2.520 | 4 | 1 | 1 | 0 |
| H4 | 134 | 9.181 | 2.795 | 14 | 9 | 7 | 0 |
| H1 | 136 | 21.442 | 3.970 | 22 | 16 | 7 | 0 |
| **Total** | | **41.213** | **9.285** | **40** | **26** | **15** | **0** |

As 15 que chegaram aos testes 4–7 caíram todas no DSR, e 10 delas também na viabilidade: as mais lucrativas no OOS (AUDJPY D1 Pinbar +US$ 128, ETHCHF H4 Pinbar +US$ 157, AUDUSD H1 Bollinger intradiária +US$ 51) arriscam US$ 2–7 por trade, com probabilidade de ruína de 10–32% em dois anos com US$ 16.

### Placar por família

Para cada célula, o parâmetro é escolhido no IS e medido no OOS. Sem vantagem e sem custo, esperaríamos cerca de 50% de OOS positivo e t mediano perto de zero. Os custos deslocam tudo para baixo.

| Família | Células | OOS > 0 | t mediano OOS | Família | Células | OOS > 0 | t mediano OOS |
|---|---|---|---|---|---|---|---|
| ADXPB | 60 | 45% | −0,10 | PINBAR | 385 | 20% | −1,21 |
| BBMR | 403 | 32% | −0,57 | ENGULF | 216 | 19% | −1,27 |
| RSIn | 388 | 29% | −0,61 | MACD | 371 | 16% | −1,36 |
| OBVRSI | 276 | 33% | −0,71 | PULLB | 400 | 10% | −1,46 |
| RSI2 | 394 | 24% | −0,77 | IBS | 403 | 13% | −1,54 |
| ZSCORE | 403 | 25% | −0,89 | DONCH | 388 | 12% | −1,54 |
| CONSEC | 396 | 24% | −0,92 | TSMOM | 401 | 15% | −1,61 |
| MACROSS | 304 | 20% | −1,07 | INSIDE | 395 | 8% | −1,65 |
| TOM | 132 | 8% | −1,08 | KELTNER | 389 | 12% | −1,75 |
| DOUBLE7 | 402 | 19% | −1,08 | NR7 | 401 | 10% | −1,88 |
| VOLBRK | 349 | 18% | −1,08 | VWAP | 136 | 5% | −2,29 |
| SUPERT | 377 | 17% | −1,17 | DOW | 133 | 14% | −2,91 |
| GAPFADE | 378 | 24% | −1,20 | HOD | 136 | 22% | −3,05 |
| VOLCAP | 189 | 23% | −1,22 | ORB | 136 | 15% | −4,97 |

**Nenhuma família tem t mediano positivo.** As de reversão à média (Bollinger, RSI, z-score, OBV + IFR2) ficam no topo, o que concorda com a literatura sobre reversão de curto prazo em índices [Connors & Alvarez 2009], mas nem elas superam o custo de forma típica. As intradiárias de horário (HOD, ORB, VWAP) ficam no fundo: o movimento por trade é pequeno e o spread é o mesmo.

### Calendário, *lead-lag* e pares

| Varredura | Testado | Passaram o FDR no IS | Aprovados (OOS, estabilidade, custo 1,5×) |
|---|---|---|---|
| Hora × dia da semana × ativo, e dia útil do mês | 75.886 células | 2 | **0** |
| *Lead-lag* A → B (46 ativos, sinal e choques de 1 e 2 desvios) | 12.420 cruzamentos | 0 | **0** |
| Pares cointegrados (15 pares, D1) | 60 configurações | — | **0** (todos perdem no OOS) |

A sequência das varreduras de calendário é, por si só, um resultado metodológico: **64 → 3 → 0 → 0** "padrões" depois de cada correção de artefato (A4, A5, A6). Nenhum padrão sobreviveu à primeira cotação executável.

No *lead-lag*, só 164 de 12.420 cruzamentos (1,3%) têm movimento bruto médio maior que o custo médio, e nenhum é distinguível do acaso. Numa hora, a informação de um par já está nos outros, ou o resíduo é menor que o spread, o que é coerente com mercados de câmbio muito líquidos.

### As rotas atuais, revistas com o simulador corrigido

| Rota | Pesquisa anterior (IS / OOS) | Com as correções (IS / OOS) | Leitura |
|---|---|---|---|
| US500 D1 RSI2 | +3,26 / +9,93 | +2,87 / **+9,73** | Sobrevive; t OOS 3,2; efeito documentado, que na rodada 2 lucrou em 6 de 8 índices (cap. 8) |
| HK50 H4 PULLB | +5,72 / +4,21 | +3,31 / +2,93 | Encolhe ~40%; parte do lucro antigo vinha da abertura de sessão; t OOS ≈ 0,7 |

### Lucro na simulação × lucro possível

Na grade, **1.413 configurações** levaram US$ 16 a mais de US$ 50 no OOS, e 522 delas também lucraram no IS. As maiores (ETHJPY D1 Donchian +US$ 366, GBPUSD D1 MACD +US$ 298) têm risco de US$ 14–38 por trade e quedas de US$ 48–119 no caminho: o primeiro stop zera a conta real. O simulador "chega" ao lucro porque não quebra. É exatamente o que o critério 7 mede.

## 14.7 Faixa experimental e decisão sobre o LKQCorp

Antes da correção A6, o candidato "LKQCorp D1, comprar na sexta" passou nos critérios 1–5 e 7, com DSR entre 0,86 e 0,99 conforme o $N$ assumido. O dono perguntou se o limiar 0,95 podia mudar. A resposta registrada foi: **o limiar não muda depois de ver o resultado, mas casos de fronteira podem ser resolvidos com dados novos**. Ficou criada, no protocolo e antes da rodada final, uma faixa intermediária:

| Situação | Destino |
|---|---|
| Critérios 1–7 (DSR ≥ 0,95) | Rota ao vivo |
| 1–5 e 7, DSR entre 0,80 e 0,95 | **Experimental**: só `/study`, com sombra e CUSUM [Page 1954] (spec 011); promoção só com ≥ 30 trades novos e t ≥ 2 |
| Restante | Descartada |

Ao preparar o motor experimental, a checagem de artefatos encontrou A6: o "efeito sexta" era a abertura irreal do candle diário, presente em todos os dias da semana. **O motor não foi construído.** Hoje nenhuma estratégia está na faixa experimental. É o desfecho correto: a faixa existe para casos estatísticos de fronteira, não para defeitos de dados.

## 14.8 Discussão

**Por que nada sobreviveu?** Três forças se somam:

1. **Custo relativo.** Em 75.886 células de calendário, 92% têm movimento bruto médio menor que o custo médio. O spread é fixo por trade e o movimento útil encolhe com o horizonte, o que pune os timeframes curtos e as regras de horário.
2. **Eficiência no nível do varejo.** Regras públicas e simples (as 28 famílias são todas de livros e artigos) foram exploradas por décadas. Pela hipótese adaptativa [Lo 2004], o que sobra tende a ser menor que o custo de quem opera um lote de varejo.
3. **Múltiplos testes.** Com 41.213 configurações, "vencedoras" aparecem por acaso aos milhares. Os filtros da seção 14.5 existem para isso, e fizeram o trabalho esperado: eliminaram as candidatas sem eliminar o RSI2 do US500, que tem fundamento independente.

**O argumento da proporção (US$ 16 → US$ 10 mil).** Uma vantagem real por contrato escala com o número de contratos enquanto houver liquidez. A recíproca é a parte importante: o que não tem vantagem com US$ 16 também não tem com US$ 10 mil. O capital maior muda outra coisa, o **risco de ruína**. Com US$ 16, um stop do RSI2 no US500 custa 10% da conta; com US$ 1.600, 0,1%. A mesma vantagem, com muito menos chance de quebrar antes de se manifestar.

**Alavancar a banca matematicamente.** O critério de Kelly [Kelly 1956; Thorp 2006] dá a fração que maximiza o crescimento geométrico,
$$f^* = p - \frac{1-p}{b},$$
com $p$ a probabilidade de ganho e $b$ a razão ganho/perda. Ele **multiplica** uma vantagem: se $f^* \le 0$ (sem vantagem), a fração ótima é zero, e qualquer alavancagem aumenta a probabilidade de ruína sem aumentar o crescimento esperado. Não existe fórmula que crie vantagem por dimensionamento.

**O valor de um resultado negativo.** Para o projeto, a pesquisa evitou quatro motores que perderiam dinheiro (A3–A6), revelou um defeito sistemático nos dados da corretora e confirmou a única rota com evidência robusta. Para quem estuda, ela é um caso documentado de por que *backtests* de varejo costumam falhar ao vivo: a maioria dos "lucros" de pesquisa amadora está nos dados, não no mercado.

## 14.9 Engenharia de software da pesquisa

A pesquisa foi tratada como software de produção, porque decide onde vai o dinheiro.

| Prática | Implementação | Por quê |
|---|---|---|
| Pré-registro versionado | `tools/quant_research/PROTOCOLO2.md`, com adendos datados | Impede mover o critério depois de ver o resultado |
| Pipeline retomável | `tools/quant_research/pipeline2.py`; cada etapa pula o que já existe em `data/` (JSON Lines por ativo) | A coleta leva horas; queda de luz, fim de cota da IA ou terminal fechado não perdem trabalho |
| Estado legível | `tools/quant_research/ESTADO_PESQUISA.md`, atualizado e enviado ao GitHub a cada etapa | Qualquer pessoa ou IA retoma de onde parou |
| Simulador testado | `tests/test_research2.py`: swap triplo, stop antes do alvo, *gap*, spread do rollover, entrada depois de pausa, hora do rollover, ausência de *look-ahead* | Cada artefato corrigido vira regra com teste de regressão |
| Validação por reprodução | O simulador novo reproduz os números publicados da rodada anterior | Garante que diferenças vêm das correções, não de bugs da reescrita |
| Restrição de hardware | Células resumidas na hora (sem guardar vetores de trades); 3 processos | Máquina-alvo de 4 GB; a primeira versão da varredura de calendário usaria mais de 1 GB |
| Fonte independente para auditoria | Candles M1 e ticks bid/ask, consultados só para verificar suspeitos | Ticks são caros de baixar; usá-los como auditoria e não como base mantém o custo baixo |
| Separação pesquisa × produção | Nenhum script de pesquisa envia ordens; motores só nascem de candidatas aprovadas | O caminho da ordem (cap. 3) não depende de código exploratório |

O fluxo completo é:

```text
universe.py ─▶ fetch2.py ─▶ research2.py ─▶ analyze2.py ─▶ report2.py ─▶ RESULTADOS2.md
 (337 ativos)   (H1/D1/M15)  (28 famílias)   (critérios 1–7)
                    │
                    ├─▶ pairs2.py    (pares)
                    ├─▶ seasonal2.py (calendário, FDR)
                    └─▶ leadlag2.py  (A → B, FDR)
            auditoria de suspeitos: candles M1 e ticks bid/ask (só leitura)
```

## 14.10 Ameaças à validade específicas

- **Comissão de ações estimada** (A1). Um custo real maior só reforçaria o resultado negativo; um menor poderia reabrir alguns casos de ações, que exigem confirmação numa operação de teste.
- **Correções conservadoras podem esconder efeitos reais.** A regra "pior entre abertura e fechamento anterior" anula *gaps* verdadeiros nos índices. Estratégias de *gap* ficam subestimadas por construção.
- **Histórico curto no H1 e no M15** (cerca de 4–5 anos no H1 e 1–2 anos no M15 do forex). Efeitos raros ou de regime podem não aparecer.
- **Uma corretora.** Spreads, horários e o defeito de abertura (A4) são da Hantec; outra corretora é outro experimento.
- **Volume de ticks** não é volume real. As famílias de volume testam atividade de cotação, não fluxo de ordens.
- **$N$ efetivo do DSR** não é observável. A pesquisa usa o $N$ mais conservador e mostra a sensibilidade (seção 14.5).

## 14.11 Referencial teórico

[Fama 1970; Lo 2004] eficiência e adaptação dos mercados; [Sullivan, Timmermann & White 1999; White 2000; Harvey, Liu & Zhu 2016] *data snooping* e múltiplos testes em finanças; [Benjamini & Hochberg 1995] FDR; [Bailey & López de Prado 2014] Deflated Sharpe Ratio; [López de Prado 2018] *walk-forward*; [Efron & Tibshirani 1993] *bootstrap*; [Page 1954] CUSUM; [Nosek et al. 2018] pré-registro; [Kelly 1956; Thorp 2006] dimensionamento; [Connors & Alvarez 2009; De Bondt & Thaler 1985; Moskowitz, Ooi & Pedersen 2012; Brock, Lakonishok & LeBaron 1992; Nison 1991; Granville 1963; French 1980; Ariel 1987; Engle & Granger 1987; Gatev, Goetzmann & Rouwenhorst 2006] as famílias testadas.

