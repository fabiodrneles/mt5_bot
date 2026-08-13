# Referências e Gigantes do Quant Trading

> "Nós não tentamos ser mais rápidos que a Virtu Financial. Nós surfamos a anomalia (a 'sujeira') que as grandes instituições deixam para trás quando movimentam o mercado."

Para manter o foco, a motivação e o alinhamento arquitetônico do projeto, documentamos as maiores mentes e instituições que pavimentaram a indústria do **Trading Quantitativo** e do **High-Frequency Trading (HFT)**. Nosso projeto bebe diretamente dessas fontes.

## Instituições de Elite

### D. E. Shaw & Co.
Fundada pelo cientista da computação David E. Shaw nos anos 80, foi pioneira no uso de supercomputadores para encontrar anomalias de preços em milissegundos. É notória por contratar apenas a elite acadêmica (Top 1% de Harvard, MIT, Stanford) em matemática. Curiosidade: Jeff Bezos trabalhou lá como engenheiro de software e aprendeu a filosofia guiada a dados antes de fundar a Amazon.

### Two Sigma
Fundo que trata o mercado não como economia, mas como um imenso problema de ciência de dados. Eles utilizam Petabytes de informações alternativas (sentimento de Twitter, imagens de satélite para contar carros em estacionamentos, dados climáticos) e processam tudo com Inteligência Artificial para operar.

### Virtu Financial
Gigante do *Market Making* (criação de mercado). A Virtu faz milhões de operações por dia lucrando frações microscópicas de centavos em cada uma. Em 2014, revelaram um dado assombroso: em 5 anos (aprox. 1.277 dias de pregão), eles tiveram **apenas um único dia de prejuízo**. Isso demonstra o poder absoluto da matemática, estatística e execução de baixíssima latência (em C++).

## Mentes Brilhantes ("Os Deuses Quants")

### Marcos López de Prado
Autor da "bíblia" moderna *Advances in Financial Machine Learning*. Ele denuncia que a maioria esmagadora do mercado aplica Machine Learning da forma errada (cometendo *overfitting*, onde a IA decora o passado e quebra no futuro). Ele provou que para o ML funcionar, os dados precisam ser coletados e estruturados de forma perfeitamente limpa no evento do setup — exatamente a arquitetura que usamos no nosso `ml_dataset.jsonl`. 

### Ray Dalio (Bridgewater Associates)
Transformou seu fundo num sistema computacional gigante. Criou o modelo onde regras econômicas e decisões financeiras globais são codificadas em algoritmos rígidos. O fundo opera baseado em lógica dura e processamento de dados (o conceito de *Pure Alpha*), sem interferência emocional humana na execução.

## A Realidade Matemática do Mercado

O nosso bot opera sob três pilares absolutos extraídos dessas referências:

1. **Vantagem Estatística (Edge):** Não existe setup com 100% de acerto. A Jane Street erra quase 49% das vezes. A diferença é que a matemática garante que os 51% de acerto rendem mais dinheiro que os 49% de perdas (Risk/Reward).
2. **Latência vs Frequência:** Instituições gastam centenas de milhões cavando túneis em montanhas apenas para ganhar 3 milissegundos de latência. Nós não disputamos latência de HFT com eles.
3. **Surfar a Exaustão (Z-Score):** O nosso bot captura o lucro usando os Rastros Institucionais. Quando os "grandes" empurram o preço de forma violenta, o mercado estica (gerando picos de Z-Score e RSI). O nosso robô captura a inevitável correção (elástico) dessa agressão.

**Mentalidade Operacional:** Operar lotes de teste (`0.01`) de forma fria, calculada e iterativa é o caminho dos cientistas de dados, isolando o emocional e acumulando riqueza estatística antes de escalar o capital real.
