<p align="center">
  <img src="https://upload.wikimedia.org/wikipedia/commons/c/c2/MetaTrader_5_logo.png" width="120" alt="MT5 Logo">
</p>

<h1 align="center">MT5Bot Maestro ⚡</h1>

<p align="center">
  <strong>Lucros consistentes. Zero emoção. Risco Cravado em 1%.</strong><br>
  <em>Measured, disciplined execution — performance varies with market conditions.</em>
</p>

---

> [!IMPORTANT]
> **Filosofia de Proteção ao Capital**
> O robô não busca ganhos desmedidos na sorte. O objetivo central é **proteger o patrimônio, perder cada vez menos**, e só autorizar ordens quando o risco for estritamente controlado e proporcional ao saldo da sua conta.

O **MT5Bot Maestro** é um robô de trading automatizado de nível institucional para MetaTrader 5. Baseado nos renomados setups da família 9.x e do Ponto Contínuo, ele opera com **disciplina absoluta** enquanto você foca no que importa. 

Totalmente reconstruído em uma moderna arquitetura Híbrida (Golang + Python), o bot agora é **100% Stateless**, garantindo segurança absoluta contra quedas de energia e travamentos.

---

## 🌟 O Que Torna o MT5Bot Único?

### 🛡️ Disaster Recovery Institucional (Arquitetura Stateless)
Esqueça robôs amadores que quebram a sua conta se a energia acabar. O MT5Bot lê a tela do servidor da B3/Corretora em tempo real.
- **Acabou a energia?** Sem pânico. Seu Trade está protegido por um **Hard Stop Loss** cravado na bolsa.
- **O PC Reiniciou?** Ao religar, o bot mapeia os trades abertos e reassume o controle perfeitamente de onde parou.

### 🧮 Position Sizer Dinâmico (Risco Fixo de 1%)
Em vez de operar lotes fixos arbitrários, o robô calcula o lote exato baseado no saldo da sua conta, garantindo que o seu Stop Loss financeiro **jamais ultrapasse 1% do seu capital**. 

### 🚀 Maestro CLI (Terminal Interativo)
Assuma o controle no estilo hacker. Um terminal inspirado nas melhores ferramentas de IAs do mundo (como Claude Code e OpenCode) permite que você adicione ou pare ativos dinamicamente sem precisar desligar o sistema!

---

## ⚡ Comece em Minutos

### Pré-requisitos
- **Windows 10/11** (Exigência do MetaTrader 5)
- **Python 3.10+**
- **Go 1.20+**
- MetaTrader 5 instalado e logado na sua conta (Demo ou Real).

### Instalação & Execução

1. Baixe o repositório e acesse a pasta raiz.
2. Instale as dependências do Python:
   ```bash
   pip install .
   ```
3. Inicie o Maestro Go (Terminal Interativo):
   ```bash
   run.bat
   ```

O terminal do Maestro abrirá com nossa identidade visual laranja. Digite `/help` e comece a operar!

---

## 🕹️ Dominando a CLI (Comandos)

No prompt interativo `mt5bot ❯`, você pode orquestrar o mercado em tempo real:

| Comando | O que faz | Exemplo |
|---------|-----------|---------|
| `/add <ativo> [timeframe]` | Spawna uma thread Python rodando 100% focada no ativo escolhido. | `/add WIN M5` |
| `/stop <ativo>` | Encerra as buscas de trades daquele ativo imediatamente. | `/stop WIN` |
| `/list` | Mostra todos os robôs operando simultaneamente em background. | `/list` |
| `/report` | Gera o relatório de performance no terminal (Ganhos vs Perdas). | `/report` |
| `/dashboard` | Abre o dashboard visual completo em seu navegador web. | `/dashboard` |

---

## 🛑 Comandos de Saída (Shutdown Seguro)

Quer fechar o bot para ir dormir, mas está com posições abertas? Não tem problema. Escolha o seu modo de saída:

- **`/quit` (Padrão - "Modo Sleep")**: Fecha o PC local. Suas posições abertas continuam rolando na Bolsa protegidas pelo Stop Loss. Religue amanhã e ele reassume.
- **`/quit cancel-open`**: Cancela armadilhas (ordens Stop pendentes) para não ativar na sua ausência, mas mantém as posições que já estão no jogo.
- **`/quit wait-flat`**: O bot para de procurar novas oportunidades, e só desliga seu PC/terminal quando os trades atuais fecharem sozinhos no alvo.
- **`/quit close-all` (Panic Button)**: Botão de emergência. Liquida imediatamente TODAS as suas posições a preço de mercado e encerra o sistema.

---

## 🧠 Setups Embutidos (DNA Estratégico)

O bot conta com o motor de varredura mais preciso do mercado, procurando ativamente pelas seguintes oportunidades táticas:

- **Setup de Abertura (GAP)**: Fareja gaps de fuga no início do pregão (ex: HK50) e atira na direção institucional logo nos primeiros candles.
- **Setup 9.1 (Larry Williams)**: Identifica a agressão primária e a virada da MME9, entrando no início das tendências.
- **Setup 9.2 & 9.3**: Pega o *Pullback* perfeito. Compra o recuo técnico nas médias móveis para surfar a continuação do movimento.
- **Ponto Contínuo (PC)**: Detecta o toque milimétrico na poderosa Média Móvel de 21 períodos (MMA21) para entradas cirúrgicas a favor da tendência macro.
- **Fechou Fora, Fechou Dentro (FFFD)**: Rastreador de Bandas de Bollinger. Identifica a exaustão de um movimento e caça reversões rápidas de retorno à média.

**Filtros Protetores**: Todo setup passa por auditoria antes da ordem. O bot avalia o distanciamento da Média de 200 (macro), a força relativa (IFR) e aborta entradas com Spread abusivo.

**Motor de Decisão (`brain/scoring.py`)**: quando vários setups disparam no mesmo ativo, o cérebro pontua cada um (`calcular_score`), aplica o gate de RRR mínimo (`MIN_RISK_REWARD`) e executa **apenas o 1º colocado**. Dois tipos de sinal alimentam a nota:

- **Vetos (anulam o setup)**: preço contra a MM50 (`mm50_favoravel`), preço esticado além de `VWAP_MAX_DEVIATION_ATR` (desvio da VWAP diária), e **filtro MTF** (`mtf_favoravel`) — quando o time frame superior nega a tendência do side, o setup é descartado e o 2º colocado assume automaticamente.
- **Bônus (aumentam a nota)**: IFR9 saindo da zona de exaustão (sobrevenda/sobrecompra) e toque milimétrico na VWAP (≤0.5 ATR).

**Alvo Top-Down por Fibonacci**: setups sem alvo próprio recebem extensão 1.0x/1.618x da amplitude do swing (`swing_levels` + `fib_extension_targets`), dando a todos os sinais o mesmo rigor de saída.

---

## 🕹️ Gestão de Posição (condução do trade)

O bot não joga a posição solta depois da entrada — ela é conduzida barra a barra:

- **Saída Parcial**: lucro de 1x ATR fecha 50% do volume (`PARTIAL_EXIT_TARGET`/`PARTIAL_EXIT_PERCENT`).
- **Breakeven**: com 1x ATR a favor, o SL sobe/desce para o preço de entrada (`ENABLE_BREAKEVEN`).
- **Trailing Stop dinâmico** (`TRAILING_ENABLED`, novo): depois do breakeven, o SL **cola no mercado barra a barra**:
  - `TRAILING_MODE = "candle"` (padrão): BUY segue a mínima do penúltimo candle; SELL a máxima.
  - `"ema9"` / `"mm21"`: cola o SL na EMA9 ou SMA21.
  - Se o preço **perder a média de referência**, o restante é liquidado a mercado.
- **Saída Final**: EMA9 virando contra a posição aperta o SL para a extremidade do candle.

Toda a lógica de trailing vive em `brain/trailing.py` (pura, testável) e é orquestrada pelo `execution_manager`.

---

## 🤝 Modo Assistência: Posições Externas (Entrada Manual)

O bot **não se limita às ordens que ele mesmo abre**. Se você abrir uma posição manualmente no MT5 (na mão, seguindo seu próprio radar), o Maestro **detecta e adota essa posição** automaticamente, passando a guiá-la com a mesma disciplina:

- **Registra** a posição no relatório de performance como setup `MANUAL` (você vê o resultado no `/report` e no dashboard).
- **Guia o stop**: aplica Breakeven a 1x ATR e trailing dinâmico pela EMA9 (move o stop para a mín/máx do candle quando a tendência vira contra).
- **Guia o alvo**: aplica a saída parcial de 50% ao atingir 1x ATR de lucro.
- **Reconciliação automática**: se você fechar a posição na mão (ou o stop fechar), o bot detecta no próximo ciclo, registra o resultado correto e mantém o relatório 100% sincronizado.

### Como usar

1. Abra sua posição manualmente no MT5 (qualquer ativo que o Maestro esteja monitorando com `/add`).
2. Nada mais a fazer — no próximo ciclo (padrão: 5s) o bot adota e começa a guiar.
3. Acompanhe em `/report` ou `/dashboard`.

### Configuração (`config.py`)

| Parâmetro | Padrão | Efeito |
|-----------|--------|--------|
| `MANAGE_EXTERNAL_POSITIONS` | `True` | `False` faz o bot ignorar posições manuais (não mexe no stop, não registra). |
| `EXTERNAL_POSITION_SETUP_NAME` | `"MANUAL"` | Nome exibido no relatório para essas operações. |

> [!NOTE]
> A assistência é aplicada por ativo monitorado. Adicione o ativo com `/add <ativo> <timeframe>` para que a posição manual dele seja adotada.

---

## ⚙️ Arquitetura por debaixo dos panos

A nossa revolução Híbrida:
- **Maestro (Golang)**: Cuida da escalabilidade, CLI não bloqueante, logs assíncronos e estabilidade multi-thread.
- **Cérebro (Python)**: Processa tensores vetoriais pesados com Pandas/Numpy e cuida da matemática financeira se comunicando com o MT5 via C++ bindings.

## 🤝 Open Source e Inteligência Artificial

> [!TIP]
> **Para IAs e desenvolvedores que estudam o projeto:** o repositório mantém uma **memória permanente RAG** (`memoria/`) com os livros-fonte, arquitetura, e decisões técnicas. Antes de programar qualquer coisa, leia o arquivo [`AGENTS.md`](AGENTS.md).

---
<p align="center">
Feito com ☕ e Disciplina. <br>
Licença MIT — Use, estude, modifique e lucre.
</p>