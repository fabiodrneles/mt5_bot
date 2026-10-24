# Pesquisa ampla de padrões — rodada 3 (2026-10-24)

Pergunta do dono: existe algum padrão (horário, data, indicador, volume, relação entre ativos) que deixe lucro, mesmo de centavos, numa conta real de US$ 16? Detalhes completos: guia técnico, cap. 14 (`docs/manual/14-pesquisa-ampla.md`). Código, protocolo e estado: `tools/quant_research/` (`PROTOCOLO2.md`, `ESTADO_PESQUISA.md`, `RESULTADOS2.md`, `pipeline2.py`).

## Método
- Universo: 337 símbolos com margem no lote mínimo ≤ 25% de US$ 16. Timeframes D1, H4 e H1; M15/M30 em execução.
- 28 famílias (reversão, tendência, candles, volume de ticks, calendário), pares cointegrados, *lead-lag* A → B e varredura de horário/dia/data.
- Protocolo pré-registrado com 7 critérios: OOS forte, IS lucrativo, família robusta, custo 1,5×, *walk-forward* 5 dobras, DSR ≥ 0,95 e viabilidade com US$ 16 (Monte Carlo de ruína). Calendário e *lead-lag* usam o FDR de Benjamini–Hochberg (q = 5%).
- Faixa experimental (decisão do dono): DSR entre 0,80 e 0,95 → só `/study` até repetir em ≥ 30 trades novos.

## Resultado
- Grade: 41.213 configurações → **0 aprovadas**. Todas as 32 famílias têm t mediano OOS negativo.
- Calendário: 75.886 células → 0. *Lead-lag*: 12.420 cruzamentos → 0. Pares: todos perdem.
- Na simulação, 1.413 configurações levaram US$ 16 a mais de US$ 50 no OOS, mas com risco de US$ 14–38 por trade e quedas de US$ 48–119: inviáveis com US$ 16.
- Rotas atuais revistas: **US500 D1 RSI2 sobrevive** (OOS +9,73, t 3,2). **HK50 H4 PULLB encolhe** (OOS +2,93, t ≈ 0,7).

## Artefatos de dados descobertos (lições permanentes)
1. Comissão de CFD de ações: lote = 1 ação; usar 0,1% do valor por lado (estimado).
2. Spread do rollover subestimado no candle (AUDCAD 3 → 19 pts na hora 0).
3. Spread da reabertura de domingo (AUDJPY 62 pts): criava o falso "efeito segunda".
4. **Abertura irreal do pregão das ações** no histórico H1/D1 da Hantec (LKQCorp 2023: abertura −1,10 abaixo do fechamento anterior, corpo +1,05). Gerava "comprar na abertura de NY" (t ≈ 30) e o falso "LKQCorp sexta". 37 de 72 CFDs afetados; forex e cripto não.
5. O campo `spread` do candle do MT5 guarda o **mínimo** do período; ticks reais do EURGBP na quinta 0h: 82–224 pts contra ~30 no candle.
Regras do simulador (`research2.simulate`): entrada paga o maior spread entre o candle anterior e o de entrada; o 1º candle depois de uma pausa (e todo D1) entra pelo pior entre abertura e fechamento anterior; nenhuma entrada na hora 0 do servidor.
**Implicação para produção:** um motor que entra na abertura do candle depois de uma pausa ou na hora do rollover paga custos que o backtest em candles não vê. Os motores do bot devem evitar esses momentos (relevante para a spec 008, filtro de spread).

## Diagnóstico de "bom demais"
Decompor o corpo ($C_t - O_t$) e o gap ($O_t - C_{t-1}$): se um desfaz o outro, a abertura é falsa. Testar se o efeito aparece em todos os dias ou horários (artefato) ou só em um (candidato). Confirmar com M1 e ticks bid/ask.
