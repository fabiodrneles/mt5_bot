# FFFD — Bollinger Fechou Fora / Fechou Dentro

Fonte: `raw/estrategias-operacionais.txt` (capítulo Bollinger) · Status: planejado para Fase 2

## Regras (COMPRA)
1. **Condição 1**: um candle **fecha FORA** da banda inferior do Bollinger (20,2).
2. **Condição 2**: o candle seguinte **fecha DENTRO** da banda (volta para dentro).
3. **Entrada**: rompimento da **máxima do candle que fechou dentro**.
4. **Stop**: mínima extrema (a menor mínima do candle de fora ou do de dentro — mais conservadora).

## Regras (VENDA) — simétrico
- Candle fecha FORA da banda superior → candle fecha DENTRO → venda no rompimento da mínima do candle de dentro; stop na máxima extrema.

## Ponto-chave
- Bollinger = **medida de volatilidade**, NÃO suporte/resistência. Tocar a banda não é sinal.
- O FFFD captura **exaustão**: o preço saiu da banda (movimento extremo) e a volta para dentro indica reversão iminente.
- Alvos: **SMA20** ou **2x o risco** (ver `gestao-de-risco.md`).

## No código (planejado)
- `indicators.py`: função para Bollinger (20,2) — média + 2 desvios.
- `strategy.py`: `check_fffd_buy/sell` na Fase 2.

## Observação de trading
- O Palex trata o Bollinger como filtro de **volatilidade**: setups só são válidos quando o mercado está "vivo" (bandas expandindo).
- Combina bem com o VWAP e com a MM200 como contexto maior.
