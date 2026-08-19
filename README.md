<div align="center">
  <img src="docs/assets/banner.jpg" alt="MT5Bot Maestro Banner" width="100%">
</div>

<br>

<div align="center">
  <strong>Plataforma Quantitativa de Trading Algorítmico com Filtro Preditivo de Machine Learning</strong><br>
  <em>Arquitetura híbrida (Go + Python) focada na preservação de capital e precisão sniper.</em>
</div>

<br>

<div align="center">
  <img src="https://img.shields.io/badge/Language-Go_%7C_Python-black?style=for-the-badge&logo=go&logoColor=FF7300" alt="Go/Python">
  <img src="https://img.shields.io/badge/AI_Engine-XGBoost-black?style=for-the-badge&logo=xgboost&logoColor=FF7300" alt="XGBoost">
  <img src="https://img.shields.io/badge/Platform-MetaTrader_5-black?style=for-the-badge&logo=metatrader&logoColor=FF7300" alt="MT5">
  <img src="https://img.shields.io/badge/License-MIT-black?style=for-the-badge&logoColor=FF7300" alt="MIT">
</div>

---

## ⬛ A Filosofia da Borda Competitiva (The Edge)
O mercado financeiro não perdoa apostadores. O **MT5Bot Maestro** não foi construído para achar o *setup perfeito*, mas para **gerenciar o risco matemático de forma brutal**. Ele opera como um fundo de hedge de nicho: o tamanho da mão nunca excede 1% do saldo total (`Risk-Sizer Dinâmico`), as reversões têm trava diária de capital (`Max Daily Loss`) e nenhuma ordem é despachada sem aprovação conjunta do motor estatístico e do filtro de Machine Learning.

---

## 🟧 Arquitetura: Maestro (Go) + Cérebro (Python)

Robôs MQL5 nativos são limitados e obsoletos para manipulação avançada de matrizes e Inteligência Artificial. O **MT5Bot Maestro** utiliza uma arquitetura híbrida revolucionária:

* **Maestro (Golang)**: O núcleo orquestrador. Roda no terminal como uma *CLI TUI (Text User Interface)* estilo cyberpunk. É responsável por abrir threads paralelas (Workers), garantir resiliência contra *Crash-Loops*, e exibir um Dashboard multithread sem bloquear as decisões de preço.
* **Cérebro (Python 3.10+)**: Onde a mágica acontece. A lib Pandas analisa a microestrutura de milhares de candles em frações de segundos. Avalia distâncias de VWAP, gera pontuação (Scoring) de cruzamento de médias, calcula o ATR para adaptar alvos, e chama os algoritmos de **Machine Learning**.

---

## ⬛ O Filtro de Machine Learning (XGBoost)

Robôs comuns sofrem em backtests porque o mercado muda. Nós usamos um sistema preditivo chamado **Data Flywheel (Harvester)**.

Quando a matemática pura apita uma compra (ex: Setup 9.1), o bot tira uma "foto" da microestrutura atual do preço (ADX, Z-Score, Distância da MM200). Antes de enviar a ordem ao MetaTrader 5, essa matriz passa pelo modelo **XGBoost (Decision Trees)** que responde a uma única pergunta: 
> *"Com base em centenas de execuções parecidas nos últimos meses, qual a probabilidade matemática deste trade dar lucro hoje?"*

Se a probabilidade for menor que `ML_MIN_WIN_PROB` (ex: 40%), **o trade é rejeitado**.
Aos finais de semana, você roda o comando de exportação e joga a nova base de conhecimento na nuvem (GitHub Actions / Colab) para retreinar e evoluir o modelo.

---

## 🟧 Cartão de Visitas: O Canivete Suíço (CLI)

O projeto acompanha uma ferramenta avançada de linha de comando (`bot.bat`). 
Projetada para que **IAs** e **Engenheiros** inspecionem a saúde do robô e do mercado com zero esforço e economizando tokens de processamento:

```powershell
bot.bat diagnose    # Traz erros críticos e faz o Health Check do MT5
bot.bat hardware    # Inspeciona uso de RAM e mitigação de memory-leaks
bot.bat market      # Inspeciona Spread, Margem e Volatilidade instantânea
bot.bat config      # Mostra o Risco % e os algoritmos atualmente ligados
bot.bat positions   # Lista posições abertas reais e "fantasmas" (Paper Trading)
bot.bat performance # Relatório de PnL (Lucro Líquido) e WinRate dos últimos 7 dias
bot.bat tail        # Imprime cirurgicamente os últimos eventos do bot.log
bot.bat panic       # 🚨 BOTAO DO PANICO: Liquida todas as ordens a mercado!
bot.bat ask "X"     # Consulta a memória permanente RAG do projeto (ex: bot ask "regras")
bot.bat train       # Inicia o retreinamento do XGBoost localmente
bot.bat backtest    # Roda simulações financeiras completas (ex: bot backtest HK50)
bot.bat test        # Roda os testes unitários do motor core
python main.py      # 🔥 INICIA O ROBÔ EM AMBIENTE DE PRODUÇÃO
```

---

## ⬛ Dicionário de Setups e Filtros

O Bot contém **11 estratégias matemáticas embutidas** que podem operar simultaneamente (ou isoladas por ativo). Quando duas estratégias entram em conflito, o módulo `scoring.py` escolhe a de maior probabilidade.

| Família de Setups | Descrição da Estratégia |
| :--- | :--- |
| **9.1, 9.2, 9.3, 9.4** | Captura de reversões rápidas (Larry Williams) e continuação contra a EMA9. |
| **Ponto Contínuo (PC)** | Entradas milimétricas a favor da tendência com toque na média de 21. |
| **Gaps de Fuga** | Exclusivo p/ HK50. Surfando o pânico/euforia institucional na abertura do mercado Asiático. |
| **Russo (Mean Reversion)** | Bandas de Bollinger (FFFD) + IFR para capturar sobrecompra extrema e exaustão. |
| **DiNapoli / SAR / IFR2** | Setup auxiliar de micro-tendências para mercados laterais (Forex). |

### 🛡️ Escudo de Defesa (Filtros Macro)
- **Bloqueio MM50 / MM200**: O bot nunca compra debaixo d'água contra a tendência majoritária.
- **Proteção Institucional (Spread)**: Rejeita ordens em fusos horários de baixíssima liquidez (ex: HK50 fora da janela asiática).
- **Trailing Stop Adaptativo**: O bot defende a posição "barra a barra". Ao atingir 1x o risco, ele trava no zero (Breakeven) e depois persegue o lucro usando a Mínima do Candle ou a Média de 9 até a exaustão.

---

## 🟧 Deploy e Instalação

Ambiente mínimo exigido para rodar a arquitetura completa:
- **Windows 10/11** (O Terminal MT5 é exclusivo Windows)
- **MetaTrader 5** instalado e logado na corretora.
- **Python 3.10+**
- Computador simples (Core i3 + 4GB RAM) é capaz de orquestrar a versão leve.

```bash
# 1. Clone a plataforma
git clone https://github.com/fabiodrneles/mt5_bot.git
cd mt5_bot

# 2. Instale as dependências de Análise de Dados e Conexão MetaQuotes
pip install -e .

# 3. Abra o seu MetaTrader 5 e deixe-o rodando.
# 4. Inicie o painel de controle!
python main.py
```
> Após rodar, o painel interativo surgirá na sua tela. Digite `/help` para listar os comandos interativos ou `/add WIN M5` para ligar um robô no mini-índice!

---

## ⬛ Open Source & Inteligência Artificial (RAG)

Este projeto foi forjado utilizando ferramentas massivas de Inteligência Artificial para aprimorar sua arquitetura. 
Se você é uma IA encarregada de estender este projeto, pare o que está fazendo e leia a base de regras `AGENTS.md`. 
O repositório contém uma **Memória Permanente RAG (Retrieval-Augmented Generation) BM25**, que dispensa embeddings na nuvem e guarda o estado, decisões e lógica deste software. Consulte a memória antes de alterar arquiteturas vitais.

---
<div align="center">
  <em>Desenvolvido com disciplina cirúrgica e código limpo. Proteja seu capital.</em>
</div>