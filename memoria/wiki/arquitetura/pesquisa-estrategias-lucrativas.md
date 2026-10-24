# Pesquisa de estratégias lucrativas — rotas quant (v2.10.0)

Pesquisa de 2026-10-23 feita sobre a conta real Hantec (hedging, alavancagem 500, saldo $16.26).
O objetivo era achar estratégias com lucro **depois de custos** que caibam em uma conta de ~$16
sem que uma sequência de perdas consuma a margem das próximas operações.

## Método
- Ferramentas: `tools/quant_research/` (só leem histórico e não enviam ordens).
- Foram testados 15 ativos com margem baixa no lote mínimo: HK50 $0.15, JP225 $0.40, EU50 $0.61,
  US500 $0.76, FR40 $0.78, AU200 $0.87, petróleo ~$1, ETH $1.19, além de outros índices e criptos.
- Timeframes M15, H1, H4 (reamostrado do H1, idêntico ao H4 nativo) e D1.
- Quatro famílias clássicas com poucos parâmetros: RSI2 (Connors), Bollinger de reversão, Donchian
  e pullback na EMA20. No total foram 3.150 configurações.
- Custos: spread real de cada candle, comissão observada nos deals da conta ($1/lote em US500,
  AU200, FR40, EU50, UK100 e cripto; zero em HK50, JP225 e petróleo) e swap por noite (pontos ou %
  anual).
- Validação: os parâmetros são escolhidos com os **60% iniciais** do histórico e o resultado que
  conta vem dos **40% finais**. Uma família só é aceita se der lucro nos dois períodos. Depois
  vem a análise ano a ano e o estresse com spread 1,5x.

## Resultado (lote mínimo, US$)
| Rota | Regra | Trades | PF | Lucro | DD máx | Pior trade | Risco/trade |
|---|---|---|---|---|---|---|---|
| **HK50 H4 PULLB** | EMA20>EMA50, a mínima toca a EMA20 e o fechamento fica acima dela e acima da SMA200 (venda espelhada). SL 1 ATR, TP 2 ATR | 277 / 4,8 anos | 1,24 | +$9,96 | $4,30 | −$0,75 | ~$0,21 |
| **US500 D1 RSI2MR** | IFR2<5 acima da SMA200 → compra (IFR2>95 abaixo → venda). SL 2 ATR. Sai quando o fechamento cruza a SMA5 ou após 15 candles | 54 / 9,5 anos | 2,40 | +$13,19 | $3,04 | −$1,41 | ~$1,63 |

- HK50 PULLB: **100% das 12 variações** da família lucram nos dois períodos (é a família mais
  robusta da grade). Ano a ano: 2022 +5,33, 2023 +0,88, 2024 −1,48, 2025 +0,65, 2026 +4,57.
- US500 RSI2MR: 7 de 10 anos positivos, e os 6 últimos todos positivos. Com spread 1,5x o
  resultado praticamente não muda.
- Descartado: cripto em D1 parece lucrativa, mas tem DD de $50–160 no lote mínimo (0,1), o que é
  impossível com $16. O setup russo do HK50 (M5) deu −$0,30 nos últimos 2 meses e +$0,13 em 7.

## Implementação
- `mt5bot/engine/quant_setups.py`: sinais puros. Rodando vela a vela com janela de 400 candles,
  eles reproduzem os sinais do backtest **sem nenhuma divergência** (2.500 candles HK50 H4 e
  2.126 US500 D1).
- `mt5bot/execution/quant_manager.py`: caminho próprio, despachado por `manage_cycle` quando
  (ativo, timeframe) está em `config.QUANT_ROUTES`. Abre a mercado na abertura do candle seguinte
  ao sinal (descarta o sinal se passar de 10% do candle), com lote mínimo fixo e SL/TP no MT5.
  **Não** passa por scoring, RVOL, XGBoost, EMA9, trailing, breakeven ou janela de horário, porque
  nada disso foi validado.
- Travas de capital: perda no SL ≤ `QUANT_MAX_RISK_PCT` (2%) do saldo; margem livre após a entrada
  ≥ 3x a margem da posição; Daily Max Loss bloqueia novas entradas. Com $16 o US500 fica travado
  sozinho (SL de ~$1,6 = 10%) e libera com saldo acima de ~$80.
- Isolamento: só gerencia posições com MAGIC do bot e comentário `Q <setup>`. Posição manual do
  usuário no mesmo ativo (conta hedging) não é tocada, e o caminho antigo ignora posições quant.
- Execução: `bot.bat quant` (ou `python tools\quant_runner.py`), ou no Maestro `/add HK50 H4` e
  `/add US500 D1`. Testes: `tests/test_quant_routes.py`.

## Expectativa honesta
Cerca de +$2/ano no HK50 com $16 (~13%/ano), com quedas de até ~$4 no caminho. É lucro de
centavos por trade (média de +$0,036). Os resultados passados não garantem os futuros. A
amostra ao vivo precisa de dezenas de trades antes de qualquer conclusão.
