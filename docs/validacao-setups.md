# Validação dos setups clássicos contra a fonte (Palex)

> Data: 2026-10-24. Fonte primária: FERNANDES, A. (Palex). *Estratégias Operacionais de Análise Técnica de Ações*, 2014, extraído em `memoria/raw/estrategias-operacionais.txt` (o mesmo PDF da pasta de livros do dono). Código: `mt5bot/engine/strategy.py` (`StrategyScorer.evaluate_all`). Testes: `tests/test_book_setups.py`, `tests/test_strategy_motor.py`.
>
> Contexto: os setups clássicos rodam só em `/study` por padrão (D5, spec 005). Na pesquisa ampla (guia, cap. 14) nenhum deles teve vantagem estatística depois dos custos. A validação abaixo verifica se o robô **implementa o que o livro diz**, não se o setup dá lucro.

## Resultado

| Setup | Regra do livro (resumo) | Código antes | Situação |
|---|---|---|---|
| **9.1** (p. 10) | MME9 caindo vira para cima em candle fechado; compra 1 tick acima da máxima do candle da virada; stop na mínima; vale enquanto a MME9 não virar de novo | Virada da inclinação da MME9; gatilho e stop no candle da virada | ✅ Conforme |
| **9.2** (p. 11) | MME9 subindo; um candle **fecha** abaixo da **mínima** do anterior; compra 1 tick acima da máxima dele; stop na mínima | Aceitava que só a **mínima** passasse da mínima anterior (mais sinais que o livro) | ✅ **Corrigido**: exige o fechamento (venda: fechamento acima da máxima anterior) |
| **9.3** (p. 14) | MME9 subindo; referência = **maior fechamento da perna**; depois ≥ 2 fechamentos abaixo dele (o 2º pode fechar acima do 1º), sem a MME9 virar; compra na máxima do último candle; stop na mínima dele | Exigia `fechamento da referência < mínima do candle anterior`, o oposto da regra, o que quase nunca acontece numa alta; stop na menor mínima dos 2 candles | ✅ **Corrigido**: nova `_ref_93` segue o livro (compra e venda) |
| **9.4** (p. 18) | MME9 subindo vira para baixo por **só 1 candle**, sem perder a mínima, e volta a subir; compra na máxima do candle que a virou para cima; stop na mínima do candle que a virou para baixo | Exatamente isso | ✅ Conforme |
| **Ponto Contínuo** (p. 27) | MM21 ascendente; o candle **toca ou se aproxima bem** da MM21; marca a máxima; compra 1 tick acima; stop na mínima. Venda espelhada | Só aceitava candles cuja mínima ficasse **acima** da MM21 (um toque de verdade era descartado); **sem a venda** | ✅ **Corrigido**: toque ou aproximação até 0,3 ATR, fechamento do lado da tendência; venda com a MM21 descendente |
| **FFFD** (Bollinger) | Fecha fora da banda, o seguinte fecha dentro; entrada no rompimento do candle de dentro; stop na mínima/máxima extrema | Exatamente isso | ✅ Conforme |
| **IFR2** (p. 72) | IFR(2) ≤ 5 com MME50 subindo e preço acima dela; referência às MM13/MM28; venda espelhada (≥ 95) | Só a compra; usa MM13 como filtro de fechamento; MM28 não usada | ⚠️ Parcial: falta a venda e a MM28 |
| **SAR** (Machado) | SAR (0,02/0,2) como direção, IFR(14) e MM13; **stop pelo cruzamento do IFR** | Gatilho com SAR, IFR > 50 e MM13; stop na mínima do candle | ⚠️ Parcial: stop pelo IFR não implementado; só compra |
| **DiNapoli** | 2º fundo acima do 1º (ou a mínima viola, mas o fechamento fica acima); fechamento acima da média deslocada; entrada 1 tick acima da máxima | Exige 2º fundo ≥ 1º (sem a exceção do fechamento); média deslocada = MME12 deslocada 3 | ⚠️ Parcial: falta a exceção; tipo da média a confirmar no livro; só compra |
| **Rompimento Falso** (Farley, p. 81) | Rompe um **suporte importante** e volta; compra 1 tick acima da máxima do candle de rompimento; stop na menor mínima | "Suporte" = mínima de 3 candles atrás | ⚠️ Simplificado: não detecta suportes estruturais |

**Acréscimos do projeto, que não estão no livro:** filtro global da SMA200 sobre todos os setups (exceto GAP) e os filtros MM50/IFR9/VWAP do scoring. São decisões de desenho (cap. 5 do guia), não regras do Palex.

## Testes acrescentados

- `test_setup_92_buy_trigger` e `test_setup_92_sell_trigger`: reescritos para a regra do fechamento. Os anteriores codificavam a regra da mínima.
- `test_setup_92_needs_the_close_not_just_the_low`.
- `test_setup_93_buy_after_two_closes_below_reference`, `test_setup_93_needs_two_closes_and_ema9_still_rising`, `test_setup_93_sell_mirror`.
- `test_ponto_continuo_buy_accepts_a_touch_through_the_mm21`, `test_ponto_continuo_sell_with_falling_mm21`.

## Pendências

Completar IFR2 (venda e MM28), SAR (stop pelo IFR), DiNapoli (exceção do fechamento) e o Rompimento Falso estrutural, cada um com teste a partir do texto do livro. Como esses setups ficam em `/study`, nenhuma pendência afeta dinheiro real.

## Outros PDFs da pasta do dono

A pasta `E:\Não mexer\Downloads` (somente leitura, nada foi alterado) também tem *Python for Finance* (Hilpisch), já resumido em `memoria/wiki/yves_hilpisch_quant_patterns.md`, e livros de QA e testes de IA. Estes últimos não trazem regras de setups, mas podem fundamentar a seção de testes do guia (cap. 10) e a validação de modelos (spec 016).
