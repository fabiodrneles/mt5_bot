<div align="center">
  <img src="docs/assets/banner.jpg" alt="MT5Bot Maestro Banner" width="100%">
</div>

<br>

<div align="center">
  <strong>🌍 Read in:</strong> <strong>Português</strong> | <a href="README.en.md">English</a>
</div>

<br>

<div align="center">
  <strong>Plataforma Quantitativa de Trading Algorítmico com Filtro Preditivo de Machine Learning</strong><br>
  <em>Arquitetura híbrida institucional focada na mitigação extrema de risco e precisão matemática.</em>
</div>

<br>

<div align="center">
  <img src="https://img.shields.io/badge/Language-Go_%7C_Python-black?style=for-the-badge&logo=go&logoColor=FF7300" alt="Go/Python">
  <img src="https://img.shields.io/badge/AI_Engine-XGBoost-black?style=for-the-badge&logo=xgboost&logoColor=FF7300" alt="XGBoost">
  <img src="https://img.shields.io/badge/Platform-MetaTrader_5-black?style=for-the-badge&logo=metatrader&logoColor=FF7300" alt="MT5">
  <img src="https://img.shields.io/badge/License-MIT-black?style=for-the-badge&logoColor=FF7300" alt="MIT">
</div>

---

## ⬛ A Borda Competitiva (The Edge)

Robôs MQL5 de prateleira falham porque são otimizados para um mercado que já não existe mais (overfitting em backtests ilusórios). 

O **MT5Bot Maestro** adota a filosofia de um *Hedge Fund Quantitativo*: o objetivo primário não é encontrar o "setup mágico", mas aplicar uma **gestão de risco brutal**. 
O tamanho da mão nunca excede 1% do saldo da conta (`Dynamic Risk-Sizer`) e a exposição diária tem trava matemática rígida (`Max Daily Loss`). **Isso significa que o seu capital sobrevive intacto aos piores crashes e "cisnes negros" do mercado.**

---

## 🟧 Arquitetura de Ponta: Maestro (Go) + Cérebro (Python)

Ambientes nativos MQL5 são obsoletos para Inteligência Artificial e Data Science. O **MT5Bot Maestro** foi reconstruído em uma arquitetura híbrida revolucionária:

* **Maestro (Golang)**: O núcleo de orquestração. Construído em Go, ele roda no terminal com uma *CLI TUI (Text User Interface)* de baixa latência. Ele gerencia o ciclo de vida dos workers em threads paralelas e fornece *Crash-Loop Protection* (Stateless Recovery). Se o sistema cair ou o PC desligar, ele remonta as posições a partir do servidor da corretora em menos de 5 segundos.
* **Cérebro (Python 3.10+)**: Onde o processamento pesado ocorre. As bibliotecas de Data Science (Pandas/NumPy) fatiam a microestrutura de milhares de velas, calculam cruzamentos de VWAP, geram Scoring dinâmico para cada ativo e conversam diretamente com o motor de Machine Learning.

---

## ⬛ Filtro Preditivo (Machine Learning XGBoost)

A estratégia base pode lhe dar as regras, mas é a **Inteligência Artificial** que lhe dá a visão do futuro. Implementamos o que chamamos de **Data Flywheel**.

Quando um setup matemático apita (ex: Setup 9.1), a ordem **não** é enviada imediatamente. O extrator captura as 24 variáveis instantâneas daquele segundo exato (Distância da MM200, Força do ADX, Volatilidade do ATR, Aceleração do Preço).
Essa matriz passa pelo nosso modelo **XGBoost (Decision Trees)**, que responde a uma única pergunta de forma binária e estatística:

> *"Historicamente, com o mercado respirando exatamente desta forma, qual a probabilidade deste trade retornar lucro?"*

Se a probabilidade inferida for menor que `ML_MIN_WIN_PROB` (ex: 40%), **o bot veta a operação**. Você para de sangrar dinheiro em dias de consolidação extrema. 
*(Para os engenheiros de MLOps: O sistema conta com Pipeline de Treinamento Contínuo no Colab/GitHub Actions via arquivos de tracking virtual - Phantom Orders).*

---

## 🟧 O Cartão de Visitas: Canivete Suíço (CLI)

Tempo e processamento são cruciais. Criamos um orquestrador central CLI (`bot.bat`) projetado para que **Engenheiros Sêniores** ou **Inteligências Artificiais** façam a telemetria do sistema de forma cirúrgica e economizando tokens preciosos.

Basta abrir o terminal e digitar:

```powershell
bot.bat diagnose    # Health Check completo do core e ping de conectividade MT5
bot.bat hardware    # Telemetria profunda de CPU/RAM e prevenção de memory-leaks
bot.bat market      # Scanning de Volatilidade, Spread dinâmico e Margens do mercado
bot.bat config      # Auditoria de Risco % ativo e algoritmos em execução
bot.bat positions   # Relatório de Exposição (Ordens Reais e Phantom Trades)
bot.bat performance # Relatório executivo de PnL (Lucro Líquido) e WinRate dos últimos 7 dias
bot.bat tail        # Extração cirúrgica do topo de log, dispensando cat massivo
bot.bat panic       # 🚨 BOTÃO DO PÂNICO: Kill-Switch que liquida toda exposição a mercado
bot.bat ask "X"     # Consulta vetorial na memória RAG do repositório (ex: bot ask "regras do 9.1")
bot.bat train       # Gatilho de retreinamento do motor XGBoost
bot.bat backtest    # Dispara o Simulador Financeiro Local (ex: bot backtest HK50)
bot.bat test        # Pipeline de Testes Unitários e Mock do Motor
python main.py      # 🔥 INICIA O ROBÔ EM MODO PRODUÇÃO / LIVE TRADING
```

---

## ⬛ Dicionário Estratégico (O Motor de Decisão)

O Maestro carrega **11 Estratégias Quantitativas** que podem operar simultaneamente. Se duas estratégias armarem no mesmo ativo, o módulo `scoring.py` roda uma matriz de probabilidade, escolhe o vencedor e aborta o perdedor.

| Algoritmo | Comportamento e Dinâmica do Mercado |
| :--- | :--- |
| **Família 9.1 ao 9.4** | Captura de micro-tendências e retrações em MME9. Ideal para volatilidade direcional. |
| **Ponto Contínuo (PC)** | Sniper algorítmico. Entradas milimétricas na média de 21 durante a tendência vigente. |
| **Gaps de Fuga** | Roteamento exclusivo p/ Índices (HK50). Explora a ineficiência e o pânico institucional na abertura asiática. |
| **Setup Russo (Mean Reversion)** | Reversão à média utilizando desvios de Bandas de Bollinger e IFR. Lucra com exaustão extrema. |
| **DiNapoli / SAR / IFR2** | Roteamento auxiliar para mercados altamente lateralizados e Forex. |

### 🛡️ Escudos Macro-Econômicos
- **Filtro MM50 / MM200**: Ordens contra a tendência macro são sumariamente ignoradas.
- **Microestrutura de Spread**: Entradas com custo transacional abusivo (slippage perigoso) são abortadas antes de tocarem a corretora.
- **Trailing Stop Adaptativo**: Uma vez dentro do trade, o bot o defende até a morte. Atingiu 1x Risco? O Stop vai pro `Breakeven` e você não perde mais 1 centavo. Daí em diante, ele espreme o lucro candle a candle até o fluxo reverter.

---

## 🟧 Subindo o Projeto (Instalação Clean)

Um ambiente robusto não deve exigir configurações dolorosas. Para colocar essa infraestrutura para rodar, basta ter o **Windows 10/11** (o Terminal MT5 é exclusivo Windows) e **Python 3.10+**.

```bash
# 1. Clone a infraestrutura
git clone https://github.com/fabiodrneles/mt5_bot.git
cd mt5_bot

# 2. Instale as dependências (Core de Dados + MetaQuotes Driver)
pip install -e .

# 3. Mantenha seu Terminal MT5 aberto, logado na corretora
# 4. Inicie o Console Interativo Maestro
python main.py
```
> O painel *Text UI* surgirá na sua tela. Digite `/help` para os manuais internos ou `/add WIN M5` para ligar as turbinas do mini-índice agora.

---

## ⬛ Arquitetura Guiada por IA (Memória Permanente RAG)

Este software foi esculpido em parceria com agentes avançados de Inteligência Artificial para garantir código blindado, *Design Patterns* elegantes e arquitetura de alto calibre.

> [!CAUTION]
> **Aviso para Inteligências Artificiais:** Se você (uma IA) acabou de ser acionada para desenvolver este repositório, suspenda suas ações imediatas e leia o arquivo mestre `AGENTS.md`. 
> Este repositório é dotado de uma **Memória Permanente RAG (BM25)** — dispensando *embeddings* caros e armazenando todo o contexto técnico, decisões estatísticas e lógica central do fundo. Leia os mandamentos em `AGENTS.md` antes de propor qualquer mudança ao sistema nervoso do bot.

---
<div align="center">
  <em>Não corra atrás do preço. Deixe a matemática cuidar do resto.</em>
</div>