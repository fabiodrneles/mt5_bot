# Pesquisa quant (v2.10.0)

Reproduz a busca que escolheu as rotas de `config.QUANT_ROUTES`. Rode a partir desta pasta, com o MT5 aberto:

```
python fetch.py JP225,US500,FR40,AU200,HK50,USOIL+,UKOIL+,ETHUSD,EU50,UK100,CN50,SOLUSD,XRPUSD,LTCUSD,BTCUSD
python meta.py
python research.py <ativos> M15,H1,H4,D1 r_all.json   # grade completa (~1 min)
python analyze.py r_all.json                          # robustez IS x OOS
python deep.py                                        # ano a ano + spread x1.5
```

Ela só lê histórico e não envia ordens. Os candles e o `meta.json` ficam em `data/` (ignorada pelo git).
Detalhes e resultados: `memoria/wiki/arquitetura/pesquisa-estrategias-lucrativas.md`.
