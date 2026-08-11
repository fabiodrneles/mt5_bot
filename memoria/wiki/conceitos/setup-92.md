# Setup 9.2 — Correção rápida

Fonte: `raw/estrategias-operacionais.txt` · Status: ✅ implementado e testado (`brain/setups.py` + `test_book_setups.py`)

## Regras (COMPRA)
1. **Contexto**: MME9 apontando para cima (tendência de alta ativa).
2. **Correção**: um candle de correção tem sua **mínima abaixo da mínima do candle anterior** (a mínima do candle anterior não é respeitada — o preço "passa" dela).
3. **Entrada**: rompimento da **máxima** do candle de correção.
4. **Stop**: mínima do candle de correção.

## Regras (VENDA) — simétrico
- MME9 apontando para baixo; candle de correção com máxima acima da máxima do anterior.
- Venda no rompimento da mínima do candle de correção. Stop: máxima do candle.

## Ponto-chave
- É um setup de **continuação da tendência** após uma correção rápida.
- A "quebra" da mínima anterior indica que a correção chegou ao fim; o rompimento da máxima confirma a retomada.
- Requer MME9 alinhada — sem isso não é 9.2 válido.

## No código (estado atual)
- `brain/setups.py`: `StrategyScorer.evaluate_all` detecta 9.2 compra/venda (EMA9 alinhada + mínima/máxima quebrando a anterior; trigger no rompimento; score 15). É o motor em produção (Maestro roda `brain/main.py`).
- `config.py`: `CONFIG_SETUPS["9.2"] = True` (habilitado por padrão).
- Testes: `test_book_setups.py` — `test_setup_92_buy_trigger`, `test_setup_92_sell_trigger`, `test_setup_92_requires_ema9_aligned`.
- O antigo estado `WATCHING_92` de `strategy.py` foi **descontinuado**: o `strategy.py` legado não é mais importado por nenhum fluxo (grep: nenhum `import strategy` no projeto).

## Observação de trading
- Palex: 9.2/9.3 são ~60% das operações dele — o core da operação.
- Preferir quando a correção é rápida (poucos candles) e rasa.
