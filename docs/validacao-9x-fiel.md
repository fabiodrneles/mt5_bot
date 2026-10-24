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

## O que ainda não foi testado (e é o próximo passo justo)

- **Ações da B3**, o mercado do Palex: a corretora do projeto não oferece B3. Seria preciso outra fonte de dados diários (por exemplo, cotações históricas públicas da B3) e o custo real de corretagem e emolumentos, sem swap.
- **A seleção discricionária**: o diário de sinais (`bot.bat anotar`) existe para medir exatamente isso, anotando os sinais 9.x que o operador escolheria e comparando com os que ele descartaria.
- **Gestão com saída parcial** (por exemplo, 50% no alvo de 1× e o resto pela MME9).

## Conclusão para a ferramenta

O laboratório não deve dizer "o 9.x não dá lucro". Ele diz: **no diário, com as regras do livro, o 9.x empata antes do custo de financiamento em ações e índices americanos, e perde em forex e via CFD com swap.** Isso é útil para quem opera: indica que **o mercado (à vista, sem swap)** e **a seleção** são onde a vantagem precisa estar, e dá um protocolo para testá-las.
