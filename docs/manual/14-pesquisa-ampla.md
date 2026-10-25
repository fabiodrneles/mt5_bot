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

### Biblioteca de regras (28 famílias + 3 propostas pelo dono)

| Grupo | Famílias | Ideia testada | Referência |
|---|---|---|---|
| Reversão à média | RSI2, RSIn, IBS, quedas seguidas, Double-7, Bollinger, z-score, *gap fade* | Excessos de curto prazo se corrigem | [Connors & Alvarez 2009; De Bondt & Thaler 1985] |
| Tendência e momento | Donchian, cruzamento de médias, TSMOM, MACD, Keltner, Supertrend, ADX + DI, pullback na EMA20 | Movimentos persistem | [Moskowitz, Ooi & Pedersen 2012; Brock, Lakonishok & LeBaron 1992] |
| Padrões de candle | NR7, *inside bar*, engolfo na banda, martelo/estrela | Formações de reversão/rompimento | [Nison 1991] |
| Volume e fluxo | Pico de volume (capitulação), rompimento com volume, OBV + IFR2, VWAP intradiário, faixa de abertura (ORB) | Atividade anormal antecede movimento | [Granville 1963] |
| Calendário | Virada do mês, dia da semana, hora do dia | Sazonalidades | [French 1980; Ariel 1987] |
| Estatística entre ativos | Pares cointegrados (z-score do spread log); *lead-lag* (A antecipa B) | Relações de equilíbrio e difusão de informação | [Engle & Granger 1987; Gatev, Goetzmann & Rouwenhorst 2006] |
| Propostas pelo dono (seção 14.8) | EMA9X (cruzamento da MME9, risco = candle), EMA9REV (reversão após tendência forte), HORNER (onda da MME34 com ângulo) | Leitura visual de gráfico transformada em regra | [Horner 2005] |

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

O simulador reproduz a pesquisa anterior antes das correções (HK50 H4 PULLB: 277 trades e +US$ 9,93 contra +US$ 9,96 publicados; US500 D1 RSI2: 54 trades e +US$ 13,18 contra +US$ 13,19), o que valida a reimplementação. Os testes em `tests/test_research2.py` fixam as regras: rolagem tripla, stop antes do alvo, saída no *gap*, spread do rollover, entrada depois de pausa, nenhuma entrada na hora do rollover e **ausência de *look-ahead***. Este último altera o futuro de uma série sintética e exige que os sinais do passado não mudem, em todas as famílias.

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

> Execução completa de 2026-10-24: 331–337 ativos em D1, H4 e H1 e 88 ativos (forex, índices, commodities e cripto) em M30 e M15, com as 31 famílias e depois das seis correções da seção 14.4. O relatório completo e atualizável é `tools/quant_research/RESULTADOS2.md` (gerado por `report2.py`).

### Funil da grade

| TF | Ativos | Configurações | Células (ativo × família) | 1: OOS forte | 1+2: IS também | 1–3: família robusta | 1–7 |
|---|---|---|---|---|---|---|---|
| D1 | 331 | 30.098 | 6.756 | 5 | 1 | 1 | 0 |
| H4 | 331 | 26.706 | 7.806 | 20 | 10 | 8 | 0 |
| H1 | 337 | 52.721 | 10.832 | 26 | 18 | 8 | 0 |
| M30 | 88 | 9.254 | 2.685 | 8 | 7 | 5 | 0 |
| M15 | 88 | 9.297 | 2.723 | 7 | 5 | 5 | 0 |
| **Total** | | **128.076** | **30.802** | **66** | **41** | **27** | **0** |

As 27 células que chegaram aos testes 4–7 caíram **todas** no DSR (o maior foi 0,049). A maioria também caiu na viabilidade: as mais lucrativas no OOS (ETHCHF H4 Pinbar +US$ 157, AUDJPY D1 Pinbar +US$ 128, USDHUF H4 RSI3 +US$ 118) arriscam de US$ 5 a US$ 12 por trade, com ruína de 25–54% em dois anos com US$ 16. A melhor em estatística t (USDCAD M15 Double-7, t 3,59, risco US$ 1,10) tem DSR ≈ 0 diante das 9.297 configurações testadas no M15.

### Placar por família

Para cada célula, o parâmetro é escolhido no IS e medido no OOS. Sem vantagem e sem custo, esperaríamos cerca de 50% de OOS positivo e t mediano perto de zero. Os custos deslocam tudo para baixo.

| Família | Células | OOS > 0 | t mediano OOS | Família | Células | OOS > 0 | t mediano OOS |
|---|---|---|---|---|---|---|---|
| ADXPB | 303 | 39% | −0,48 | BBMR_I | 513 | 13% | −1,51 |
| BBMR | 1.173 | 25% | −0,79 | PINBAR | 1.128 | 14% | −1,52 |
| RSIn | 1.148 | 24% | −0,83 | MACD | 1.116 | 13% | −1,53 |
| EMA9REV | 930 | 26% | −0,84 | PULLB | 1.163 | 10% | −1,55 |
| OBVRSI | 822 | 25% | −0,90 | KELTNER | 1.154 | 10% | −1,59 |
| HORNER | 820 | 18% | −1,02 | TSMOM | 1.167 | 14% | −1,63 |
| VOLBRK | 1.000 | 20% | −1,03 | GAPFADE | 1.060 | 14% | −1,74 |
| TOM | 327 | 11% | −1,06 | INSIDE | 1.157 | 7% | −2,04 |
| MACROSS | 912 | 21% | −1,08 | RSI2_I | 513 | 8% | −2,10 |
| RSI2 | 1.157 | 20% | −1,10 | IBS | 1.175 | 8% | −2,12 |
| ZSCORE | 1.175 | 19% | −1,13 | NR7 | 1.170 | 7% | −2,20 |
| SUPERT | 1.121 | 18% | −1,17 | VWAP | 512 | 7% | −2,59 |
| CONSEC | 1.158 | 16% | −1,23 | ZSCORE_I | 513 | 7% | −2,92 |
| VOLCAP | 545 | 20% | −1,29 | DOW | 331 | 7% | −3,48 |
| EMA9X | 1.171 | 16% | −1,31 | HOD | 337 | 10% | −5,16 |
| DOUBLE7 | 1.170 | 14% | −1,34 | ORB | 513 | 7% | −5,52 |
| ENGULF | 683 | 15% | −1,37 | IBS_I | 513 | 4% | −5,86 |
| DONCH | 1.152 | 14% | −1,45 |  | | |  |

**Nenhuma das 35 famílias (31 regras mais 4 variantes intradiárias `_I`) tem t mediano positivo.** As de reversão à média (ADX com recuo, Bollinger, RSI) e as do dono (EMA9REV, HORNER) ficam no terço superior, mas nem elas superam o custo de forma típica. As intradiárias de horário (HOD, ORB, VWAP) e as variantes que fecham no fim do dia ficam no fundo: o movimento por trade é pequeno e o spread é o mesmo.

### Calendário, *lead-lag* e pares

| Varredura | Testado | Passaram o FDR no IS | Aprovados (OOS, estabilidade, custo 1,5×) |
|---|---|---|---|
| Hora × dia da semana × ativo, e dia útil do mês | 136.864 células | 20 | **1**: USDJPY, comprar na segunda às 01h do servidor por 1 hora (t OOS 2,19; positivo em todos os anos) |
| *Lead-lag* A → B (sinal e choques de 1 e 2 desvios) | 45.918 cruzamentos | 0 | **0** |
| Pares cointegrados (15 pares, D1) | 60 configurações | — | **0** (todos perdem no OOS) |

A sequência das varreduras de calendário é, por si só, um resultado metodológico: **64 → 3 → 0** "padrões" depois de cada correção de artefato (A4, A5, A6), e **1** na rodada final com o universo inteiro. Esse sobrevivente foi auditado com ticks reais, como os anteriores. Às 01h de segunda o spread do USDJPY já está normal (1 ponto), então ele **não** é um artefato de custo. Nas quatro segundas mais recentes, o resultado executável foi de +306, −90, −13 e −83 pontos. Sendo 1 sobrevivente entre 136.864 testes, com FDR de 5% e 20 rejeições no IS, uma descoberta falsa é o esperado. Ele é candidato à **faixa experimental** (seção 14.7): estudo ao vivo sem dinheiro, não rota. Na v3.2.0 ele entrou como rota em estudo (`config.QUANT_ROUTES["USDJPY"]`, setup `HOUR` em `mt5bot/engine/quant_setups.py`, com SL protetor de 3 ATR e saída depois de 1 candle). Só vira rota de verdade com ≥ 30 segundas novas e t ≥ 2 no estudo.

### As rotas atuais, revistas com o simulador corrigido

| Rota | Pesquisa anterior (IS / OOS) | Com as correções (IS / OOS) | Leitura |
|---|---|---|---|
| US500 D1 RSI2 | +3,26 / +9,93 | +2,87 / **+9,73** | Sobrevive; t OOS 3,2; generaliza para os índices americanos (seção 14.9) |
| HK50 H4 PULLB | +5,72 / +4,21 | +3,31 / +2,93 | Encolhe ~40%; parte do lucro antigo vinha da abertura de sessão; t OOS ≈ 0,7 |

### Lucro na simulação × lucro possível

Na grade completa, **2.000 configurações** levaram US$ 16 a mais de US$ 50 no OOS, e 733 delas também lucraram no IS. As maiores têm risco de US$ 5–38 por trade e quedas de dezenas de dólares no caminho: o primeiro stop zera a conta real. O simulador "chega" ao lucro porque não quebra. É exatamente o que o critério 7 mede.

## 14.7 Faixa experimental e decisão sobre o LKQCorp

Antes da correção A6, o candidato "LKQCorp D1, comprar na sexta" passou nos critérios 1–5 e 7, com DSR entre 0,86 e 0,99 conforme o $N$ assumido. O dono perguntou se o limiar 0,95 podia mudar. A resposta registrada foi: **o limiar não muda depois de ver o resultado, mas casos de fronteira podem ser resolvidos com dados novos**. Ficou criada, no protocolo e antes da rodada final, uma faixa intermediária:

| Situação | Destino |
|---|---|
| Critérios 1–7 (DSR ≥ 0,95) | Rota ao vivo |
| 1–5 e 7, DSR entre 0,80 e 0,95 | **Experimental**: só `/study`, com sombra e CUSUM [Page 1954] (spec 011); promoção só com ≥ 30 trades novos e t ≥ 2 |
| Restante | Descartada |

Ao preparar o motor experimental, a checagem de artefatos encontrou A6: o "efeito sexta" era a abertura irreal do candle diário, presente em todos os dias da semana. **O motor não foi construído.** Hoje nenhuma estratégia está na faixa experimental. É o desfecho correto: a faixa existe para casos estatísticos de fronteira, não para defeitos de dados.

## 14.8 Estudo de caso: a regra da MME9 trazida pelo dono

Durante a pesquisa, o dono apresentou um trade real como contraexemplo: *US500 M15, 23/10/2026, o candle de venda fecha abaixo da MME9 e a operação paga 2 vezes o risco*. Ele questionou como tantos cálculos não tinham visto isso. O caso foi tratado como hipótese e testado em cinco versões sucessivas, cada uma incorporando um refinamento proposto por ele. É o gatilho do setup 9.1 de Larry Williams (cap. 5). As ferramentas ficaram em `tools/quant_research/` e reproduzem cada número abaixo.

| Versão | Refinamento do dono | Ferramenta | Resultado (US500 M15, sinais avaliados um a um) |
|---|---|---|---|
| 1 | Candle fecha cruzando a MME9; alvo 2× o tamanho do candle | `check_ema9.py` | O trade citado existe e pagou +US$ 0,09. No mesmo dia houve 20 sinais e só 2 atingiram o alvo. No histórico (1.994 trades): acerto 32,9% contra 33,3% de empate, −US$ 19,09, e −US$ 7,65 mesmo sem spread |
| 2 | Stop na máxima/mínima do candle; filtros de volume, tendência e tempos maiores (M30, H1, H4 fechados) | `check_ema9_filters.py` | 135 combinações; 10 de 130 lucram no IS e no OOS. A escolhida no IS (+US$ 4,49) dá −US$ 0,05 no OOS. Multi-tempo alinhado: acerto 32,9%, ainda abaixo do empate |
| 3 | "Máquina do tempo": achar a combinação que seleciona só os vencedores | `signal_mining.py` | Entre 19.286 regras, 4 selecionam exatamente os 2 vencedores do dia; nos outros dias, as 4 perdem (−US$ 3,50 a −US$ 37,50). A regra aprendida nos 60% iniciais: IS +US$ 8,44 → OOS −US$ 3,68 |
| 4 | Só reversão depois de tendência forte; lateralização percebida pela sequência de stops; "assinatura" dos vencedores | `check_reversal.py`, `check_signature.py` | 72 definições de tendência forte em 15 ativo × timeframe: nenhuma com t ≥ 2 no OOS. k-NN sobre sinais passados, pausa após stops e filtros de regime (Kaufman, Choppiness): 0 variações lucram no IS e no OOS |
| 5 | Basta "algum lucro"; força pelo ângulo do relógio (Raghee Horner) | `check_exits.py`, `check_clock.py`, `check_horner.py` | 55–65% dos sinais chegam a ficar ≥ 1 centavo no lucro antes do stop, mas nenhuma regra de saída fixada antes embolsa isso: "1º fechamento no lucro" acerta 54%, ganha US$ 0,042 e perde US$ 0,077. Onda da MME34 com ângulo e entrada a favor [Horner 2005]: 0 variações robustas, exceto GBPUSD H1 (5 de 20 lucram nos dois períodos; t ≤ 0,8) |

Três observações têm valor didático:

1. **Os próprios exemplos contradizem o critério.** Nos três sinais citados como "bom" e "ruim", o "ruim" foi o que teve a maior tendência anterior medida (ADX 39; +15 ATR em 40 candles) e também ganhou. O "bom" de 16/10 estava deitado no relógio (3h). O critério visual existe, mas não coincide com as medidas objetivas testadas.
2. **Com N regras e poucos casos, a separação perfeita é garantida.** Com 16 sinais num dia e 19 mil regras, sempre há uma combinação que isola os 2 vencedores. É combinatória, não previsão. O teste é escolher a regra sem ver o período seguinte (Parte B), e ele dá zero.
3. **O olho vê o que o gráfico mostra depois.** A maioria dos sinais passa pelo lucro antes do stop. Isso é verdade, mas não é executável sem saber, de antemão, onde sair.

**O teste justo do 9.x.** As cinco versões acima são simplificações para robô: intradiário, entrada a mercado e alvo fixo. O Palex opera ações no **diário**, com **ordem stop** acima da máxima e **saída conduzida pela MME9** (cap. 5). Essa versão fiel foi testada em 166 ativos (`tools/quant_research/check_9x_fiel.py`, relatório em `docs/validacao-9x-fiel.md`). Nas ações e índices americanos, no período recente e sem o custo de financiamento, o 9.1, o 9.2 e o 9.4 ficam **no empate** (−0,03 a +0,03 R por trade, t ≈ 0), muito melhor que a versão simplificada. Com o **swap** do CFD (7 a 10 dias por trade), o empate vira prejuízo; ações à vista na B3 não pagam esse custo. No forex a família perde em qualquer versão, e o 9.3 perde em todos os mercados. A conclusão correta não é "o 9.x não funciona". É: mecanicamente ele empata antes do financiamento, então qualquer vantagem de quem lucra com ele tende a vir do mercado à vista e da seleção dos sinais, que não estão nas regras mecânicas.

**E na B3?** Com dados públicos ajustados de 59 ações líquidas do Ibovespa (cerca de 20 anos, sem swap), o 9.x fiel dá lucro na compra com saída pela MME9: o 9.1 com congruência semanal faz +0,09 R por trade nos dois períodos. Mas o resultado deixa de ser significativo quando agregado por mês (t 0,35), e **entradas aleatórias** nos mesmos dias de tendência, com a mesma saída, rendem em média +0,16 R. O lucro vem da tendência de alta das ações brasileiras e da condução pela MME9, não do gatilho do candle (`docs/validacao-9x-fiel.md`). Em carteira, com o dinheiro fora da posição aplicado no CDI, o 9.1 rende 9,9% ao ano desde 2005, contra 10,6% do CDI e 9,9% do Ibovespa, com queda máxima de só 7,9%. Ele reduz o risco, mas não acrescenta retorno acima da renda fixa.

**Os outros setups do Palex.** Catorze setups mecânicos do livro foram testados da mesma forma em forex e na B3 (`tools/quant_research/palex_setups.py`, relatório em `docs/validacao-palex.md`). No **forex, todos perdem**. Na **B3, as compras ganham e as vendas perdem**, a assinatura da tendência de alta. Em carteira, o **cruzamento MM9 × MM21** rende 16,4% ao ano desde 2005 (19,6% desde 2016), com queda máxima de 15%. Contra uma exposição equivalente às mesmas ações (55% ações + 45% CDI), ele tem Sharpe igual ou maior e **metade da queda máxima**, o comportamento clássico do *timing* por médias móveis [Faber 2007]. É o setup do livro com valor comprovado neste teste, e o candidato natural a uma rota da B3 em modo estudo.

A resposta de engenharia não foi descartar a intuição do operador. Foi criar um instrumento para medi-la sem viés: o **diário de sinais** (cap. 9 §9.7). Se o olho tiver vantagem, ela aparece em sinais anotados antes do resultado, e o motivo escrito em cada anotação vira a especificação da regra a ser testada aqui. As famílias 29 (EMA9X), 30 (EMA9REV) e 31 (HORNER) também entraram na grade completa, para passar pelos sete critérios em todos os ativos.

## 14.9 RSI2 nos índices e a rota US100 em estudo

A regra RSI2 da rota US500, **sem mudar nenhum parâmetro**, foi aplicada a todos os índices de margem baixa com o simulador corrigido:

| Índice | Trades (≈10 anos) | Acerto | Resultado | t | Risco por trade |
|---|---|---|---|---|---|
| US500 | 54 | 70% | +US$ 12,60 | 2,48 | US$ 1,21 |
| US100 | 55 | 73% | +US$ 51,39 | 2,10 | US$ 5,20 |
| US30 | 89 | 65% | +US$ 49,99 | 1,14 | US$ 7,24 |
| JP225 | 49 | 69% | +US$ 2,72 | 0,81 | US$ 0,64 |
| Europa, Ásia e Austrália (12 índices) | — | — | 4 positivos, 8 negativos | ≤ 0,3 | — |

O efeito é consistente **nos índices americanos** e fraco nos demais. Aplicar a mesma regra a outros mercados, sem reotimizar, é um teste de generalidade e não uma busca: ele não aumenta o número de tentativas no sentido da seção 14.5.

Com US$ 16, o US100 não cabe: um stop custa cerca de um terço da conta. A solução de engenharia foi o **modo estudo** das rotas quant (`mode = "study"` em `config.QUANT_ROUTES`). A rota usa o mesmo sinal, a mesma janela de entrada (`quant_manager.entry_window`, compartilhada com as rotas ao vivo) e a mesma regra de saída, mas a posição é virtual e nada é enviado ao MT5 (`mt5bot/execution/quant_study.py`, testes em `tests/test_quant_study.py`). As operações ficam em `quant_study.json`. Quando o saldo comportar (≈ US$ 52 para 10% por stop), basta `mode = "live"` no `config.toml`, depois de comparar o estudo ao vivo com o histórico (spec 011).

O plano de crescimento resultante é escalonado: US500 agora; US100 com ≈ US$ 52; US30 com ≈ US$ 72. Ele não aumenta o risco por trade. A mesma vantagem por contrato passa a valer em mais mercados à medida que a conta permite.

## 14.10 Discussão

**Por que nada sobreviveu?** Três forças se somam:

1. **Custo relativo.** Na varredura de calendário, cerca de 90% das células têm movimento bruto médio menor que o custo médio. O spread é fixo por trade e o movimento útil encolhe com o horizonte, o que pune os timeframes curtos e as regras de horário.
2. **Eficiência no nível do varejo.** Regras públicas e simples (as 28 famílias são todas de livros e artigos) foram exploradas por décadas. Pela hipótese adaptativa [Lo 2004], o que sobra tende a ser menor que o custo de quem opera um lote de varejo.
3. **Múltiplos testes.** Com 128.076 configurações, "vencedoras" aparecem por acaso aos milhares. Os filtros da seção 14.5 existem para isso, e fizeram o trabalho esperado: eliminaram as candidatas sem eliminar o RSI2 do US500, que tem fundamento independente.

**O argumento da proporção (US$ 16 → US$ 10 mil).** Uma vantagem real por contrato escala com o número de contratos enquanto houver liquidez. A recíproca é a parte importante: o que não tem vantagem com US$ 16 também não tem com US$ 10 mil. O capital maior muda outra coisa, o **risco de ruína**. Com US$ 16, um stop do RSI2 no US500 custa 10% da conta; com US$ 1.600, 0,1%. A mesma vantagem, com muito menos chance de quebrar antes de se manifestar.

**Alavancar a banca matematicamente.** O critério de Kelly [Kelly 1956; Thorp 2006] dá a fração que maximiza o crescimento geométrico,
$$f^* = p - \frac{1-p}{b},$$
com $p$ a probabilidade de ganho e $b$ a razão ganho/perda. Ele **multiplica** uma vantagem: se $f^* \le 0$ (sem vantagem), a fração ótima é zero, e qualquer alavancagem aumenta a probabilidade de ruína sem aumentar o crescimento esperado. Não existe fórmula que crie vantagem por dimensionamento.

**O valor de um resultado negativo.** Para o projeto, a pesquisa evitou quatro motores que perderiam dinheiro (A3–A6), revelou um defeito sistemático nos dados da corretora e confirmou a única rota com evidência robusta. Para quem estuda, ela é um caso documentado de por que *backtests* de varejo costumam falhar ao vivo: a maioria dos "lucros" de pesquisa amadora está nos dados, não no mercado.

## 14.11 Engenharia de software da pesquisa

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

## 14.12 Ameaças à validade específicas

- **Comissão de ações estimada** (A1). Um custo real maior só reforçaria o resultado negativo; um menor poderia reabrir alguns casos de ações, que exigem confirmação numa operação de teste.
- **Correções conservadoras podem esconder efeitos reais.** A regra "pior entre abertura e fechamento anterior" anula *gaps* verdadeiros nos índices. Estratégias de *gap* ficam subestimadas por construção.
- **Histórico curto no H1 e no M15** (cerca de 4–5 anos no H1 e 1–2 anos no M15 do forex). Efeitos raros ou de regime podem não aparecer.
- **Uma corretora.** Spreads, horários e o defeito de abertura (A4) são da Hantec; outra corretora é outro experimento.
- **Volume de ticks** não é volume real. As famílias de volume testam atividade de cotação, não fluxo de ordens.
- **$N$ efetivo do DSR** não é observável. A pesquisa usa o $N$ mais conservador e mostra a sensibilidade (seção 14.5).

## 14.13 Referencial teórico

[Fama 1970; Lo 2004] eficiência e adaptação dos mercados; [Sullivan, Timmermann & White 1999; White 2000; Harvey, Liu & Zhu 2016] *data snooping* e múltiplos testes em finanças; [Benjamini & Hochberg 1995] FDR; [Bailey & López de Prado 2014] Deflated Sharpe Ratio; [López de Prado 2018] *walk-forward*; [Efron & Tibshirani 1993] *bootstrap*; [Page 1954] CUSUM; [Nosek et al. 2018] pré-registro; [Kelly 1956; Thorp 2006] dimensionamento; [Horner 2005] onda da MME34 e ângulo da tendência; [Connors & Alvarez 2009; De Bondt & Thaler 1985; Moskowitz, Ooi & Pedersen 2012; Brock, Lakonishok & LeBaron 1992; Nison 1991; Granville 1963; French 1980; Ariel 1987; Engle & Granger 1987; Gatev, Goetzmann & Rouwenhorst 2006] as famílias testadas.

