# Setup 9.3 — Recuo profundo (2 fechamentos)

Fonte: `raw/estrategias-operacionais.txt` · Status: já implementado (`check_setup_93_*`)

## Regras (COMPRA)
1. **Contexto**: MME9 apontando para cima.
2. **Correção**: **pelo menos 2 candles consecutivos** de recuo, mantendo a MME9 apontando para cima (o preço recua mas a média não vira).
3. **Entrada**: rompimento da **máxima do candle de recuo** (o último candle da correção).
4. **Stop**: mínima do candle de recuo.

## Regras (VENDA) — simétrico
- MME9 apontando para baixo; ≥2 candles de recuperação mantendo a média para baixo.
- Venda no rompimento da mínima do candle de recuo. Stop: máxima.

## Diferença vs 9.2
- **9.2**: 1 candle de correção que **quebra a mínima anterior** (correção rápida/forte).
- **9.3**: **≥2 candles** de recuo que **não** quebram estrutura anterior — recuo "deitado", mais lento.
- Ambos exigem MME9 a favor.

## No código (estado atual)
- `indicators.py`: `check_pullback_to_ema9` (identifica recuo de 2+ candles).
- `strategy.py`: `check_setup_93_buy/sell` — usa o rompimento da máxima do último candle de recuo.
- Implementado na Fase 2 (ver `ROADMAP_IMPROVEMENTS.md`, CHANGELOG L62-68).

## Observação de trading
- Mais filtro de tempo que o 9.2: recuo de 2+ candles dá mais confirmação, mas entrada mais distante.
- Palex combina 9.2/9.3 com a MME9 (referência central da estratégia).
