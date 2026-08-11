# Setup 9.4 — Falso recuo (1 candle contra)

Fonte: `raw/estrategias-operacionais.txt` · Status: planejado para Fase 2 (não implementado ainda)

## Regras (COMPRA)
1. **Contexto**: tendência de alta estabelecida (MME9 para cima).
2. **Falso recuo**: a MME9 **vira contra** por apenas **1 candle** (candle de correção que vira a média para baixo), **sem** romper a mínima estrutural anterior.
3. **Retomada**: no candle seguinte a MME9 **volta a apontar para cima**.
4. **Entrada**: rompimento da **máxima do candle de retomada** (o candle que re-virou a MME9).
5. **Stop**: abaixo do fundo da correção.

## Regras (VENDA) — simétrico
- Tendência de baixa; MME9 vira para cima por 1 candle sem romper máxima estrutural; volta a virar para baixo; venda no rompimento da mínima do candle de retomada.

## Ponto-chave
- É a "armadilha" clássica: a média vira contra mas não confirma, e o preço retoma a tendência com força.
- **Distinção crítica vs 9.1**: no 9.4 a MME9 **não precisa** re-virar por estrutura — o que importa é que a virada foi **falsa** (não sustentada).
- Validar com o conceito de "fundo que não foi rompido" (estrutura preservada).

## No código (planejado)
- `strategy.py`: adicionar `check_setup_94_buy/sell` na Fase 2 (ver `fases.md`).
- Precisa de detecção de: MME9 virou contra (1 candle) + não rompeu mínima estrutural + re-virada.

## Observação de trading
- Menos frequente que 9.2/9.3, mas com ótima relação risco-retorno (stop curto).
- Palex usa ~10% das operações nesse setup.
