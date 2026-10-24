# 0. Fundamentos teóricos

Este capítulo reúne a teoria de base que o resto do manual pressupõe: o que é o mercado em que o robô opera, por que regras técnicas **poderiam** ter vantagem num mercado competitivo, como se mede essa vantagem e por que a sobrevivência do capital vem antes do lucro. Cada seção termina ligando a teoria a uma decisão concreta do projeto.

## 0.1 O objeto de estudo: trading algorítmico de varejo

**Trading algorítmico** é a execução de decisões de compra e venda por regras explícitas, codificadas e reprodutíveis [Chan 2009]. O MT5Bot pertence a uma classe específica:

| Dimensão | No MT5Bot |
|---|---|
| Horizonte | *Swing* de curto prazo: candles de 1 hora a 1 dia; posições de horas a semanas |
| Instrumentos | CFDs de índices (HK50, US500), moedas e *commodities* numa corretora MT5 |
| Capital | Conta de varejo pequena (o caso de estudo tem cerca de US$ 16) |
| Fonte da vantagem | Padrões de preço (tendência, reversão de curto prazo), não velocidade |
| Infraestrutura | Computador doméstico modesto, sem colocação em *data center* |

Essa classe **não** compete em latência com fundos de alta frequência. Se existir vantagem, ela precisa vir de padrões que persistem por horas ou dias, onde milissegundos não importam. É isso que permite rodar o sistema num i3 com 4 GB de RAM (cap. 1 §1.1).

## 0.2 Microestrutura: o que o robô realmente negocia

### CFD, lote e valor do ponto

Um **CFD** (*contract for difference*) é um contrato com a corretora que paga a diferença de preço de um ativo de referência entre a abertura e o fechamento, sem posse do ativo [Harris 2003]. No MT5 o tamanho da posição é medido em **lotes**; cada instrumento define:

- **tick size:** a menor variação de preço (ex.: 1 ponto no HK50);
- **tick value:** quanto 1 tick vale, em dinheiro, para 1 lote, **na moeda de cotação** do instrumento;
- **volume mínimo, passo e máximo:** a granularidade dos lotes (tipicamente 0,01).

O ganho de uma posição é $\Pi = \frac{P_{\text{saída}} - P_{\text{entrada}}}{\text{tick size}} \times \text{tick value} \times q$ (sinal invertido na venda). Quando o instrumento é cotado numa moeda diferente da conta (HK50 em HKD numa conta em USD), o valor precisa ser convertido; o projeto usa `order_calc_profit` do próprio MT5 para isso (cap. 6 §6.1).

### *Bid*, *ask* e *spread*

A corretora cota dois preços: o **bid** (pelo qual compra de você) e o **ask** (pelo qual vende a você). A diferença é o ***spread***, o custo mais básico de cada operação: uma compra começa perdendo o *spread* no instante em que abre [Harris 2003]. O *spread* varia ao longo do dia e se alarga em horários de baixa liquidez e em notícias. Por isso o projeto:

- simula com o **spread registrado em cada candle**, e não com um valor médio (cap. 8 §8.2);
- aborta ordens com *spread* acima do limite do ativo (cap. 6 §6.7);
- restringe horários por ativo (janela institucional do HK50).

### Margem, alavancagem e *swap*

Para abrir uma posição, a corretora bloqueia uma **margem**, uma fração do valor nocional. A razão entre o nocional e a margem é a **alavancagem**. Alavancagem não muda a expectativa de uma estratégia, mas multiplica a variância do resultado em relação ao capital: com pouca margem livre, uma sequência normal de perdas pode zerar a conta. Posições mantidas de um dia para o outro pagam ou recebem ***swap***, a taxa de rolagem do financiamento implícito.

### Tipos de ordem e onde vive o *stop*

| Ordem | Uso no projeto |
|---|---|
| A mercado | Rotas quant: entrada na abertura do candle seguinte ao sinal |
| *Buy stop* / *sell stop* | Setups clássicos: entra só se o preço romper a máxima/mínima do candle de sinal |
| *Stop loss* / *take profit* | Gravados **na ordem**, no servidor da corretora |

A diferença entre o preço pedido e o executado é o ***slippage***. Um *stop* gravado no servidor protege a posição mesmo com o computador desligado; um *stop* "mental", mantido só pelo programa, não. Essa é a base do princípio 1 da constituição (cap. 1 §1.1).

## 0.3 Por que regras técnicas poderiam funcionar?

### Hipótese dos mercados eficientes

Na formulação de [Fama 1970], um mercado é eficiente quando os preços refletem plenamente a informação disponível. Na **forma fraca**, a informação é o histórico de preços; se ela vale, nenhuma regra baseada só em preços passados obtém retorno anormal de forma consistente, depois de custos. A intuição remonta a [Samuelson 1965]: preços corretamente antecipados flutuam de forma imprevisível.

Se a forma fraca valesse de modo estrito, o projeto inteiro seria inútil. Por isso a pergunta científica central do MT5Bot é empírica: **existe, depois de custos reais, alguma regra de preço com expectativa positiva fora da amostra?** O cap. 8 é a tentativa de respondê-la sem se enganar.

### Evidência empírica sobre análise técnica

- [Brock, Lakonishok & LeBaron 1992] testaram médias móveis e rompimentos no índice Dow Jones por 90 anos e encontraram retornos condicionais diferentes dos de passeios aleatórios e de modelos GARCH.
- [Lo, Mamaysky & Wang 2000] formalizaram padrões gráficos com regressão não paramétrica e mostraram que eles carregam alguma informação incremental.
- [Park & Irwin 2007] revisaram cerca de 95 estudos modernos: a maioria relata lucros, mas muitos sofrem de *data snooping*, de custos mal modelados e de risco ignorado.
- [Aronson 2006] argumenta que a análise técnica só é defensável quando tratada como hipótese testável, com inferência estatística e correção para buscas múltiplas.

A leitura honesta é que **algumas** regras simples tiveram vantagem em **alguns** mercados e períodos, e que a maior parte do que se publica como vantagem é artefato de mineração de dados. O projeto adota essa postura: os setups dos livros-fonte são tratados como **hipóteses**, e só operam ao vivo os que passaram por validação (decisão D5, cap. 5).

### Finanças comportamentais e limites à arbitragem

Duas famílias de anomalias documentadas sustentam as duas rotas quant:

| Efeito | Evidência | Mecanismo proposto | Rota do projeto |
|---|---|---|---|
| **Reversão de curto prazo** | [De Bondt & Thaler 1985; Lo & MacKinlay 1990] | Reação exagerada a notícias e à pressão de liquidez; o preço "passa do ponto" e volta | RSI2MR (US500 D1) |
| **Momento / tendência** | [Jegadeesh & Titman 1993; Moskowitz, Ooi & Pedersen 2012] | Sub-reação e difusão lenta da informação; tendências persistem | PULLB (HK50 H4) |

A **teoria da perspectiva** de [Kahneman & Tversky 1979] descreve vieses que alimentam esses efeitos: aversão à perda, tendência de realizar ganhos cedo e segurar perdas. E [Shleifer & Vishny 1997] explicam por que distorções podem persistir: arbitrar custa capital, tem risco e tem horizonte limitado, então nem toda ineficiência é eliminada.

### Mercados adaptativos

A **hipótese dos mercados adaptativos** [Lo 2004] reconcilia eficiência e anomalias: os participantes aprendem e se adaptam, e as vantagens aparecem, são exploradas e se desgastam ao longo do tempo. Duas consequências práticas para o projeto:

1. uma vantagem validada no passado **pode desaparecer**; por isso o HK50 PULLB é tratado como experimento ao vivo, com acompanhamento (cap. 8 §8.7);
2. faz sentido medir continuamente o desempenho real contra o esperado (telemetria, cap. 9) em vez de confiar num backtest para sempre.

## 0.4 Medir a vantagem: expectativa matemática

### Expectativa em unidades de risco

Seja $R$ o risco de um trade (a perda se o *stop* for atingido). Se a estratégia acerta com probabilidade $p$ e o ganho médio é $b \cdot R$ (o *payoff*), a **expectativa por trade**, em múltiplos de $R$, é

$$E = p \cdot b - (1 - p).$$

Os livros-fonte trazem a mesma fórmula como "regra de ouro": **nunca operar com expectativa negativa** [Fernandes, Fundamentos]. Duas consequências diretas:

- **Taxa de acerto de equilíbrio:** $E = 0 \iff p^* = \frac{1}{1 + b}$. Com alvo de 2R (PULLB), basta acertar mais de 1/3 dos trades; com 1R, mais da metade. É por isso que o limiar do filtro de ML é 0,40, e não 0,50 (cap. 7 §7.3).
- **Custos em unidades de risco:** se cada trade paga um custo $c$ (spread, comissão, *swap*) expresso em $R$, a expectativa líquida é $E_{\text{líq}} = p\,b - (1-p) - c$. Um *stop* curto encarece cada trade em termos relativos, porque o mesmo *spread* vale uma fração maior de $R$. Daí a trava que rejeita *stops* menores que 1,5 × *spread* (cap. 6 §6.1).

### Métricas usadas no projeto

| Métrica | Definição | Leitura |
|---|---|---|
| Taxa de acerto | trades vencedores / total | Não basta sozinha; depende do *payoff* |
| *Payoff* | ganho médio / perda média | Junto com a taxa, determina $E$ |
| Fator de lucro | Σ ganhos / \|Σ perdas\| | > 1 significa lucro; para $p$ e $b$ constantes, $PF = \frac{p\,b}{1-p}$ |
| Queda máxima (*max drawdown*) | Maior queda do pico ao vale da curva de capital | Mede a dor e o risco de ruína |
| Estatística t | $\bar x / (s/\sqrt{n})$ do lucro por trade | Distingue média positiva de acaso (cap. 8 §8.6) |
| Índice de Sharpe | Retorno médio / desvio-padrão [Sharpe 1994] | Comparação entre estratégias; não usado como critério principal por causa das amostras pequenas |

### Sequências de perdas são normais

Mesmo com $E > 0$, sequências longas de perdas acontecem. Com taxa de erro $q = 1 - p$, o comprimento da maior sequência de perdas em $n$ trades cresce aproximadamente como $\log_{1/q} n$ [Feller 1968]. Para o PULLB ($q \approx 0{,}6$, $n = 277$): $\ln 277 / \ln(1/0{,}6) \approx 11$ perdas seguidas são **esperadas** ao longo do histórico. Um sistema que não sobrevive a 11 *stops* seguidos não sobrevive à própria estratégia.

## 0.5 Sobreviver antes de lucrar

### Assimetria das perdas

Depois de perder uma fração $x$ do capital, é preciso ganhar $x/(1-x)$ para voltar ao ponto de partida: 10% pedem 11%, 50% pedem 100% e 90% pedem 900%. Perdas grandes são desproporcionalmente difíceis de recuperar, o que justifica limitar a perda por trade e por dia (cap. 6).

### Crescimento geométrico e Kelly

Arriscando uma fração fixa $f$ do capital por trade, o crescimento logarítmico esperado por trade é

$$G(f) = p \ln(1 + f\,b) + (1 - p)\ln(1 - f),$$

maximizado na **fração de Kelly** $f^* = p - \frac{1-p}{b}$ [Kelly 1956; Thorp 2006]. Acima de $2f^*$, o crescimento esperado fica negativo **mesmo com expectativa positiva**: apostar demais destrói uma estratégia boa. Como $p$ e $b$ são só estimativas, a prática recomenda uma fração de Kelly [MacLean, Thorp & Ziemba 2011]. O projeto usa risco fixo de 1% e, quando há uma probabilidade estimada, meio Kelly com limites (cap. 6 §6.2).

### Ruína

Com uma aposta de tamanho fixo em dinheiro, a probabilidade de ruína é positiva mesmo com vantagem, e cresce quanto menor o capital em relação à aposta: é o problema clássico da **ruína do jogador** [Feller 1968]. Arriscar uma fração do saldo, e não um valor fixo, torna a ruína assintótica, porque a aposta encolhe com o capital [Vince 1990]. No limite inferior, porém, o lote mínimo impõe um piso: com saldo muito pequeno, até o menor lote arrisca uma fração grande. É o que o *Risk Shield* e as travas por rota tratam (cap. 6 §6.1 e §6.3).

### O que a evidência diz sobre o investidor de varejo

A literatura é dura com o operador individual. [Barber & Odean 2000] mostram que os investidores que mais negociam têm os piores retornos líquidos. No Brasil, [Chague, De-Losso & Giovannetti 2019] acompanharam todos os indivíduos que fizeram *day trade* de minicontratos de índice e encontraram que a imensa maioria dos que persistiram perdeu dinheiro. Na Europa, o regulador constatou que entre 74% e 89% das contas de varejo em CFDs perdiam dinheiro, e restringiu a alavancagem oferecida [ESMA 2018].

Esses números justificam a filosofia declarada do projeto: o objetivo é **perder cada vez menos**, operando só o que tem evidência, com risco pequeno e travas independentes.

## 0.6 Da teoria às decisões do projeto

| Fundamento | Decisão de projeto | Onde |
|---|---|---|
| Forma fraca da eficiência: a vantagem é a exceção | Setups são hipóteses; só o validado opera ao vivo (D5) | cap. 5, 8 |
| *Data snooping* e comparações múltiplas | Robustez da família, teste de sorte, $t$ e generalização | cap. 8 |
| Mercados adaptativos | Rota PULLB tratada como experimento; telemetria contínua | cap. 8, 9 |
| Custos em unidades de risco | *Spread* por candle no backtest; trava de *stop* mínimo | cap. 6, 8 |
| Ruína e assimetria das perdas | Risco fracionário, *Risk Shield*, perda diária máxima | cap. 6 |
| Kelly com estimativas incertas | Meio Kelly com piso e teto | cap. 6 |
| *Stop* precisa sobreviver ao computador | SL/TP gravados no servidor; arquitetura *stateless* | cap. 1, 3 |
| Evidência negativa do varejo | Confirmação explícita de conta REAL | cap. 6 §6.6 |

## 0.7 Referencial teórico

[Fama 1970; Samuelson 1965] eficiência de mercado; [Lo 2004] mercados adaptativos; [Brock, Lakonishok & LeBaron 1992; Lo, Mamaysky & Wang 2000; Park & Irwin 2007; Aronson 2006] evidência sobre análise técnica; [De Bondt & Thaler 1985; Lo & MacKinlay 1990] reversão; [Jegadeesh & Titman 1993; Moskowitz, Ooi & Pedersen 2012] momento; [Kahneman & Tversky 1979] teoria da perspectiva; [Shleifer & Vishny 1997] limites à arbitragem; [Harris 2003] microestrutura; [Chan 2009] trading quantitativo; [Kelly 1956; Thorp 2006; MacLean, Thorp & Ziemba 2011; Vince 1990] dimensionamento; [Feller 1968] ruína e sequências; [Sharpe 1994]; [Barber & Odean 2000; Chague, De-Losso & Giovannetti 2019; ESMA 2018] desempenho do varejo; [Fernandes, Fundamentos] expectativa nos livros-fonte.
