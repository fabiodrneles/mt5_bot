# Protocolo da pesquisa ampla (rodada 3) — registrado antes dos resultados

Data: 2026-10-24. Conta-alvo: real Hantec, saldo $16, lote mínimo, alavancagem 500.
Este arquivo foi escrito **antes** de rodar a grade. Os critérios não mudam depois de ver os números
(mudá-los seria otimizar o critério, uma forma de *overfitting*).

## Universo
Todo símbolo negociável cuja margem no lote mínimo é ≤ 25% de $16 (`universe.py`): forex, índices,
commodities, cripto e CFDs de ações. Timeframes H1, H4 (reamostrado do H1) e D1.

## Custos
Spread real de cada candle (mediana do H1 no D1), comissão observada nos deals da conta (sem deal:
$1/lote em índices, cripto e ações; zero em forex e petróleo), swap por rolagem com a **rolagem
tripla** do símbolo. Entrada na abertura do candle seguinte ao sinal; stop antes do alvo no mesmo candle.

## Famílias (28)
Reversão à média: RSI2, RSIn, IBS, quedas seguidas, Double-7, Bollinger, z-score, *gap fade*.
Tendência/momento: Donchian, cruzamento de médias, TSMOM, MACD, Keltner, Supertrend, ADX+DI, pullback EMA20.
Padrões de candle: NR7, *inside bar*, engolfo na banda, martelo/estrela.
Calendário: virada do mês, dia da semana, hora do dia.
Volume e fluxo (volume de ticks): pico de volume (capitulação), rompimento com volume, OBV + IFR2,
VWAP intradiário, rompimento da faixa de abertura.
Pares (estatística): z-score do spread log entre pares cointegrados candidatos (D1).

## Seleção (só dentro da amostra)
60% iniciais = IS, 40% finais = OOS. Em cada (símbolo, timeframe, família) o parâmetro é escolhido
pela estatística t do lucro por trade **no IS** (mínimo 20 trades). O OOS nunca participa da escolha.

## Critérios de aprovação (todos)
1. OOS: ≥ 30 trades, lucro > 0, fator de lucro ≥ 1,2, estatística t ≥ 2,0.
2. IS também lucrativo.
3. Robustez da família: ≥ 50% das variações lucram em IS e OOS.
4. Custos 1,5× e 2×: lucro OOS > 0 com 1,5×.
5. *Walk-forward* ancorado com 5 dobras (re-escolhendo o parâmetro em cada IS): soma OOS > 0 e ≥ 3 de 5 dobras positivas.
6. *Deflated Sharpe Ratio* ≥ 0,95, com N = número total de configurações testadas no timeframe.
7. Viável com $16: perda mediana no stop ≤ $1,60 (10%) e probabilidade de ruína < 5% em 2 anos
   (Monte Carlo por reamostragem dos trades OOS, ruína = patrimônio abaixo de margem + 1 stop).

Aprovada em 1–7 = **candidata a rota**. Aprovada em 1–4 mas reprovada em 5–7 = "promissora, não
comprovada". O relatório lista as duas, e também quantas configurações foram testadas no total.

## Notas de implementação (adicionadas durante a execução, antes de qualquer aprovação)

- **Custos (2026-10-24):** o protocolo diz "spread real de cada candle". Na execução apareceram três subestimações, todas corrigidas para o lado conservador antes da análise final: comissão de CFDs de ações (0,1% por lado, estimada), spread do rollover nos candles intradiários e spread da reabertura do fim de semana no D1. Detalhes em `ESTADO_PESQUISA.md`.
- **Variância do DSR:** o protocolo não fixava o estimador de $V[\widehat{SR}]$. A variância bruta é dominada por configurações degeneradas (por exemplo, Sharpe por trade de −97 em leilões de ações, onde todo trade perde só o custo), que não representam a dispersão das tentativas. Uso o desvio robusto $1{,}4826\cdot\mathrm{MAD}$. **Atenção:** o robusto é **menos rigoroso** que o bruto (variância menor → limiar $SR_0$ menor). Por transparência, o relatório mostra o DSR pelos dois e marca quem só passa pelo robusto.
