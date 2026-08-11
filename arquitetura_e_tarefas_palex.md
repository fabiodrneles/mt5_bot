# Arquitetura e Tarefas: Motor Quantitativo Palex (Go + Python)

Este documento foi criado para preservar o contexto do desenvolvimento caso a sessão atual perca o limite de tokens. Ele detalha exatamente o que deve ser implementado, a arquitetura e as fórmulas de cálculo.

## 1. A Arquitetura (Golang Maestro + Python Brain)

Foi decidido e aprovado que a aplicação não usará Docker/Linux. Rodará inteiramente no Windows (devido à limitação do MetaTrader 5). A máquina alvo é um i3 com 4GB de RAM, exigindo que o código seja extremamente leve.

### Como vai funcionar:
- **Golang (O Maestro):** Será responsável pelo gerenciamento de processos e ordens. O Go roda leve, conecta na porta do MT5 e monitora o ciclo de vida. Para cada par de moedas/ativo em operação, o Go *spawnará* (via `os/exec`) um processo isolado em Python. O Go também fará ping periódico ("Heartbeat") via `stdin/stdout` com o Python para garantir que ele não travou.
- **Python (O Cérebro):** Será responsável estritamente pela matemática e lógica da estratégia. Rodando via Pandas e NumPy, os cálculos vetorizados nas séries de preço (que serão pequenas janelas temporais de velas, para economizar RAM) determinarão o sinal. Se houver sinal, o Python cospe um JSON no stdout: `{"action": "buy", "setup": "9.1", "stop": 10.0, "take_profit": 11.5}`. O Golang lê isso e envia a ordem para o MT5.

## 2. As Fórmulas e Lógicas (Motor de Setups)

Os seguintes modelos matemáticos foram extraídos dos livros do Palex e devem ser vetorizados no Python (via Pandas):

- **Filtros e Geometria:**
  - **Bandas de Bollinger:** SMA(20) ± 2 * Desvio Padrão. Mede volatilidade e trava entradas em lateralidade extrema.
  - **Fibonacci:** Cálculos dinâmicos de Retração (limite de anulação em 61.8%) e Projeção (alvo mínimo de 1.618x do risco).
  - **Filtro Macro:** SMA(200) bloqueia compras abaixo dela e vendas acima dela. SMA(21) valida a direção da tendência secundária.

- **Os Setups (EMA 9 e SMA 21):**
  - **Setup 9.1:** Virada da EMA 9 contra a tendência. Gatilho na máxima do candle que fez a EMA virar.
  - **Setup 9.2:** EMA 9 na direção principal. Fechamento contra a direção, superação da máxima aciona a entrada.
  - **Setup 9.3:** EMA 9 na direção principal. Dois fechamentos contra a direção. Superação da máxima do último aciona a entrada.
  - **Setup 9.4:** Falsa reversão da EMA 9 que volta a apontar para a tendência no candle seguinte.
  - **Ponto Contínuo (PC):** Retorno rigoroso e aproximação à SMA 21 em um forte ciclo de tendência. Gatilho no rompimento a favor.
  - **FFFD (Fechou Fora, Fechou Dentro):** Rompimento da máxima/mínima de um candle que fechou de volta para dentro das Bandas de Bollinger de 2 desvios.

- **Scoring:** Em caso de sobreposição (ex: um candle ativa 9.3 e Ponto Contínuo ao mesmo tempo), o sistema de scoring pontua mais alto o setup composto, garantindo uma única entrada de alta probabilidade ("Golden Setup").

## 3. Tarefas para a Branch `feat/palex-implementation`

- [ ] **1. Estrutura do Brain (Python):**
  - Criar o arquivo `brain/indicators.py` com as funções puras de Pandas para EMA(9), SMA(21), SMA(200), ATR, e Bollinger Bands.
  - Criar o arquivo `brain/setups.py` que implementará a classe `PalexScorer`. Ela receberá o DataFrame de velas atualizado e retornará a matriz booleana com o gatilho ativo (`is_91_buy`, `is_94_sell`, etc).
  - Criar `brain/main.py` que inicia um loop lendo `sys.stdin` buscando as novas velas enviadas pelo Go, processa na classe `PalexScorer`, e cospe o JSON de decisão no `sys.stdout`.

- [ ] **2. Estrutura do Maestro (Golang):**
  - Modificar o `main.go` para ser o orquestrador (atualmente é um monólito).
  - Criar o pacote `worker` em Go que executa `exec.Command("python", "brain/main.py")` e cria canais para os pipes de `Stdin` e `Stdout`.
  - Implementar a rotina de envio de velas do MT5 para o `Stdin` do Python em JSON.
  - Implementar a goroutine de escuta do `Stdout` do Python para parsear a resposta (Buy/Sell) e despachar a ordem na API do MT5.
  - Implementar a lógica de Heartbeat: Se o Python não processar o sinal em até X milissegundos, o Go *mata* o processo e reinicia (Fault Tolerance).

- [ ] **3. Integração e Testes (Ambiente Local):**
  - Escrever o arquivo `run.bat` que levanta o Golang no Windows.
  - Realizar um backtest seco injetando JSON simulado de velas no `main.py` (mock) e certificando que o scoring de FFFD e 9.1 apita corretamente no log.
