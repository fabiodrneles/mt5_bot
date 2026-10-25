# Pesquisa ampla de padrões — rodada 3 (2026-10-24)

Pergunta do dono: existe algum padrão (horário, data, indicador, volume, relação entre ativos) que deixe lucro, mesmo de centavos, numa conta real de US$ 16? Detalhes completos: guia técnico, cap. 14 (`docs/manual/14-pesquisa-ampla.md`). Código, protocolo e estado: `tools/quant_research/` (`PROTOCOLO2.md`, `ESTADO_PESQUISA.md`, `RESULTADOS2.md`, `pipeline2.py`).

## Método
- Universo: 337 símbolos com margem no lote mínimo ≤ 25% de US$ 16. Timeframes D1, H4 e H1; M15/M30 em execução.
- 28 famílias (reversão, tendência, candles, volume de ticks, calendário), pares cointegrados, *lead-lag* A → B e varredura de horário/dia/data.
- Protocolo pré-registrado com 7 critérios: OOS forte, IS lucrativo, família robusta, custo 1,5×, *walk-forward* 5 dobras, DSR ≥ 0,95 e viabilidade com US$ 16 (Monte Carlo de ruína). Calendário e *lead-lag* usam o FDR de Benjamini–Hochberg (q = 5%).
- Faixa experimental (decisão do dono): DSR entre 0,80 e 0,95 → só `/study` até repetir em ≥ 30 trades novos.

## Resultado
- Grade final (D1/H4/H1 em ~335 ativos; M30/M15 em 88): 128.076 configurações → **0 aprovadas**, 27 promissoras (todas DSR < 0,05). As 35 famílias têm t mediano OOS negativo.
- Calendário: 136.864 células → 1 (USDJPY, compra na segunda às 01h por 1h; spread real normal nos ticks; candidato à faixa experimental). *Lead-lag*: 45.918 → 0. Pares: todos perdem.
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

## Regra da MME9 do dono (guia cap. 14 §14.8)
Cinco versões testadas (alvo 2×; stop na máxima/mínima + volume/tendência/multi-tempo; "máquina do tempo" com 19.286 regras; reversão após tendência forte, k-NN e regime; "algum lucro" e ângulo do relógio/Raghee Horner). Nenhuma lucra fora da amostra. 55–65% dos sinais passam pelo lucro antes do stop, mas nenhuma saída fixada antes embolsa isso. Sinais citados pelo dono: o "ruim" teve a maior tendência medida e também ganhou. Ferramentas `check_*.py` em `tools/quant_research/`.

## RSI2 nos índices e rota US100 em estudo (§14.9)
Mesma regra do US500, sem reotimizar: US500 t 2,48; US100 t 2,10 (+$51 em 10 anos, risco $5,20); US30 t 1,14; demais fracos ou negativos. `config.QUANT_ROUTES["US100"]` com `mode = "study"` (`mt5bot/execution/quant_study.py`): ordens virtuais em `quant_study.json`; ativa com `[routes.US100] mode = "live"`. Plano: US100 com ~$52, US30 com ~$72.

## Diário de sinais (guia cap. 9 §9.7)
`bot.bat anotar ATIVO TF compra|venda bom|ruim "motivo" [--alvo R]` grava hora e preço na hora (recusa mercado fechado); `bot.bat diario` mede com M1 e spread e calcula a cauda binomial contra o empate 1/(1+R). Conclusão só com ≥ 30 sinais "bom" encerrados. Arquivo: `%APPDATA%\mt5bot\diario_sinais.csv`.

## Rota USDJPY H1 em estudo (v3.2.0)
`config.QUANT_ROUTES["USDJPY"]`: setup `HOUR` (`quant_setups.signal_hour_of_week`), compra na segunda às 01h do servidor, sai após 1 candle, SL 3 ATR, `mode = "study"`. Promoção só com ≥ 30 segundas novas e t ≥ 2 (faixa experimental).

## Rota USDJPY D1 IFR2 Stormer em estudo
`config.QUANT_ROUTES["USDJPY_IFR2"]` com `"symbol": "USDJPY"`: setup `STORMER` (`quant_setups.signal_stormer`), só compra com IFR2 < 5, alvo na máxima dos 2 últimos candles, saída em 7 candles, SL protetor 3 ATR, `mode = "study"`. Achado entre 238 combinações par × variante (USDJPY consistente nas duas metades, t ≈ 3; swap positivo na compra). Várias rotas por ativo: chave livre + `symbol`; `quant_manager.get_route(symbol, tf)` busca por ativo e tempo gráfico; `signal_key` = ativo:segundos; o estudo casa a operação aberta por ativo e setup.

## Teste justo do 9.x (diário, ordem stop, saída pela MME9) — `docs/validacao-9x-fiel.md`
166 ativos (165 CFDs de ações com abertura irreal excluídos). Ações/índices EUA, OOS, sem swap: 9.1 −0,027/−0,001 R, 9.2 −0,002 R, 9.4 −0,016 R (t ≈ 0) → **empate**; com spread normal, −0,002 a +0,027 R. Com swap do CFD → prejuízo (−0,08 a −0,20 R). 9.3 perde em tudo; forex perde forte. Filtros semanal/SMA200 não ajudam. Não testado: ações da B3 (sem swap), seleção discricionária, saídas parciais. Mensagem: o 9.x mecânico empata antes do financiamento; a vantagem de quem lucra tende a vir do mercado à vista e da seleção.

## 9.x na B3 (`check_9x_b3.py`, dados Yahoo ajustados, 59 ações, ~20 anos, sem swap)
Compra + saída MME9: 9.1 semanal +0,086 R (IS) / +0,095 R (OOS); 9.2 semanal+SMA200 +0,29/+0,14 R. Porém t por mês 0,35–0,49 (não significativo), 15/27 anos positivos, e entradas ALEATÓRIAS em dias de tendência com a mesma saída rendem +0,16 R → o lucro vem da tendência de alta da bolsa e da saída pela MME9, não do gatilho. Viés de sobrevivência (só membros atuais do Ibovespa).
Comparação em carteira (`compare_b3.py`, desde 2005, sem IR): CDI 10,6% a.a.; Ibovespa 9,9% (DD −60%); comprar e segurar as 59 ações 22,8% (inflado por sobrevivência); 9.1 semanal com CDI fora da posição 9,9% (DD −7,9%, investido 22%); 9.2 10,3% (DD −2,3%). O 9.x não supera o CDI.

## Setups do Palex em forex e B3 (`palex_setups.py`, `compare_palex_b3.py`, `docs/validacao-palex.md`)
14 setups mecânicos (Fura-teto, Harami/Engolfo, cruzamentos MM5/MM9×MM21, MM200, IFR14+reversão, IFR2 Connors, topo histórico, Iguana, Latinha, Inside Day, Shark, Peg Leg, Realização frustrada, Key Buy). **Forex: todos perdem.** B3: compras positivas, vendas negativas (tendência). Carteira desde 2005: **Cruz MM9×MM21 16,4% a.a., DD −15%** (desde 2016: 19,6%, DD −12,7%) vs CDI 10,6%, Ibov 9,9%. Contra mistura 55% ações + 45% CDI do mesmo universo: Sharpe 0,51 vs 0,48 (2005) e 0,79 vs 0,58 (2016), metade da queda. Candidato a rota B3 em estudo. Viés de sobrevivência; sem IR.
