# Setups do Palex: teste justo em forex e na B3

> Data: 2026-10-24. Ferramentas: `tools/quant_research/palex_setups.py` (setups e simulador), `compare_palex_b3.py` (carteira contra CDI e Ibovespa) e, para a família 9.x, `check_9x_fiel.py`, `check_9x_b3.py` e `compare_b3.py` (ver `docs/validacao-9x-fiel.md`). Fonte das regras: FERNANDES, A. (Palex). *Estratégias Operacionais de Análise Técnica de Ações*, 2014 (`memoria/raw/estrategias-operacionais.txt`).

## O que foi testado

O livro tem cerca de 35 setups. Foram testados os que têm **regra mecânica completa** no texto, como o livro manda: entrada por rompimento (ordem stop) ou no fechamento, stop do livro, alvo de projeção quando o livro especifica e, quando não especifica, "conduzir pela MME9".

| Setup (página) | Regra implementada |
|---|---|
| Retorno à MM21 + Fura-teto (24) | MM21 subindo, ≥ 2 candles de recuo, **fecha** acima do fura-teto = máxima + 0,14 × (máxima − mínima) do candle anterior |
| Harami e Engolfo de alta (25), semanal | MM21 e MM50 subindo; padrão de fundo; compra acima da máxima |
| Cruzamento de médias (30) | MM5 ou MM9 cruza a MM21; entra no fechamento; sai no cruzamento contrário |
| MM200 (36) | Fecha cruzando a MM200; sai no cruzamento contrário |
| IFR14 + candle de reversão (45) | IFR14 na zona de sobrevenda (≤ 30) + candle de reversão; stop na mínima; sai na zona de sobrecompra |
| IFR2 sobrevendido (Connors, 53) | IFR2 < 5 acima da MM200; compra no fechamento; vende quando fecha acima da MM5; sem stop |
| Rompimento de topo histórico (70) | Compra acima da maior máxima histórica; stop largo (mínima de 20 candles) |
| Iguana (Jeff Cooper, 74) | Mínima de 4 candles com abertura e fechamento acima de 75% do candle; rompe a máxima |
| Latinha chacoalhada (79), semanal | Menor amplitude de 4 candles; rompimento para um dos lados |
| Inside Day (90) | Barra contida na anterior, a favor da tendência; alvo = projeção da barra-mãe |
| Shark (Walter Downs, 91) | ≥ 3 barras contidas; rompe o 1º candle; alvo = amplitude dele |
| Peg Leg (John Crane, 93) | Contra a tendência: nova máxima de 20 em até 3 candles; venda abaixo da mínima (válida 2 candles) |
| Realização frustrada (95) | Tendência de alta; baixa–alta–baixa; rompe a máxima do conjunto; alvo = amplitude |
| Key Buy (Velez e Capra, 97) | Nova máxima, depois 3+ barras com máximas e mínimas menores; rompe a última |

Já validados antes, no código do robô: 9.1–9.4, Ponto Contínuo, FFFD, IFR2 + MME50, SAR, DiNapoli e Rompimento Falso (`docs/validacao-setups.md`, `docs/validacao-9x-fiel.md`).

**Não testados**, por serem discricionários ou estarem incompletos no texto extraído: Triple Screen, Three Line Bar, Hilo Tranquilo (o período do Hi-Lo não aparece), as 10 táticas de guerrilha de Velez, triângulos, congestões, divergências e as variantes de Bollinger (estreitamento, *walking up*, escadaria, tobogã).

Universo: **forex**, 34 pares da corretora (dados MT5, com spread e swap); **B3**, 59 ações líquidas (dados públicos ajustados, 0,05% por lado, sem swap). Diário e semanal. Cada sinal é avaliado sozinho, em múltiplos do risco (R); t calculado **por mês**, para não inflar com sinais simultâneos.

## Forex: nenhum setup funciona

**Todos** os setups perdem no forex, na compra e na venda, no diário e no semanal, nos dois períodos (de −0,09 a −2,5 R por trade, t por mês quase sempre abaixo de −2). Os menos ruins são o IFR2 sobrevendido (−0,09 a −0,12 R) e o topo histórico (−0,11 R). O spread, o swap e a ausência de tendência de longo prazo nos pares de moedas eliminam qualquer vantagem.

## B3: as compras ganham, as vendas perdem

Na B3, as **vendas perdem sempre** e as **compras costumam dar positivo**. É a assinatura da tendência de alta de longo prazo das ações brasileiras, a mesma vista no 9.x. Por isso o teste que decide é a **carteira** contra o CDI e o Ibovespa.

**Carteiras de peso igual, uma posição por vez por ação, dinheiro fora da posição no CDI, sem imposto de renda** (`compare_palex_b3.py`):

| Desde 2005 | Ao ano | Queda máxima | Investido | | Desde 2016 | Ao ano | Queda máxima |
|---|---|---|---|---|---|---|---|
| **Cruz. MM9 × MM21** | **16,39%** | **−15,1%** | 55% | | **Cruz. MM9 × MM21** | **19,61%** | **−12,7%** |
| Cruz. MM5 × MM21 | 14,23% | −17,2% | 56% | | Cruz. MM5 × MM21 | 18,25% | −12,7% |
| MM200 | 13,60% | −24,8% | 58% | | Ibovespa | 15,39% | −46,8% |
| IFR2 sobrevendido | 12,44% | −6,4% | 7% | | MM200 | 11,64% | −24,8% |
| Topo histórico | 11,26% | −3,1% | 6% | | Fura-teto | 10,93% | −2,7% |
| Fura-teto | 11,03% | −2,7% | 11% | | IFR2 sobrevendido | 10,42% | −6,4% |
| IFR14 + reversão | 10,82% | −8,3% | 5% | | IFR14 + reversão | 10,37% | −8,3% |
| CDI | 10,61% | 0% | — | | Topo histórico | 10,18% | −3,1% |
| Key Buy | 10,22% | −0,7% | 2% | | CDI | 9,60% | 0% |
| Ibovespa | 9,88% | −60,0% | — | | Key Buy, Realização, Iguana | 8,3–9,2% | até −4,9% |
| Iguana, Realização frustrada | 9,1–9,2% | até −4,9% | — | | Peg Leg | 0,99% | −28,9% |
| Peg Leg | 5,65% | −28,9% | 19% | | | | |

**O cruzamento de médias contra uma exposição equivalente.** O cruzamento MM9 × MM21 fica investido 55% do tempo, e as 59 ações sobreviventes renderam 22,8% ao ano no comprar e segurar (número inflado pelo viés de sobrevivência). A comparação justa é com uma **mistura fixa de 55% nessas ações e 45% no CDI**, no mesmo universo:

| | Desde 2005: ao ano / Sharpe / queda | Desde 2016: ao ano / Sharpe / queda |
|---|---|---|
| Comprar e segurar 59 ações | 22,75% / 0,48 / −54,1% | 22,00% / 0,58 / −46,3% |
| Mistura fixa 55% ações + 45% CDI | 18,18% / 0,48 / −32,5% | 17,06% / 0,58 / −27,6% |
| **Cruz. MM9 × MM21** | **16,39% / 0,51 / −15,1%** | **19,61% / 0,79 / −12,7%** |
| Cruz. MM5 × MM21 | 14,23% / 0,34 / −17,2% | 18,25% / 0,70 / −12,7% |

(Sharpe = retorno acima do CDI por unidade de volatilidade, anualizado.)

## Leitura

1. **No forex, nenhum setup do livro tem vantagem.** A aplicação, no forex, deve operar só o que tem evidência própria (o RSI2 nos índices americanos), e não os setups do Palex.
2. **Na B3, o cruzamento MM9 × MM21 é o setup do livro com valor comprovado no teste justo.** Ele rende o mesmo ou mais que uma exposição equivalente às ações, com Sharpe igual ou maior e **metade da queda máxima**. É o comportamento clássico do *timing* por médias móveis [Faber 2007]: o valor está em sair das ações nas tendências de baixa.
3. **Os setups de entrada de curto prazo** (Iguana, Key Buy, Realização frustrada, Shark, Inside Day, IFR14) ficam investidos pouco tempo e rendem perto do CDI ou abaixo dele. Os que vão contra a tendência (Peg Leg) perdem.
4. **A B3 é o mercado da aplicação para os setups do Palex**, mas com a lógica de seguir tendência e controlar quedas, e não a de prever reversões em candles.

## Sem viés de sobrevivência: série oficial COTAHIST da B3 (`tools/quant_research/cotahist_b3.py`)

Arquivos anuais oficiais de 2004 a 2026 (mercado à vista, lote padrão), com **todas** as empresas negociadas, inclusive as que depois saíram da bolsa, faliram ou foram compradas. **Universo ponto-no-tempo:** em cada ano, as 60 ações com maior volume financeiro no ano anterior. Ao todo, 193 ações passaram pelo universo. Os desdobramentos e grupamentos foram detectados e ajustados (202 eventos, incluindo a antiga cotação "por lote de mil"). Dias de negócio único com salto acima de 30% foram descartados, e quedas reais (como a das Americanas em 2023) foram mantidas. **Proventos não foram incluídos:** isso subestima todas as carteiras de ações em cerca de 3% a 5% ao ano no comprar e segurar (proporcionalmente menos nas estratégias que ficam parte do tempo no CDI), enquanto o Ibovespa é um índice de retorno total.

| Carteira (sem IR, sem proventos) | Desde 2005: ao ano / Sharpe / queda | Desde 2016: ao ano / Sharpe / queda |
|---|---|---|
| CDI | 10,61% / — / 0% | 9,60% / — / 0% |
| Ibovespa (com proventos) | 9,89% / 0,10 / −60,0% | 15,39% / 0,34 / −46,8% |
| Comprar e segurar o universo ponto-no-tempo | 3,86% / −0,12 / −61,9% | 8,58% / 0,09 / −51,6% |
| Mistura fixa 55% ações + 45% CDI | 7,73% / −0,12 / −35,9% | 9,91% / 0,09 / −31,4% |
| **Cruz. MM9 × MM21** | **8,24% / −0,12 / −24,5%** | **12,20% / 0,25 / −22,1%** |
| Cruz. MM5 × MM21 | 6,29% / −0,27 / −27,6% | 9,97% / 0,09 / −25,2% |
| MM200 | 5,14% / −0,43 / −21,5% | 5,15% / −0,33 / −21,5% |

**Leitura:**
1. **O viés de sobrevivência inflava muito os números.** Com as empresas que saíram do índice, o comprar e segurar cai de 22,8% para 3,9% ao ano desde 2005 (sem proventos), e o cruzamento MM9 × MM21 de 16,4% para 8,2%.
2. **O cruzamento MM9 × MM21 continua sendo o melhor setup do livro**, e a vantagem relativa sobrevive. Contra uma exposição equivalente às mesmas ações, ele rende igual ou mais (8,2% contra 7,7% desde 2005; 12,2% contra 9,9% desde 2016), com Sharpe igual ou maior (−0,12 contra −0,12; 0,25 contra 0,09) e **queda máxima bem menor** (−24,5% contra −35,9%; −22,1% contra −31,4%).
3. **Contra a renda fixa, não há vantagem clara.** Somando os proventos que faltam (cerca de 2% ao ano para quem fica 55% investido), o cruzamento fica perto do CDI desde 2005 e um pouco acima desde 2016. O valor real dele é **reduzir as quedas de quem quer estar em ações**, não superar o CDI.
4. As médias MM5 × MM21 e MM200 ficam abaixo da exposição equivalente.

### Todos os setups de compra do livro na série oficial (sem IR, sem proventos)

| Setup | Desde 2005: ao ano / Sharpe / queda | Desde 2016: ao ano / Sharpe / queda |
|---|---|---|
| CDI | 10,61% / — / 0% | 9,60% / — / 0% |
| **IFR2 sobrevendido (Connors)** | **11,67% / 0,36 / −5,3%** | **10,28% / 0,27 / −4,5%** |
| IFR14 + reversão | 9,77% / −0,17 / −13,3% | 9,79% / 0,07 / −10,1% |
| Key Buy | 9,74% / −0,98 / −0,8% | 8,94% / −0,66 / −0,8% |
| Topo histórico | 9,69% / −0,52 / −1,9% | 8,71% / −0,59 / −1,9% |
| 9.4 + semanal | 9,62% / −0,41 / −1,9% | 8,87% / −0,30 / −1,9% |
| Fura-teto | 8,91% / −0,52 / −2,7% | 8,46% / −0,33 / −2,7% |
| 9.2 + semanal + SMA200 | 8,80% / −0,86 / −1,5% | 8,98% / −0,25 / −1,4% |
| Iguana | 8,56% / −1,00 / −4,5% | 7,96% / −0,85 / −3,8% |
| Cruz. MM9 × MM21 | 8,24% / −0,12 / −24,5% | 12,20% / 0,25 / −22,1% |
| 9.3 + semanal + SMA200 | 7,52% / −0,96 / −2,6% | 8,73% / −0,23 / −2,6% |
| Realização frustrada | 6,98% / −0,82 / −5,3% | 6,77% / −0,60 / −5,3% |
| Cruz. MM5 × MM21 | 6,29% / −0,27 / −27,6% | 9,97% / 0,09 / −25,2% |
| 9.1 + semanal | 5,65% / −0,91 / −7,5% | 5,75% / −0,69 / −7,5% |
| MM200 | 5,14% / −0,43 / −21,5% | 5,15% / −0,33 / −21,5% |
| Peg Leg | −0,39% / −1,48 / −41,8% | −0,97% / −1,35 / −32,6% |

Os setups de curto prazo ficam investidos pouco tempo e, por isso, rendem perto do CDI (que recebem fora da posição) com quedas pequenas. O Sharpe negativo mostra que **a parte investida rende menos que o CDI**. As exceções são:
- **IFR2 sobrevendido (Connors):** o único setup do livro que **supera o CDI nos dois períodos** sem viés de sobrevivência (11,7% contra 10,6% desde 2005; 10,3% contra 9,6% desde 2016), com Sharpe positivo (0,36 e 0,27) e queda máxima de só 5%. Como fica pouco tempo investido, a falta de proventos quase não o afeta. É o mesmo efeito que sustenta a rota RSI2 do US500: reversão de curto prazo comprando quedas fortes em tendência de alta.
- **Cruz. MM9 × MM21:** melhor que a exposição equivalente às ações, com metade da queda, mas sem vantagem clara sobre o CDI.
- **Peg Leg** (contra a tendência) perde dinheiro.

### IFR2 do Stormer (adaptação brasileira do IFR2)

Pedido do dono, a partir do vídeo "Setup IFR2 Stormer". O vídeo não pôde ser lido, então foi testada a **descrição mais comum** do setup: IFR2 abaixo de 25 (ou 10) no fechamento; compra no fechamento; alvo na máxima dos 2 últimos candles; saída por tempo depois de 7 candles; sem stop de preço; com e sem o filtro da MM200. Série oficial COTAHIST, universo ponto-no-tempo:

| Variante | Desde 2005: ao ano / Sharpe / queda | Desde 2016: ao ano / Sharpe / queda |
|---|---|---|
| CDI | 10,61% / — / 0% | 9,60% / — / 0% |
| IFR2 Connors (referência acima) | **11,67% / 0,36 / −5,3%** | **10,28% / 0,27 / −4,5%** |
| Stormer, IFR2 < 10 + MM200 | 10,88% / 0,08 / −8,4% | 8,88% / −0,14 / −8,4% |
| Stormer, IFR2 < 10 | 10,41% / 0,05 / −32,4% | 8,26% / −0,04 / −32,4% |
| Stormer, IFR2 < 25 + MM200 | 9,45% / −0,12 / −16,1% | 8,66% / −0,10 / −16,1% |
| Stormer, IFR2 < 25 | 6,52% / −0,16 / −38,4% | 8,86% / 0,04 / −37,0% |

**Leitura:** a versão do Stormer, com alvo curto na máxima de 2 candles, saída por tempo e sem stop, fica **no nível do CDI ou abaixo**, com quedas maiores sem o filtro da MM200 (a falta de stop pesa nas ações que despencam). A versão original de Connors, que sai quando o fechamento passa da MM5, foi melhor nos dois períodos. Se o vídeo usar parâmetros diferentes, basta ajustá-los em `palex_setups.py` (sinal "IFR2 Stormer") e rodar `ONLY="IFR2" python cotahist_b3.py`.

## Ressalvas

- **Viés de sobrevivência:** as tabelas com dados do Yahoo incluem só as ações que estão no Ibovespa hoje. A seção COTAHIST acima corrige isso e é a referência.
- **Proventos** faltam na série COTAHIST, o que penaliza todas as carteiras de ações em relação ao CDI e ao Ibovespa.
- **Imposto de renda** (15% sobre ganhos em operações comuns) e o rebalanceamento diário de peso igual não foram modelados.
- **Vários setups foram testados.** O cruzamento de médias é uma regra conhecida há décadas e documentada fora deste estudo, o que reduz, mas não elimina, o risco de seleção.
- Antes de operar com dinheiro, o cruzamento MM9 × MM21 na B3 deve rodar em **modo estudo** numa conta demo da Clear ou da Genial (o robô já escolhe o terminal pelo `mt5_path`).
