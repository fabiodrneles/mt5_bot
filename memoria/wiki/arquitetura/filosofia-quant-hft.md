# Filosofia Quant e Engenharia de Execução (HFT)

> "Treinar pesado offline, executar leve e rápido online."

Nossa arquitetura (Cérebro em Python + Maestro em Go) não foi escolhida por acaso. Ela herda a filosofia de engenharia de software das maiores instituições financeiras e empresas de tecnologia do mundo. Quando operamos com hardware limitado (ex: i3 4ª geração, 4GB RAM), não podemos nos dar ao luxo de rodar redes neurais profundas e pesadas no momento da execução das ordens. O *delay* (latência) seria fatal.

## A "Sacada de Gênio": Separação entre Inteligência e Execução

A grande disrupção do nosso bot é separar completamente o aprendizado da execução:

1. **A Fábrica de Ingredientes (Python):** O bot passa o dia inteiro coletando dados tabulares ricos (Z-Score, RSI, Distância de Médias, ATR, tamanho do corpo/pavio) toda vez que um setup é armado. Esses dados formam um dataset multivariável perfeito (`ml_dataset.jsonl`).
2. **O Treino Noturno (Python/ML):** Fora do horário de pregão, usamos algoritmos baseados em Árvores de Decisão (como **XGBoost** ou **LightGBM**) — que são extremamente superiores a Deep Learning para dados tabulares financeiros — para encontrar os padrões ocultos.
3. **A Injeção Direta (Golang):** O modelo treinado é exportado para uma fórmula matemática limpa (matrizes, regras *if/else* de árvores ou formato ONNX) e injetado diretamente no nosso orquestrador em **Go**. O Go, sendo compilado e hiper-rápido, lê essa fórmula em microssegundos e aprova ou veta a ordem no MetaTrader 5 sem pesar a CPU ou a memória.

## Inspirações Reais e Casos de Sucesso

### Renaissance Technologies (O Fundo Medallion)
Fundado pelo matemático Jim Simons, é o fundo quantitativo mais rentável da história. A genialidade de Simons foi contratar matemáticos, astrônomos e físicos em vez de economistas. Eles usam cadeias de Markov, estatística avançada e algoritmos em linguagens de baixíssimo nível (C/C++) para garantir que as predições matemáticas sejam executadas sem atrasos.

### Jane Street e Citadel Securities
Sendo os maiores criadores de mercado (*Market Makers*) globais, eles proveem liquidez para a bolsa. A Jane Street é famosa por usar **OCaml** (uma linguagem funcional altamente performática e segura) para seus sistemas de execução. O aprendizado de máquina acontece nos bastidores (offline) lidando com petabytes de dados, mas o que vai para o "campo de batalha" são modelos de execução extremamente enxutos e compilados, desenhados para não falhar nem engasgar.

### Uber e o "Surge Pricing"
Na área de tecnologia, a Uber resolve um problema semelhante. O algoritmo que calcula o preço dinâmico (Surge) é treinado usando **XGBoost** (Machine Learning para tabelas). No entanto, o motor que aguenta os milhões de passageiros e motoristas solicitando o preço ao mesmo tempo é escrito em **Golang**. O modelo Python gera as regras, e o Go executa as regras em tempo real.

### A Comunidade Elite do MQL5
Os desenvolvedores HFT (High Frequency Trading) de elite no MetaTrader 5 treinam seus algoritmos quantitativos no Python (geralmente usando **CatBoost**) e, em seguida, exportam toda a árvore de decisão resultante para código nativo (C++ ou MQL5 puro). Dessa forma, a "inteligência artificial" não exige a abertura de um interpretador Python na hora do trade, economizando memória e protegendo a latência.

## Conclusão
Ao adotarmos lotes de `0.01` hoje e guardarmos minuciosamente os dados, estamos agindo exatamente como os pesquisadores da Renaissance Technologies em seus primeiros anos: acumulando probabilidade e estatística. Nossa IA do futuro não será pesada nem tentará "adivinhar" gráficos com imagens; será um motor matemático cirúrgico que roda liso até no computador mais modesto, validando a genialidade por trás do **Maestro em Go**.
