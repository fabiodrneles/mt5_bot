# 4. Indicadores técnicos

Os indicadores são calculados de forma vetorizada com pandas em `mt5bot/engine/indicators.py:add_all_indicators`, e de forma independente em `mt5bot/engine/quant_setups.py` para as rotas quant. Notação: $C_t, H_t, L_t$ = fechamento, máxima e mínima do candle $t$; $V_t$ = volume.

## 4.1 Médias móveis

**Média simples (SMA)**, `calculate_sma`:
$$SMA_n(t) = \frac{1}{n}\sum_{i=0}^{n-1} C_{t-i}$$

**Média exponencial (EMA)**, `calculate_ema`: `ewm(span=n, adjust=False)`:
$$EMA_n(t) = \alpha\, C_t + (1-\alpha)\,EMA_n(t-1), \qquad \alpha = \frac{2}{n+1}, \quad EMA_n(0) = C_0$$

Médias calculadas: EMA9, SMA13, SMA21, SMA28, EMA50, SMA50, SMA200 e a EMA12 deslocada 3 candles (`ema12_displaced`, usada no setup DiNapoli, ver [DiNapoli 1998]).

**Por que `adjust=False`?** Com `adjust=True` o pandas normaliza os pesos pela soma finita da série, o que muda os primeiros valores conforme o tamanho da janela carregada. A forma recursiva é a definição usada nas plataformas de trading [Murphy 1999], e torna o valor dependente apenas do histórico, não do recorte. O custo é o "aquecimento" discutido no cap. 3 §3.2.

**Inclinação:** `ema9_up` = $EMA9_t > EMA9_{t-1}$, e análogos para SMA21 e EMA50. São a base da família 9.x (cap. 5).

## 4.2 Índice de Força Relativa (IFR/RSI) de Wilder

`calculate_rsi` (períodos 2, 9 e 14):
$$G_t = \max(C_t - C_{t-1}, 0), \qquad P_t = \max(C_{t-1} - C_t, 0)$$
$$\bar G_t = \tfrac{1}{n} G_t + (1-\tfrac{1}{n})\bar G_{t-1}, \qquad \bar P_t \text{ análogo}$$
$$RSI_t = 100 - \frac{100}{1 + \bar G_t / \bar P_t}$$

A suavização usa $\alpha = 1/n$, a **média de Wilder** [Wilder 1978], e não a EMA comum ($\alpha = 2/(n+1)$). A diferença é relevante: com a EMA comum, um "IFR(14)" equivale aproximadamente a um IFR de Wilder de período 7,5. Usar a definição original mantém os níveis de referência (30/70, ou 5/95 no IFR2) com o mesmo significado da literatura que os propôs [Wilder 1978; Connors & Alvarez 2009].

## 4.3 Average True Range (ATR)

$$TR_t = \max\big(H_t - L_t,\; |H_t - C_{t-1}|,\; |L_t - C_{t-1}|\big)$$
$$ATR_t = \frac{(n-1)\,ATR_{t-1} + TR_t}{n}, \qquad ATR_{n-1} = \frac{1}{n}\sum_{i=0}^{n-1} TR_i$$

Implementado com semente pela média simples em `indicators.py:calculate_atr` (como em [Wilder 1978]) e com `ewm(alpha=1/n, min_periods=n)` em `quant_setups._atr`. As duas formas convergem: a diferença inicial decai como $(1-1/n)^k$, ou seja, abaixo de 0,01% após cerca de 120 candles para $n=14$. A equivalência das rotas quant com o backtest foi verificada vela a vela: 0 divergências em 4.600 candles (cap. 8 §8.6).

**Por que ATR para stops?** O ATR mede a volatilidade *absoluta* recente. Um stop em múltiplos de ATR se adapta ao regime: fica mais largo quando o mercado está nervoso e mais curto quando está calmo. Com isso, a probabilidade de o stop ser atingido por ruído fica aproximadamente constante entre regimes, ao contrário de um stop fixo em pontos [Wilder 1978; Kaufman 2013].

## 4.4 Bandas de Bollinger

`calculate_bollinger_bands` (20 períodos, 2 desvios):
$$M_t = SMA_{20}(t), \qquad U_t, D_t = M_t \pm 2\,\sigma_{20}(t)$$
com $\sigma$ = desvio-padrão **amostral** (`rolling().std()`, ddof=1). Bollinger usa o desvio populacional [Bollinger 2001]; com $n=20$, o fator entre os dois é $\sqrt{20/19} \approx 1{,}026$, ou seja, as bandas do projeto são cerca de 2,6% mais largas. A diferença não afeta a validação, que foi feita com a mesma implementação.

Uso: o Setup Russo (reversão à média, cap. 5) e o FFFD.

## 4.5 ADX (Average Directional Index)

`calculate_adx`: movimentos direcionais $+DM_t = H_t - H_{t-1}$ e $-DM_t = L_{t-1} - L_t$, cada um mantido só quando é o maior dos dois e positivo. Depois:
$$+DI = 100\,\frac{\widetilde{+DM}}{\widetilde{TR}}, \quad -DI = 100\,\frac{\widetilde{-DM}}{\widetilde{TR}}, \quad DX = 100\,\frac{|{+DI} - {-DI}|}{{+DI} + {-DI}}, \quad ADX = \widetilde{DX}$$
onde $\widetilde{\cdot}$ é a média de Wilder de 14 períodos [Wilder 1978]. O ADX mede **força** de tendência, não direção, e entra como *feature* do modelo de ML (cap. 7).

## 4.6 SAR Parabólico

`calculate_sar`, com aceleração inicial 0,02, incremento 0,02 e máximo 0,20 [Wilder 1978]:
$$SAR_{t+1} = SAR_t + AF\,(EP - SAR_t)$$
em que $EP$ é o ponto extremo da tendência corrente. O fator $AF$ cresce 0,02 a cada novo extremo, até 0,20, e a tendência inverte quando o preço cruza o SAR. É usado no setup SAR (cap. 5).

## 4.7 Volume: RVOL e VWAP

**Volume relativo** (`calculate_rvol`):
$$RVOL_t = \frac{V_t}{\frac{1}{20}\sum_{i=1}^{20} V_{t-i}}$$
Usa o volume real quando existe (bolsa) e o *tick volume* nos demais casos (Forex e CFDs, onde não há volume centralizado). O filtro exige $RVOL \ge 1{,}15$.

**VWAP** (`calculate_vwap`): preço típico $TP = (H+L+C)/3$, **ancorado por dia**:
$$VWAP_t = \frac{\sum_{i \in \text{dia}(t),\, i \le t} TP_i V_i}{\sum_{i \in \text{dia}(t),\, i \le t} V_i}$$
Quando não há coluna de tempo, cai para uma janela móvel de 200 candles. O filtro de VWAP veta entradas muito esticadas: $|C - VWAP| > 2\,ATR$.

**Limitação.** Em CFDs, o *tick volume* conta mudanças de preço, não contratos negociados; ele é só uma *proxy* de atividade.

## 4.8 Estatísticas e *features*

- **Z-score de 21 períodos:** $z_t = (C_t - SMA_{21})/\sigma_{21}$, com desvio populacional (ddof=0).
- **Retornos logarítmicos** $r_t = \ln(C_t/C_{t-1})$, sinais defasados $\text{sign}(r_{t-k})$ para $k=1,2,3$ e a volatilidade móvel $\sigma_{10}(r)$, conforme os padrões de [Hilpisch 2018]. São *features* do XGBoost (cap. 7).

## 4.9 Níveis de swing e extensões de Fibonacci

`swing_levels`: a máxima e a mínima dos últimos 20 candles. `fib_extension_targets`: com amplitude $A = H_{\max} - L_{\min}$, os alvos de compra são $E + A$ e $E + 1{,}618\,A$ (simétricos na venda). Esses alvos entram no contexto do ML e da simulação de estudo.

## 4.10 Filtros de contexto (caminho clássico)

| Filtro | Regra (compra; venda espelhada) | Código |
|---|---|---|
| SMA200 | $C_t > SMA_{200}$ | `strategy.py` (fim de `evaluate_all`) |
| MM50 | $C_t > SMA_{50}$ | `check_mm50_filter` |
| IFR9 | IFR9 saindo de ≤ 30 (bônus no *score*) | `check_ifr9_filter` |
| VWAP | $|C - VWAP| \le 2\,ATR$ | `check_vwap_filter` |
| Multi-timeframe | No timeframe superior (H1→D1, H4→D1, M15→H1…): EMA9 ≥ EMA21 e EMA9 subindo | `check_mtf_trend` |
| RVOL | $RVOL \ge 1{,}15$ | `check_rvol_filter` |

Todos são **permissivos na falta de dados** (devolvem "favorável"): faltar uma coluna nunca bloqueia uma operação por acidente. **Limitação:** essa escolha também pode deixar passar uma operação que deveria ser filtrada. É um *trade-off* consciente entre disponibilidade e rigor, e não se aplica às rotas quant, que não usam esses filtros.

## 4.11 Por que vetorizado?

Calcular com operações de coluna do pandas/NumPy, em vez de laços Python, é ordens de grandeza mais rápido [Hilpisch 2018; McKinney 2017]. Isso importa num i3 que recalcula 400 candles por ativo. As exceções (ATR com semente e SAR) são recursões com dependência entre passos, impossíveis de vetorizar diretamente.

## 4.12 Referencial teórico

[Wilder 1978] RSI, ATR, ADX, SAR; [Bollinger 2001] bandas; [Murphy 1999] e [Kaufman 2013] análise técnica e sistemas; [DiNapoli 1998] médias deslocadas; [Hilpisch 2018] e [McKinney 2017] computação vetorizada.
