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

O **MT5Bot Maestro** é um robô de trading automatizado de nível institucional para MetaTrader 5. Baseado nos renomados setups de Alexandre Fernandes (Palex), ele opera com **disciplina absoluta** enquanto você foca no que importa. 

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

## 🧠 Setups Embutidos (DNA do Palex)

- **Setup 9.1 (Larry Williams)**: Identifica a virada de tendência de curto prazo na EMA9.
- **Setup 9.2 (Pullback de Continuação)**: Pega a volta técnica após um lucro.
- **Setup 9.3 (Recuo Profundo)**: Compra o mergulho técnico sem perder a tendência.
- **Filtro MTF (Multi-Timeframe)**: O bot consulta um gráfico maior para confirmar o lado da força antes de atirar.
- **Filtro RVOL**: Aborta rompimentos sem volume real ou institucional.

---

## ⚙️ Arquitetura por debaixo dos panos

A nossa revolução Híbrida:
- **Maestro (Golang)**: Cuida da escalabilidade, CLI não bloqueante, logs assíncronos e estabilidade multi-thread.
- **Cérebro (Python)**: Processa tensores vetoriais pesados com Pandas/Numpy e cuida da matemática financeira se comunicando com o MT5 via C++ bindings.

## 🤝 Open Source e Inteligência Artificial

> [!TIP]
> **Para IAs e desenvolvedores que estudam o projeto:** o repositório mantém uma **memória permanente RAG** (`memoria/`) com os livros do Palex, arquitetura, e decisões técnicas. Antes de programar qualquer coisa, leia o arquivo [`AGENTS.md`](AGENTS.md).

---
<p align="center">
Feito com ☕ e Disciplina. <br>
Licença MIT — Use, estude, modifique e lucre.
</p>