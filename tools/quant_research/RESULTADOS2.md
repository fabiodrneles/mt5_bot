# Resultados da pesquisa ampla (rodada 3)

> Gerado por `report2.py`. Protocolo registrado antes dos resultados: [PROTOCOLO2.md](PROTOCOLO2.md).
> Valores em US$ no **lote mínimo**, com spread, comissão e swap. Passado não garante futuro.

## O que foi testado

| TF | Símbolos | Configurações | Desvio do Sharpe/trade entre configurações |
|---|---|---|---|
| D1 | 91 | 7.258 | 0.1531 |
| H4 | 92 | 6.314 | 0.1451 |
| H1 | 93 | 13.576 | 0.1748 |

Total: **27.148 configurações**.

## Funil dos critérios

| TF | Células (símbolo × família) | 1: OOS forte | 1+2: IS também | 1+2+3: família robusta |
|---|---|---|---|---|
| D1 | 1714 | 10 | 8 | 5 |
| H4 | 1903 | 5 | 4 | 3 |
| H1 | 2711 | 13 | 11 | 5 |

Passaram 1–3 e foram para os testes 4–7: **13**. Aprovadas em todos os 7: **0**.

## Aprovadas nos 7 critérios

Nenhuma.

## Promissoras (passaram 1–3, falharam em algum de 4–7)

| Símbolo | TF | Família | Parâmetros | OOS trades | OOS lucro | OOS PF | t | Custo 1,5× | Walk-forward (5 dobras) | DSR | Risco/trade | Ruína 2 anos | Generaliza | Falhou |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LKQCorp | D1 | DOW | wd=4, side=1 | 155 | +3.62 | 2.39 | 3.9 | +3.17 | +5.62 / +6.13 / +6.96 / +1.69 / +0.24 | 0.865 | $0.328 | 0.0% | 20/55 | c6 |
| NuveenNAS | D1 | GAPFADE | g=0.5 | 93 | +1.90 | 2.44 | 3.39 | +1.35 | +2.36 / +2.07 / +2.90 / +1.45 / -0.24 | 0.28 | $0.164 | 0.0% | 17/55 | c6 |
| AUDUSD | H1 | BBMR_I | dev=2.5, sma200=True | 100 | +50.60 | 1.95 | 2.64 | +48.39 | -0.58 / +13.31 / +15.11 / +19.10 / +19.66 | 0.0 | $2.409 | 1.9% | 0/0 | c6, c7 |
| AUDJPY | D1 | PINBAR | R=1.5 | 41 | +128.77 | 2.34 | 2.59 | +125.97 | +65.67 / +6.87 / +17.33 / +81.99 / +36.72 | 0.002 | $5.437 | 25.1% | 1/3 | c6, c7 |
| Sunrun | H1 | BBMR | dev=2.0, sma200=False | 80 | +2.18 | 1.93 | 2.36 | +1.90 | -0.34 / +0.57 / +2.42 / +0.44 / +0.45 | 0.0 | $0.089 | 0.0% | 8/56 | c6 |
| Sunrun | H1 | ZSCORE | z=2.0, k=2.0 | 80 | +2.18 | 1.93 | 2.36 | +1.90 | -0.34 / +0.02 / +2.42 / +0.44 / +0.48 | 0.0 | $0.089 | 0.0% | 8/56 | c6 |
| TripAdvis | D1 | DOW | wd=4, side=1 | 149 | +1.20 | 1.7 | 2.31 | +0.90 | -0.91 / +1.98 / +1.26 / +0.35 / +0.05 | 0.0 | $0.209 | 0.0% | 20/55 | c6 |
| ETHCAD | H4 | PINBAR | R=1.5 | 59 | +163.16 | 2.04 | 2.28 | +159.09 | +16.43 / +17.88 / +164.98 / +93.02 / +26.50 | 0.0 | $4.974 | 36.7% | 4/17 | c6, c7 |
| AUDCAD | H1 | GAPFADE | g=1.0 | 58 | +18.01 | 2.2 | 2.12 | +11.25 | +1.37 / -3.26 / +2.16 / +2.24 / +13.71 | 0.0 | $1.622 | 0.0% | 1/3 | c6, c7 |
| AUDCAD | H4 | BBMR | dev=2.0, sma200=False | 143 | +81.44 | 1.48 | 2.11 | +79.08 | +36.52 / +17.11 / +6.51 / +18.57 / +42.06 | 0.0 | $3.649 | 25.0% | 1/3 | c6, c7 |
| AUDCAD | H4 | ZSCORE | z=2.0, k=2.0 | 143 | +81.44 | 1.48 | 2.11 | +79.08 | +49.64 / -0.74 / +50.75 / +1.39 / +38.33 | 0.0 | $3.649 | 25.0% | 1/3 | c6, c7 |
| ManU | D1 | GAPFADE | g=0.5 | 66 | +0.77 | 1.89 | 2.02 | +0.54 | +0.18 / -0.37 / +0.21 / +0.62 / +0.27 | 0.0 | $0.086 | 0.0% | 17/55 | c6 |
| AUDUSD | H1 | RSIn | N=4, L=10 | 64 | +41.28 | 1.86 | 2.02 | +40.65 | -1.58 / -19.20 / +21.14 / +14.65 / +13.04 | 0.0 | $3.053 | 7.4% | 0/0 | c6, c7 |

Legenda das falhas: c4 = não sobrevive a custo 1,5×; c5 = *walk-forward* fraco; c6 = Deflated Sharpe < 0,95 (pode ser sorte, dado o número de testes); c7 = não cabe na conta de $16.

## Placar por família (todas as células)

| Família | Células | OOS > 0 | IS e OOS > 0 | t mediano no OOS |
|---|---|---|---|---|
| ADXPB | 45 | 44% | 18% | -0.36 |
| BBMR | 275 | 35% | 16% | -0.43 |
| TOM | 90 | 34% | 27% | -0.43 |
| DOW | 91 | 38% | 36% | -0.54 |
| RSIn | 268 | 31% | 16% | -0.56 |
| ZSCORE | 276 | 29% | 13% | -0.63 |
| OBVRSI | 173 | 31% | 9% | -0.71 |
| RSI2 | 270 | 29% | 18% | -0.74 |
| CONSEC | 271 | 24% | 12% | -0.82 |
| GAPFADE | 266 | 23% | 9% | -1.02 |
| SUPERT | 261 | 18% | 8% | -1.06 |
| VOLBRK | 235 | 16% | 6% | -1.08 |
| PINBAR | 263 | 21% | 8% | -1.08 |
| DOUBLE7 | 275 | 20% | 8% | -1.12 |
| VOLCAP | 127 | 19% | 6% | -1.18 |
| MACROSS | 196 | 23% | 11% | -1.24 |
| IBS | 276 | 16% | 9% | -1.37 |
| MACD | 255 | 16% | 5% | -1.38 |
| ENGULF | 135 | 20% | 12% | -1.42 |
| PULLB | 273 | 14% | 6% | -1.43 |
| BBMR_I | 93 | 16% | 8% | -1.44 |
| DONCH | 268 | 12% | 3% | -1.48 |
| TSMOM | 274 | 17% | 8% | -1.52 |
| INSIDE | 268 | 12% | 3% | -1.53 |
| NR7 | 275 | 11% | 4% | -1.62 |
| KELTNER | 271 | 11% | 5% | -1.76 |
| RSI2_I | 93 | 9% | 3% | -1.88 |
| VWAP | 93 | 6% | 2% | -2.17 |
| ZSCORE_I | 93 | 5% | 2% | -2.64 |
| HOD | 93 | 10% | 9% | -4.66 |
| IBS_I | 93 | 3% | 1% | -5.35 |
| ORB | 93 | 9% | 0% | -6.10 |

Uma família sem vantagem teria cerca de 50% de OOS positivo antes dos custos e menos depois deles.

