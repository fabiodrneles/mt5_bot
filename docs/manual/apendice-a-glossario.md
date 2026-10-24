# Apêndice A. Glossário

Termos em ordem alfabética. Entre parênteses, o capítulo onde o termo é mais usado.

| Termo | Definição |
|---|---|
| **Alavancagem** | Razão entre o valor nocional da posição e a margem exigida. Multiplica a variância do resultado em relação ao capital (0) |
| **Ask / Bid** | Preço de venda e de compra cotados pela corretora. A compra entra no *ask*, a venda no *bid* (0) |
| **ATR** | *Average True Range*: média da amplitude verdadeira dos candles; mede volatilidade em unidades de preço (4) |
| **Backtest** | Simulação de uma regra sobre dados históricos (8) |
| **BM25** | Função de ranqueamento probabilística usada na memória RAG (11) |
| **Breakeven** | Mover o *stop* para o preço de entrada (no projeto, com uma pequena trava a favor) (6) |
| **Candle (vela)** | Resumo de um período em abertura, máxima, mínima e fechamento (OHLC) (3) |
| **CFD** | *Contract for difference*: contrato que paga a variação de preço de um ativo de referência sem posse dele (0) |
| **Crash loop** | Processo que cai repetidamente logo após reiniciar; o Maestro desliga o trabalhador após 3 quedas em 2 minutos (2) |
| **Data snooping** | Encontrar padrões por acaso ao testar muitas hipóteses nos mesmos dados (8) |
| **Deal** | Registro de execução no MT5; a soma dos *deals* de uma posição é o resultado real (3) |
| **Drawdown (queda)** | Queda da curva de capital desde o último pico (0, 8) |
| **EMA / SMA** | Média móvel exponencial / simples (4) |
| **Expectativa** | Ganho médio esperado por trade, $E = p\,b - (1-p)$ em unidades de risco (0) |
| **Fail-open / fail-closed** | Em caso de erro, liberar / bloquear a ação (12) |
| **Fator de lucro** | Soma dos ganhos dividida pela soma das perdas (0, 8) |
| **Features** | Variáveis de entrada de um modelo de aprendizado de máquina (7) |
| **IFR / RSI** | Índice de Força Relativa de Wilder (4) |
| **IS / OOS** | *In-sample* (dados usados para escolher) / *out-of-sample* (dados reservados para conferir) (8) |
| **Kelly (critério de)** | Fração do capital que maximiza o crescimento logarítmico esperado (0, 6) |
| **Look-ahead bias** | Usar, numa decisão simulada, informação que ainda não existia no momento (3) |
| **Lote** | Unidade de tamanho de posição no MT5 (0) |
| **Magic number** | Identificador gravado nas ordens do robô; ele só mexe no que tem o seu *magic* (6) |
| **Maestro** | Orquestrador em Go com interface de terminal (2) |
| **Margem** | Valor bloqueado pela corretora para manter uma posição aberta (0) |
| **Overfitting (sobreajuste)** | Modelo ou regra que se ajusta ao ruído dos dados históricos e não generaliza (8) |
| **Payoff** | Razão entre o ganho médio e a perda média (0) |
| **Pullback** | Recuo temporário do preço contra a tendência (5) |
| **RAG** | *Retrieval-Augmented Generation*: recuperar trechos relevantes antes de responder (11) |
| **Risk Shield** | Trava que rejeita a ordem quando o risco do lote passa de 1,5% do saldo (6) |
| **Rota quant** | Par (ativo, timeframe) com uma regra validada fora da amostra (5) |
| **RRR** | Razão risco-retorno: distância ao alvo dividida pela distância ao *stop* (5) |
| **RVOL** | Volume relativo: volume atual dividido pela média recente (4) |
| **SDD** | *Spec Driven Development*: processo guiado por especificações com requisitos e critérios de aceite (10) |
| **Setup** | Regra que identifica uma oportunidade com entrada, *stop* e alvo (5) |
| **Slippage** | Diferença entre o preço pedido e o executado (0) |
| **Smoke test** | Teste rápido de ponta a ponta que confirma que o produto instalado funciona (10) |
| **Spread** | Diferença entre *ask* e *bid*; custo pago em toda operação (0) |
| **Stateless** | Sem estado crítico em memória: o estado é relido da fonte da verdade a cada ciclo (1, 3) |
| **Stop loss / take profit** | Preços de saída com perda / com lucro, gravados na ordem (0) |
| **Swap** | Taxa de rolagem cobrada ou paga por manter a posição de um dia para o outro (0) |
| **Telemetria** | Estado da conta, posições e risco exposto às interfaces (9) |
| **Tick size / tick value** | Menor variação de preço / valor dessa variação para 1 lote (0) |
| **Trailing stop** | *Stop* que acompanha o preço a favor, sem nunca recuar (6) |
| **VWAP** | Preço médio ponderado por volume, ancorado no início do dia (4) |
| **Walk-forward** | Validação com várias janelas sucessivas de otimização e teste (8) |
| **Watchdog** | Vigia que mata um processo que parou de responder (2) |
| **Wine** | Camada de compatibilidade que roda programas Windows no Linux e no macOS (10) |
| **XGBoost** | Biblioteca de *gradient boosting* de árvores de decisão (7) |
