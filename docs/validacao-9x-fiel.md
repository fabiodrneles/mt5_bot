# Teste justo do 9.x: as regras do livro, como o Palex opera

> Data: 2026-10-24. Ferramenta: `tools/quant_research/check_9x_fiel.py` (só lê histórico). Resultados brutos: `tools/quant_research/data/9x_fiel.json` e `9x_fiel_spread_normal.json` (ignorados pelo git). Motivação: a pesquisa ampla (guia, cap. 14) testou versões **simplificadas** da família 9.x (intradiário, entrada a mercado, alvo fixo). Antes de concluir qualquer coisa sobre o 9.x, ele precisava ser testado como o autor opera.

## O que foi testado

| Aspecto | Versão simplificada (cap. 14) | Versão fiel (este teste) |
|---|---|---|
| Tempo gráfico | M15, H1, H4, D1 | **Diário** |
| Entrada | A mercado, na abertura seguinte | **Ordem stop** 1 tick acima da máxima (venda: abaixo da mínima). No 9.1, a ordem vale enquanto a MME9 não virar contra; no 9.2 e no 9.3, a entrada **desce** para as máximas menores (livro, p. 11 e 14) |
| Stop inicial | Tamanho do candle | O do livro para cada setup |
| Saída | Alvo fixo de 2× | **Conduzida pela MME9** (livro, p. 10): quando a média vira contra, marca a mínima do candle que a virou; perdendo essa mínima, sai. O alvo de 2× foi rodado só para comparar |
| Filtros | — | Congruência com o semanal (MME9 semanal a favor, só semanas fechadas) e SMA200 |
| Custos | Spread, comissão, swap | Os mesmos, com o resultado **sem swap** guardado à parte (ações à vista na B3 não pagam swap) e uma sensibilidade com o spread normal do pregão |
| Universo | — | 166 ativos: índices, forex, cripto, commodities e CFDs de ações americanas. Os 165 CFDs de ações com abertura diária irreal (artefato A6) foram excluídos |

As regras dos setups são as do código do robô depois da validação contra o livro (`docs/validacao-setups.md`). Cada sinal acionado é avaliado sozinho, e o resultado é medido em múltiplos do risco (R). IS = 60% iniciais do histórico de cada ativo; OOS = 40% finais.

## Resultado (só compra, saída pela MME9, sem filtro)

| Classe | Setup | IS sem swap | OOS sem swap (t) | OOS com swap |
|---|---|---|---|---|
| Ações (EUA) | 9.1 | −0,235 R | **−0,027 R** (−0,69) | −0,106 R |
| Ações (EUA) | 9.2 | −0,069 R | **−0,002 R** (−0,03) | −0,094 R |
| Ações (EUA) | 9.3 | −0,251 R | −0,112 R (−2,94) | −0,199 R |
| Ações (EUA) | 9.4 | −0,232 R | **−0,016 R** (−0,29) | −0,087 R |
| Índices | 9.1 | −0,147 R | **−0,001 R** (−0,01) | −0,201 R |
| Índices | 9.2 | −0,314 R | −0,178 R (−1,95) | −0,389 R |
| Índices | 9.3 | −0,162 R | −0,131 R (−2,42) | −0,377 R |
| Índices | 9.4 | −0,244 R | −0,067 R (−0,77) | −0,236 R |
| Forex | 9.1–9.4 | −0,22 a −0,41 R | −0,26 a −0,44 R (t −6 a −17) | pior |
| Cripto | 9.1 / 9.4 | +0,09 / +0,12 R | −0,007 / +0,035 R | −0,10 / −0,06 R |

Com o **spread normal do pregão** (a ordem stop costuma ser acionada fora da abertura), o OOS das ações fica em −0,002 R (9.1), +0,027 R (9.2) e +0,003 R (9.4). Os filtros de congruência semanal e SMA200 **não melhoram** o resultado agregado (ver o JSON).

## Leitura honesta

1. **A versão fiel é muito melhor que a simplificada.** Nas ações e índices americanos, no período recente, o 9.1, o 9.2 e o 9.4 ficam **no zero a zero sem o custo de financiamento**. A versão simplificada perdia claramente. A forma de entrada (ordem stop) e de saída (conduzir pela MME9) importa, como o livro ensina.
2. **Nos CFDs, o swap transforma o empate em prejuízo.** Um trade conduzido pela MME9 fica em média 7 a 10 dias aberto, e o financiamento diário do CFD custa de 0,05 a 0,4 R por trade. **Ações à vista na B3 não pagam esse custo.** Por isso este teste não contradiz quem opera o 9.x em ações da B3; ele mostra que **o 9.x via CFD alavancado é outro negócio**.
3. **Mecanicamente, o 9.x não mostrou vantagem estatística** em centenas de ativos americanos. No período antigo (IS) ele perde e no recente (OOS) empata. Se há vantagem na operação de quem lucra com o 9.x, ela tende a vir do que **não está nas regras mecânicas**: escolha dos ativos (tendência, setor, congruência lida pelo olho), gestão (saídas parciais, aumento de posição) e o mercado brasileiro em si.
4. **O 9.3 perde em todos os mercados**, e o **forex é o pior ambiente** para a família no diário: o spread pesa demais em relação ao movimento.

## Ações da B3 (o mercado do Palex): `tools/quant_research/check_9x_b3.py`

Dados diários públicos (API de gráficos do Yahoo Finance, tickers `.SA`), ajustados por desdobramentos e proventos. São 59 ações líquidas do Ibovespa com cerca de 20 anos de histórico (11 tickers renomeados ou fora da fonte ficaram de fora). Custo de ação à vista: 0,05% por lado, sem swap e sem corretagem; imposto de renda não incluído. **Viés de sobrevivência:** só entram as ações que estão no índice hoje, o que favorece o resultado.

**Só compra, saída pela MME9:**

| Setup | Filtro | IS | OOS |
|---|---|---|---|
| 9.1 | congruência semanal | +0,086 R (t 2,04) | +0,095 R (t 2,44) |
| 9.2 | semanal + SMA200 | +0,294 R (t 2,49) | +0,135 R (t 2,09) |
| 9.3 | semanal + SMA200 | −0,028 R | +0,194 R (t 4,95) |
| 9.4 | semanal | +0,101 R (t 1,86) | +0,057 R (t 0,97) |

À primeira vista, o 9.x **dá lucro** na B3, ao contrário dos CFDs. Três verificações qualificam esse resultado:

1. **Ano a ano:** o 9.1 com congruência semanal fica positivo em 15 de 27 anos. Boa parte do lucro vem de poucos anos fortes (2003, 2005, 2009, 2019).
2. **Trades correlacionados:** dezenas de ações dão sinal juntas quando o mercado se move. Com o resultado agregado **por mês**, o t cai para **0,35** (9.1) e **0,49** (9.2): deixa de ser estatisticamente significativo.
3. **Comparação com entradas aleatórias** (mesmas ações e quantidade de trades, qualquer dia com MME9 subindo e semanal a favor, mesma ordem stop, mesmo stop e mesma saída pela MME9; 30 sorteios): o aleatório rende **+0,16 R em média** (de +0,02 a +0,46). O 9.1 (+0,09 R) supera só 33% dos sorteios; o 9.2 (+0,23 R), 73%.

**Leitura:** o lucro do 9.x na B3 é real no período, mas **não vem do gatilho do setup**. Ele vem de (a) a **tendência de alta de longo prazo** das ações brasileiras (comprar a favor da tendência tende a ganhar) e (b) a **saída conduzida pela MME9**, que deixa o lucro correr nas tendências longas. Uma entrada qualquer a favor da tendência com a mesma saída teria resultado parecido. Isso ajuda a explicar por que muitos operadores ganham com o 9.x na B3: o que trabalha a favor deles é o mercado e a condução do trade, mais que o padrão do candle.

### Comparação com CDI, Ibovespa e comprar e segurar (`tools/quant_research/compare_b3.py`)

Carteiras de peso igual entre as ações disponíveis em cada dia. No 9.x, cada ação tem uma posição por vez pelas regras do livro, e fora da posição o dinheiro rende o CDI (série SGS 12 do Banco Central). Ibovespa = `^BVSP`. Custo de 0,05% por lado; **sem imposto de renda**.

| Carteira | Desde 2005: ao ano / queda máx. | Desde 2016: ao ano / queda máx. |
|---|---|---|
| CDI | 10,61% / 0% | 9,60% / 0% |
| Ibovespa | 9,88% / −60,0% | 15,39% / −46,8% |
| Comprar e segurar as 59 ações (peso igual) | 22,75% / −54,1% | 22,00% / −46,3% |
| **9.1 + semanal**, fora da posição no CDI (investido 22% do tempo) | **9,89% / −7,9%** | **9,14% / −7,9%** |
| **9.2 + semanal + SMA200**, fora da posição no CDI (investido 8–9% do tempo) | **10,33% / −2,3%** | **10,53% / −2,5%** |

**Leitura:**
- O 9.x mecânico **não supera o CDI**. Como fica investido só 8% a 22% do tempo, ele é, na prática, "CDI com um pouco de ações", com quedas pequenas.
- O **comprar e segurar** as 59 ações rende 22% ao ano, mas esse número está **muito inflado pelo viés de sobrevivência**: são as ações que estão no índice hoje, as vencedoras. O Ibovespa, que inclui as que saíram, rendeu perto do CDI desde 2005.
- Depois do imposto de renda (15% sobre ganhos), o 9.x fica abaixo do CDI. Em fundos e títulos, o imposto também incide, mas há regras próprias (a tabela regressiva do CDI chega a 15% depois de dois anos).
- Conclusão para a B3: **o 9.x reduz muito o risco, mas não acrescenta retorno acima da renda fixa.** Quem quer só retorno com pouco risco tem o CDI; quem aceita risco tem o índice. Um setup só agrega valor se superar uma dessas duas referências no seu próprio nível de risco.

## O que ainda não foi testado (e é o próximo passo justo)

- **Ações que saíram do índice ou quebraram** (corrigir o viés de sobrevivência com a série oficial COTAHIST da B3).
- **A seleção discricionária**: o diário de sinais (`bot.bat anotar`) existe para medir exatamente isso, anotando os sinais 9.x que o operador escolheria e comparando com os que ele descartaria.
- **Gestão com saída parcial** (por exemplo, 50% no alvo de 1× e o resto pela MME9).

## Conclusão para a ferramenta

O laboratório não deve dizer "o 9.x não dá lucro". Ele diz: **no diário, com as regras do livro, o 9.x empata antes do custo de financiamento em ações e índices americanos, e perde em forex e via CFD com swap.** Isso é útil para quem opera: indica que **o mercado (à vista, sem swap)** e **a seleção** são onde a vantagem precisa estar, e dá um protocolo para testá-las.
