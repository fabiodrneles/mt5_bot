<div align="center">
  <img src="docs/assets/banner.jpg" alt="MT5Bot Maestro" width="100%">
</div>

<div align="center">

**🌍 Idioma:** **Português** | [English](README.en.md)

# MT5Bot Maestro

**Robô de trading algorítmico para MetaTrader 5, em Python e Go, feito para contas pequenas.**
Faz gestão de risco rígida, usa estratégias validadas fora da amostra e respeita a sua margem.

![Versão](https://img.shields.io/badge/vers%C3%A3o-3.1.0-FF7300?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![Go](https://img.shields.io/badge/Go-Maestro-00ADD8?style=flat-square&logo=go&logoColor=white)
![MetaTrader 5](https://img.shields.io/badge/MetaTrader-5-1F6FEB?style=flat-square)
![Testes](https://img.shields.io/badge/testes-251%20passando-2EA043?style=flat-square)
![Licença](https://img.shields.io/badge/licen%C3%A7a-MIT-555?style=flat-square)

</div>

> [!WARNING]
> **Trading envolve risco real de perda.** Resultados de backtest não garantem resultados futuros. Teste primeiro em **conta demo**. Na conta real, use só dinheiro que você aceita perder. Este software não é recomendação de investimento.

---

## 📑 Sumário

1. [O que é](#-o-que-é)
1. [Propósito acadêmico](#-propósito-acadêmico)
2. [Requisitos](#-requisitos)
3. [Instalação](#-instalação)
4. [Primeiros passos: escolha um modo](#-primeiros-passos-escolha-um-modo)
5. [Modo Quant (recomendado)](#-modo-quant-recomendado)
6. [Modo Maestro (interativo)](#-modo-maestro-interativo)
7. [Estratégias](#-estratégias)
8. [Proteção de capital](#️-proteção-de-capital)
9. [Comandos do `bot.bat`](#-comandos-do-botbat)
10. [Configuração](#️-configuração)
11. [Onde ficam os dados e logs](#-onde-ficam-os-dados-e-logs)
12. [Emergência: como parar tudo](#-emergência-como-parar-tudo)
13. [Backtest e pesquisa de estratégias](#-backtest-e-pesquisa-de-estratégias)
14. [Machine Learning (XGBoost)](#-machine-learning-xgboost)
15. [Notificações no Telegram](#-notificações-no-telegram)
16. [Diário de sinais: teste o seu olho](#-diário-de-sinais-teste-o-seu-olho)
17. [Arquitetura](#️-arquitetura)
18. [Solução de problemas](#-solução-de-problemas)
19. [Desenvolvimento](#-desenvolvimento)

---

## 💡 O que é

O MT5Bot conecta no terminal **MetaTrader 5** aberto no seu Windows e opera sozinho. Ele lê os candles fechados, procura sinais, calcula o tamanho da posição e envia as ordens com stop loss.

O projeto tem dois modos de operação:

| Modo | Para quem | O que roda |
|---|---|---|
| **Quant** (`bot.bat quant`) | Contas pequenas que querem **só o que foi validado** | 2 estratégias testadas com custos reais e fora da amostra |
| **Maestro** (`mt5bot.bat`) | Quem quer explorar a família 9.x, o Ponto Contínuo, o Setup Russo e outros | Painel interativo com vários robôs em paralelo |

---

## 🎓 Propósito acadêmico

O MT5Bot é um **projeto de estudo e de portfólio**, não um produto comercial. Ele serve como estudo de caso completo de engenharia de software aplicado a um domínio onde erros têm custo real: um robô que opera dinheiro de verdade numa corretora. Isso obriga a praticar o que costuma ficar só na teoria, como requisitos verificáveis, testes, segurança, observabilidade e processo.

> 📘 **Manual técnico completo:** [`docs/manual/`](docs/manual/README.md). São 14 capítulos e 3 apêndices: fundamentos teóricos de mercado e risco, arquitetura e motores, fórmulas, justificativas de projeto, ameaças à validade, reprodutibilidade e referencial teórico (mais de 75 obras). Também sai em arquivo único em cada release (`MT5Bot-Guia-Tecnico-<versão>.md`).

### O que se estuda aqui

| Área de engenharia de software | Como aparece no projeto | Onde ver |
|---|---|---|
| **Engenharia de requisitos (SDD)** | Specs com requisitos funcionais e não funcionais (FR/NFR) e critérios de aceite Dado/Quando/Então; constituição com princípios verificáveis; decisões registradas (estilo ADR) | [`specs/`](specs/) |
| **Arquitetura de software** | Sistema poliglota: orquestrador em **Go** supervisionando workers em **Python**, com comunicação por JSON via stdin/stdout; arquitetura stateless que reconstrói o estado a partir da corretora | `maestro/`, `interfaces/brain_worker.py` |
| **Confiabilidade e tolerância a falhas** | Watchdog com heartbeat, proteção contra crash loop, recuperação sem estado, stop gravado no servidor da corretora | `maestro/worker.go`, `mt5bot/execution/` |
| **Engenharia de segurança (safety)** | Invariantes de capital (só mexe no que tem o MAGIC do robô), defesa em profundidade (limite de risco, reserva de margem, trava diária), botão de pânico, padrões seguros | `mt5bot/execution/quant_manager.py`, `tools/panic.py`, [constituição](specs/constitution.md) |
| **Testes de software** | Mais de 220 testes automatizados com *test doubles* (MT5 simulado), testes de layout da TUI, teste que importa todos os módulos e **checagem de mutação** dos testes novos | `tests/`, `maestro/*_test.go` |
| **Integração e entrega contínuas** | GitHub Actions em matriz Windows/Ubuntu × Python 3.10/3.13, lint como gate, verificação do pacote instalado e CI local equivalente | `.github/workflows/`, `tools/ci.ps1`, `tools/check_wheel.py` |
| **Gerência de configuração** | Um PR por ticket, Conventional Commits, épicos com sub-issues, Keep a Changelog, SemVer, configuração do usuário separada do código (`config.toml`) | [PRs](https://github.com/fabiodrneles/mt5_bot/pulls?q=is%3Apr), [`CHANGELOG.md`](CHANGELOG.md) |
| **Manutenção e evolução** | Análise de causa raiz (CI vermelho por 2 meses, botão de pânico que não fechava nada, pacote quebrado), refatoração de código legado, redução de dívida técnica | [`specs/ANALYSIS.md`](specs/ANALYSIS.md), PRs #9–#16 |
| **Observabilidade** | Telemetria única alimentando três interfaces, logs na pasta do usuário, diagnóstico por comando | `mt5bot/core/telemetry.py`, `bot.bat diagnose` |
| **Interação humano-computador** | TUI com Bubble Tea, painel colorido no console, dashboard web responsivo, estados vazios que ensinam o próximo passo, internacionalização (pt/en/es) | `maestro/ui.go`, `tools/quant_runner.py`, `interfaces/dashboard.py` |
| **Desempenho sob restrição** | Projeto pensado para um i3 com 4 GB de RAM: cache de candles e de arquivos, biblioteca padrão no lugar de frameworks pesados, RAG lexical (BM25) em vez de embeddings | `tools/quant_runner.py`, `memoria/` |
| **Método científico aplicado (finanças quantitativas)** | Backtest com custos reais, separação dentro × fora da amostra, teste de significância (estatística t), comparação com 300 carteiras aleatórias, registro honesto de quando uma estratégia **não** generaliza | `tools/quant_research/`, [wiki da pesquisa](memoria/wiki/arquitetura/pesquisa-estrategias-lucrativas.md) |
| **Engenharia com IA** | Desenvolvimento assistido por IA com memória permanente consultável (RAG) e um mapa do projeto para agentes, com verificação adversarial do que a IA produz | `memoria/`, [`AGENTS.md`](AGENTS.md) |

### Por que isso é importante

- **Teoria com consequência real.** Um teste que falta ou um gate fraco aqui viram dinheiro perdido. Isso torna concreto por que requisitos, testes e CI existem.
- **Os erros ficam documentados, não escondidos.** A análise registra com evidência os defeitos encontrados (CI vermelho desde agosto, comandos chamando arquivos inexistentes) e mostra como cada um foi corrigido pela causa raiz. Ler essa trajetória ensina mais do que ler um código "perfeito".
- **Honestidade quantitativa.** O projeto mostra o caminho completo de uma hipótese de mercado até uma estratégia operável, incluindo os resultados negativos. É a defesa contra o *overfitting*, o erro mais comum em finanças quantitativas.
- **Processo reprodutível.** Qualquer pessoa pode seguir as specs, os épicos e os PRs para entender por que cada decisão foi tomada. Isso serve de material para disciplinas como Engenharia de Software, Sistemas Distribuídos e Finanças Computacionais.
- **Portfólio verificável.** As afirmações do README são checadas pelo CI e pelos testes, não só descritas.

> Este projeto tem fins educacionais. Nada aqui é recomendação de investimento.

---

## 🧰 Requisitos

- **Windows 10/11.** A biblioteca `MetaTrader5` do Python só existe para Windows.
- **MetaTrader 5** instalado, logado na corretora e **aberto** enquanto o bot roda.
- **Python 3.10+** (testado no 3.13).
- **Go 1.21+**: para compilar o Maestro na primeira vez (o `mt5bot.bat` faz isso sozinho, ou use `bot.bat build`). Os binários prontos ficam nas [Releases](https://github.com/fabiodrneles/mt5_bot/releases).
- O hardware pode ser modesto: o projeto roda em um i3 de 4ª geração com 4 GB de RAM.

---

## 📦 Instalação

### Jeito mais fácil: instalador (Windows 10/11)

1. Baixe o **`MT5Bot-Setup-<versão>.exe`** na página de [Releases](https://github.com/fabiodrneles/mt5_bot/releases/latest). Ao lado dele há o arquivo `SHA256SUMS`, para conferir a integridade do download.
2. Execute. Não é preciso ser administrador, e não é preciso instalar Python, Go nem git: tudo vem embutido.
3. O instalador ainda **não tem assinatura digital**, então o Windows pode mostrar "O Windows protegeu o computador". Clique em **Mais informações → Executar assim mesmo**.
4. No fim da instalação abre o **assistente de configuração** (também em `bot.bat setup`). Ele confere o MT5, mostra se a conta é REAL ou DEMO e quanto cada trade pode perder no seu saldo.
5. Use os atalhos do menu Iniciar: **MT5Bot Quant**, **MT5Bot Maestro**, **MT5Bot Dashboard**, **Assistente de configuração** e **Diagnóstico**.

> 🔒 **Conta REAL só opera depois da sua confirmação.** Até você rodar o assistente e digitar `CONFIRMO`, o robô não abre posições numa conta real (aparece "CONFIRME A CONTA REAL"). Conta DEMO opera direto. A confirmação fica gravada no `config.toml` (`live_confirmed = true`).

Para desinstalar, use "Desinstalar MT5Bot" no menu Iniciar. Seus dados (`%APPDATA%\mt5bot`) só são apagados se você confirmar.

### Para desenvolvedores: pelo código-fonte

```powershell
# 1. Baixe o projeto
git clone https://github.com/fabiodrneles/mt5_bot.git
cd mt5_bot

# 2. Instale as dependências (MetaTrader5, pandas, numpy, pytz, xgboost, pytest)
pip install -e ".[dev]"
pip install -r requirements-ml.txt   # scikit-learn, usado no treino do XGBoost
```

**Prepare o MetaTrader 5:**

1. Faça login na sua conta (demo ou real).
2. Ligue o botão **Algo Trading** na barra de ferramentas. Ele precisa ficar verde.
3. Em *Ferramentas → Opções → Expert Advisors*, marque **Permitir negociação algorítmica**.
4. Na *Observação do Mercado*, deixe visíveis os ativos que você vai operar (ex.: `HK50`, `US500`).

**Confira a conexão:**

```powershell
bot.bat diagnose
```

```
MT5: Conectado | Saldo: $16.26 | Margem Livre: $14.35
Erros nas ultimas 24h (bot.log): 0
```

> Rode todos os comandos **da pasta raiz do projeto**. No PowerShell, use o prefixo `.\` (ex.: `.\bot.bat diagnose`); no `cmd`, `bot.bat diagnose` basta.

---

## 🚀 Primeiros passos: escolha um modo

```
                 Conta pequena ou primeira vez?
                              │
            ┌────────── sim ──┴── não ──────────┐
            ▼                                   ▼
     bot.bat quant                         mt5bot.bat
  (só estratégias validadas)       (painel Maestro: /study, /add)
```

Se nunca rodou o bot, comece com o **Modo Quant em conta demo** e deixe passar algumas semanas antes de ir para a conta real.

---

## 📈 Modo Quant (recomendado)

```powershell
bot.bat quant
```

Ele roda continuamente, com um ciclo a cada 5 segundos, e mostra um **painel ao vivo**. Deixe a janela aberta e pare com **Ctrl+C**:

```
  ◆ MT5BOT  ·  MODO QUANT                                       26/10 22:20:00
 REAL  Conta 50352457   Saldo $16.26   Patrimônio $16.38   Margem livre $14.20
        Hoje +$0.12   Placar quant 3 trades (2 no lucro)  +$0.35

 ▍ROTAS
   ATIVO            ESTADO                       PRÓX. CANDLE     RISCO / LIMITE
   HK50 H4 PULLB    🟢 EM POSIÇÃO (PULLB BUY)     em 1h 05m        ✓ $0.21 / $0.33
   US500 D1 RSI2MR  ⏳ AGUARDANDO MERCADO         mercado fechado  ✓ $1.62 / $1.95

 ▍POSIÇÕES DO ROBÔ
   HK50 ▲ BUY 0.01 @ 23050.00  SL 22850.00  TP 23450.00   +$0.12

 ▍EVENTOS
   26/10 22:15  [HK50] PULLB BUY @ 23050.0 SL=22850.00 TP=23450.0 lote=0.01
────────────────────────────────────────────────────────────────────────────────
  Ctrl+C  parar    .\bot.bat panic  emergência   log: %APPDATA%\mt5bot\logs
```

- **Risco / limite:** ✓ quando o trade cabe no limite; 🔒 quando está travado para proteger a margem, mostrando o porquê.
- **Próx. candle:** quanto falta para o candle fechar, pelo relógio do servidor. Indica "mercado fechado" no fim de semana.
- **Placar quant:** só os trades das rotas quant, com o lucro real (comissão e swap incluídos).
- `python tools\quant_runner.py --plain` mostra só o log, sem painel (útil para redirecionar para um arquivo). `--once` roda um ciclo e sai.
- O painel é leve: as 400 velas só são baixadas quando um candle fecha.

### As estratégias do Modo Quant

As duas saíram de uma pesquisa com **3.150 combinações** (15 ativos × 4 timeframes × 4 famílias). A pesquisa usou o **spread real de cada candle**, a comissão da corretora e o swap. Os parâmetros foram escolhidos só com os 60% iniciais do histórico, e o resultado abaixo vem dos 40% finais, que o otimizador nunca viu.

| Rota | Regra | Histórico (lote 0.01) | Risco por trade |
|---|---|---|---|
| **HK50 H4 — PULLB** | Tendência de alta (EMA20 > EMA50 e preço acima da SMA200). O candle recua até a EMA20 e fecha acima dela, e o bot compra. A venda é espelhada. **SL 1 ATR, TP 2 ATR.** | 277 trades em 4,8 anos · fator de lucro 1,24 · **+$9,96** · pior queda $4,30 | ~$0,21 |
| **US500 D1 — RSI2MR** | IFR(2) < 5 com o preço acima da SMA200: compra a queda forte (venda espelhada). **SL 2 ATR.** Sai quando o fechamento cruza a SMA5 ou depois de 15 dias. | 54 trades em 9,5 anos · fator de lucro 2,40 · **+$13,19** · pior queda $3,04 | ~$1,63 |

**Como ele opera:**
- A entrada é **a mercado, logo após o fechamento** do candle de sinal, como no backtest. Se passar de 10% da duração do candle, o sinal é descartado.
- Usa sempre o **lote mínimo**, com **SL e TP gravados no MT5**: a proteção continua valendo mesmo que o PC desligue.
- Não usa scoring, XGBoost, trailing nem breakeven, porque nada disso fez parte da validação.

**O quanto confiar em cada rota** (testes de sorte em `tools/quant_research/robustness.py`):

| | HK50 H4 PULLB | US500 D1 RSI2MR |
|---|---|---|
| Estatística t (≥ 2 é forte) | 1,65: fraca | **2,57: boa** |
| A mesma regra funciona em outros índices? | Não (8 de 9 perdem) | **Sim** (6 de 8 lucram) |
| Contra 300 carteiras de entradas aleatórias no HK50 | Vence as 300 | — |

O US500 tem a evidência mais forte: é o efeito RSI2 de Connors, documentado há décadas. O HK50 tem um sinal que agrega valor *no HK50*, mas deve ser tratado como experimento ao vivo.

**Quer liberar o US500 com saldo pequeno?** Dê à rota um limite próprio em `config.py`, por exemplo `"US500": {..., "max_risk_pct": 12.0}`. Com $16, cada stop custa ~$1,63 (10% da conta). A pior queda histórica foi de $3,04, com cerca de 6 trades por ano. Nesta instalação o US500 já vem **liberado com 12%**. Para voltar a travá-lo, apague o `"max_risk_pct"` da rota.

**Revisão de outubro de 2026 (pesquisa ampla, guia cap. 14).** Com o simulador corrigido (spread do rollover, abertura de pregão e swap triplo), o **US500 RSI2 se manteve**: +$9,73 fora da amostra, t 2,48 em 10 anos. O **HK50 PULLB encolheu** para cerca de +$3 fora da amostra (t ≈ 0,7), porque parte do lucro antigo vinha de custos subestimados. A mesma regra RSI2, **sem mudar nenhum parâmetro**, também lucrou no **US100** (55 trades, t 2,10) e no US30, ou seja, o efeito é consistente nos índices americanos.

**Rota USDJPY em estudo (📘).** O único sobrevivente da varredura de calendário (cap. 14 §14.6): comprar USDJPY na segunda às 01h do servidor e sair 1 hora depois. Roda virtualmente até acumular pelo menos 30 segundas novas; só então se decide se vira rota real.

**Rota US100 em estudo (📘).** O US100 RSI2 está configurado em **modo estudo**: o robô calcula os sinais, as entradas e as saídas exatamente como faria ao vivo, mas **não envia nenhuma ordem**. As operações virtuais ficam em `%APPDATA%\mt5bot\quant_study.json`. Motivo: cada stop do US100 custa ~$5,20 no lote mínimo (um terço de $16). Com saldo de ~$52 (10% por stop), dá para operar de verdade com `[routes.US100]` e `mode = "live"` no `config.toml`.

**Expectativa honesta:** é lucro de **centavos por trade**. No HK50, a média histórica é de +$0,036 por operação, cerca de 13% ao ano sobre $16, com quedas de até ~$4 no caminho. Houve anos negativos (2024: −$1,48). Só dá para tirar conclusão depois de dezenas de trades reais.

### Travas de margem do Modo Quant

| Trava | Regra | Efeito com saldo de $16 |
|---|---|---|
| Risco por trade | Perda no SL ≤ **2% do saldo** (`QUANT_MAX_RISK_PCT`) | HK50 opera dentro de 2%. O **US500 usa limite próprio de 12%** (`max_risk_pct`); sem ele, só liberaria com saldo acima de ~$80. |
| Reserva de margem | A margem livre que sobra deve ser ≥ **3× a margem da posição** (`QUANT_MARGIN_RESERVE_MULT`) | Nunca usa toda a margem, então sobra dinheiro para as próximas tentativas |
| Perda diária | Bloqueia novas entradas depois de perder 2% no dia | Limita uma sequência ruim |
| Uma entrada por candle | Não reentra no mesmo sinal | Evita repetir o prejuízo |

> **Posições manuais são respeitadas.** Em conta *hedging*, o Modo Quant só gerencia as posições abertas por ele (MAGIC do bot + comentário `Q PULLB` / `Q RSI2MR`). Uma operação que você abriu na mão no mesmo ativo **não é tocada**.

---

## 🎛 Modo Maestro (interativo)

```powershell
mt5bot.bat          # compila o Maestro na primeira vez, depois só abre
# ou: run.bat        # compila e roda via "go run" (exige Go)
```

O painel abre no terminal. Cada ativo vira um "robô" (um worker Python) supervisionado pelo Maestro:

```
 ◆ MT5BOT MAESTRO v2.12.0   LIVE   MT5 ON   CONTA REAL  ─────────────────── 26/10 22:20:00
 Saldo $16.26   Patrimônio $16.38   Margem livre $14.20   Flutuante +$0.12   Posições do robô 1
╭──────────────────────────────────────╮╭──────────────────────────────────────────────────╮
│ROBÔS  2 ativo(s)                     ││EVENT LOG (Live)                                  │
│● HK50 H4                 [POS] 2h13m ││[HK50|H4] PULLB BUY @ 23050.0 ... Enviando a      │
│  EM POSIÇÃO (PULLB BUY)              ││mercado.                                          │
│  ★ QUANT PULLB · candle em 1h 05m    ││                                                  │
│  ✓ risco $0.21 / limite $0.33        │╰──────────────────────────────────────────────────╯
│  ▲ BUY 0.01 @ 23050.00  +$0.12       │╭──────────────────────────────────────────────────╮
│┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄  ││PERFORMANCE RESUMO (Por Ativo)                    │
│● US500 D1               [WAIT] 2h13m ││[HK50|H4] LOTE 0.01  +$0.35  WR 66.7%  3T         │
│  AGUARDANDO MERCADO                  ││[US500|D1] LOTE 0.01  sem dados                   │
╰──────────────────────────────────────╯╰──────────────────────────────────────────────────╯
 | mt5bot ❯ /add US500 D1
```

- **Cabeçalho:** modo (LIVE/SIMULADOR), conexão com o MT5, conta **REAL/DEMO**, saldo, patrimônio, margem livre e o lucro/prejuízo flutuante das posições do robô.
- **Cartão por robô:** estado colorido, rota quant (★), quanto falta para o candle fechar, risco × limite (✓ ou 🔒) e a posição aberta com P/L.
- **Prompt:** digite `/` e as sugestões aparecem em cinza; **Tab** completa, **Esc** limpa a linha e **Ctrl+C** sai.

| Comando | O que faz |
|---|---|
| `/study HK50 H1` | **Simulação.** Mostra os sinais e abre trades virtuais, **sem ordem real**. Comece por aqui. |
| `/add HK50 H4` | Liga o robô **real** no ativo e timeframe. `HK50 H4` e `US500 D1` usam o Modo Quant automaticamente. |
| `/stop HK50` | Para o robô do ativo |
| `/list` | Lista os robôs ativos |
| `/report` | Relatório em dólar dos trades reais, por estratégia |
| `/dashboard` | Abre o dashboard web ao vivo no navegador |
| `/fix` | Reinicia robôs que entraram em crash loop |
| `/idioma pt\|en\|es` | Troca o idioma da interface |
| `/quit` | Encerra e mantém as ordens no MT5 |
| `/quit cancel-open` | Cancela as ordens pendentes **do robô** e encerra |
| `/quit wait-flat` | Bloqueia novas entradas e espera as posições **do robô** zerarem |
| `/quit close-all` | **[PÂNICO]** Fecha a mercado as posições **do robô** (as manuais ficam) |

> ⚠️ **Não rode o Modo Quant e o `/add` do mesmo ativo ao mesmo tempo.** Seriam dois processos disputando a mesma posição.

---

## 🖥 Dashboard web

```powershell
.\bot.bat dashboard     # ou /dashboard no Maestro
```

Abre no navegador um painel **ao vivo** (atualiza a cada 5 s), em português, inglês ou espanhol:

- **Indicadores:** saldo, patrimônio, margem livre, resultado do dia e flutuante do robô, com o selo REAL/DEMO.
- **Rotas quant:** risco por trade × limite e quanto falta para o próximo candle.
- **Posições do robô** com SL, TP e P/L.
- **Curva de patrimônio**, desempenho (trades, acerto, fator de lucro, queda máxima) e resultado por estratégia — tudo em **dólar**, com o lucro real do MT5.
- **Configuração** (somente leitura): rotas quant, travas de risco e setups por ativo.

Roda só com a biblioteca padrão do Python, em `localhost`. Nada sai do seu computador.

---

## 🧠 Estratégias

### Validadas (Modo Quant)
Veja a [tabela acima](#as-estratégias-do-modo-quant). Detalhes completos em `memoria/wiki/arquitetura/pesquisa-estrategias-lucrativas.md`.

### Clássicas (Modo Maestro)
São baseadas nos setups da família 9.x (Larry Williams) e nos livros de estratégias operacionais. Qual setup roda em qual ativo é definido em `ASSET_SETUPS` (`mt5bot/core/config.py`).

| Setup | Ideia | Saída |
|---|---|---|
| **9.1** | A EMA9 vira a favor | EMA9 virando contra / trailing |
| **9.2** | Correção leve contra a EMA9 em tendência | idem |
| **9.3** | Recuo profundo com 2 fechamentos | idem |
| **9.4** | Falso recuo (a EMA9 vira e desvira) | idem |
| **PC** | Ponto Contínuo: toque na MM21 em tendência | idem |
| **FFFD** | Bollinger: fechou fora, fechou dentro | trailing |
| **GAP** | Fechamento de gap de abertura > 0,5% | alvo próprio (TP) |
| **russian_bb** | Setup Russo: Bollinger + IFR14 (reversão à média) | só TP/SL |
| **judas** | Fading the open (EURUSD, horários fixos) | só TP/SL |
| **DiNapoli / IFR2 / SAR / RompFalso** | Setups auxiliares | trailing |

Os setups clássicos passam por filtros extras antes da ordem: SMA200, multi-timeframe, volume relativo (RVOL), scoring (RRR ≥ 1) e o veto do XGBoost.

> Em backtest recente, o Setup Russo no HK50 ficou **praticamente no zero a zero** (+$0,13 em 7 meses, −$0,30 nos últimos 2). Por isso o Modo Quant é o recomendado para contas pequenas.

---

## 🛡️ Proteção de capital

| Proteção | Configuração | Onde vale |
|---|---|---|
| Risco por trade 1% do saldo (lote dinâmico, Half-Kelly com a IA) | `MAX_RISK_PER_TRADE_PERCENT` | Maestro |
| Risk Shield: recusa o trade se o lote mínimo arriscar > 1,5% | `ABSOLUTE_MAX_TRADE_RISK_PERCENT` | Maestro |
| Risco no SL ≤ 2% e reserva de margem 3× | `QUANT_MAX_RISK_PCT`, `QUANT_MARGIN_RESERVE_MULT` | Quant |
| Perda diária máxima 2% (bloqueia entradas; no Maestro também liquida) | `MAX_DAILY_LOSS_PERCENT`, `DAILY_MAX_LOSS_CLOSE_ENABLED` | Ambos |
| Filtro de spread (aborta se o spread estiver alto) | `MAX_SPREAD_POINTS`, `SYMBOL_MAX_SPREAD_POINTS` | Ambos |
| Breakeven com trava (entrada + spread + 1 tick) | `ENABLE_BREAKEVEN`, `BREAKEVEN_LOCK_SPREAD_MULT` | Maestro |
| Janela de horário por ativo (ex.: HK50 22:15–01:00 BRT) | `SYMBOL_TRADING_HOURS` | Maestro |
| Capital mínimo por ativo ("Garage Lock") | `MIN_BALANCE_REQUIREMENTS` | Maestro |
| Só candles **fechados** (nada de decidir com vela em formação) | — | Ambos |

---

## 🧭 Comandos do `bot.bat`

Ferramentas rápidas para inspecionar o robô sem abrir arquivos grandes. Cada comando devolve o código de saída real (0 = sucesso).

| Comando | O que faz |
|---|---|
| `bot.bat setup` | **Assistente:** confere o MT5, a conta (REAL/DEMO) e o risco de cada rota; libera a conta REAL |
| `bot.bat quant` | **Liga o Modo Quant** (HK50 H4 / US500 D1 ao vivo; US100 D1 e USDJPY H1 em estudo, sem ordens) |
| `bot.bat dashboard` | **Abre o dashboard web ao vivo** no navegador |
| `bot.bat diagnose` | Conexão com o MT5, saldo, margem e erros do `bot.log` nas últimas 24h |
| `bot.bat market` | Preço, spread, valor do tick e margem dos ativos configurados |
| `bot.bat config` | Risco %, perda diária, filtro de IA, **rotas quant com o limite em $ pelo saldo atual** e setups por ativo |
| `bot.bat positions` | Posições do robô e operações virtuais (paper) |
| `bot.bat performance` | Lucro líquido e taxa de acerto dos últimos 7 dias |
| `bot.bat tail` | Últimas 15 linhas do log mais recente (`%APPDATA%\mt5bot\logs`) |
| `bot.bat hardware` | Uso de CPU/RAM |
| `bot.bat backtest HK50 3` | Backtest do Setup Russo (ativo, meses). Só lê o histórico. |
| `bot.bat train` | Retreina o modelo XGBoost |
| `bot.bat ask "pergunta"` | Consulta a memória do projeto (RAG) |
| `bot.bat test` | Roda a suíte de testes |
| `bot.bat ci` | Roda localmente os mesmos passos do CI (lint, testes, pacote e Maestro) |
| `bot.bat build` | Compila o Maestro (`maestro\maestro.exe`) |
| `bot.bat panic` | 🚨 **Fecha a mercado todas as posições do robô** (as manuais ficam) |
| `bot.bat anotar ...` | **Diário de sinais:** anota um sinal *antes* do resultado (veja a seção própria) |
| `bot.bat diario` | Mede os sinais anotados e diz se o seu olho tem vantagem estatística |

Para ver o log do Modo Quant: `Get-Content $env:APPDATA\mt5bot\logs\quant_runner.log -Tail 20`

---

## ⚙️ Configuração

Os padrões ficam em **`mt5bot/core/config.py`**. Para mudar sem editar código, crie o arquivo **`%APPDATA%\mt5bot\config.toml`** (o `bot.bat config` mostra o caminho exato e marca com `[config.toml]` cada valor que veio dele):

```toml
quant_max_risk_pct = 2.0          # perda máxima no SL, % do saldo (padrão das rotas)
max_daily_loss_percent = 2.0      # trava diária
ml_filter_enabled = true          # veto do XGBoost nos setups clássicos

[routes.US500]
max_risk_pct = 12.0               # limite próprio desta rota
enabled = true                    # false desliga a rota
```

Valores com tipo errado ou fora da faixa são **recusados com aviso** (citando o arquivo e a chave), e o padrão é mantido. Nada derruba o robô.

Os padrões mais importantes do `config.py`:

```python
# Rotas quant: (ativo) -> timeframe, setup e parametros validados
QUANT_ROUTES = {
    "HK50":  {"timeframe": "H4", "setup": "PULLB",  "params": {"sl_atr": 1.0, "tp_r": 2.0}},
    "US500": {"timeframe": "D1", "setup": "RSI2MR", "params": {"rsi_level": 5.0, "sl_atr": 2.0,
                                                              "long_only": False, "max_bars": 15},
              "max_risk_pct": 12.0},   # limite proprio: cada stop ~10% da conta com $16
}
QUANT_MAX_RISK_PCT = 2.0           # perda maxima no SL, % do saldo (rota pode ter "max_risk_pct" proprio)
QUANT_MARGIN_RESERVE_MULT = 3.0    # margem livre que precisa sobrar (x margem da posicao)

MAX_RISK_PER_TRADE_PERCENT = 1.0   # Maestro: risco por trade
MAX_DAILY_LOSS_PERCENT = 2.0       # trava diaria
ML_FILTER_ENABLED = True           # veto do XGBoost nos setups classicos
ML_MIN_WIN_PROB = 0.40
ASSET_SETUPS = {...}               # quais setups classicos rodam em cada ativo
SYMBOL_TRADING_HOURS = {...}       # janela de horario por ativo (BRT)
MAGIC = 20260731                   # identifica as ordens do robo no MT5
```

> **Não mude os parâmetros das rotas quant sem refazer a validação** ([veja como](#-backtest-e-pesquisa-de-estratégias)). Ajustar um número para "melhorar" o passado é o caminho mais curto para o overfitting.

---

## 📂 Onde ficam os dados e logs

| Arquivo | Conteúdo |
|---|---|
| `%APPDATA%\mt5bot\trades.json` | Histórico de trades (entradas, saídas, lucro real com comissão e swap) |
| `%APPDATA%\mt5bot\virtual_rejections.json` | Sinais rejeitados (risco, spread, IA), usados pelo Otimizador |
| `%APPDATA%\mt5bot\config.toml` | Sua configuração (opcional), sobre os padrões do `config.py` |
| `%APPDATA%\mt5bot\diario_sinais.csv` | Diário de sinais (abre no Excel; separador `;`) |
| `%APPDATA%\mt5bot\quant_study.json` | Operações virtuais das rotas em estudo (ex.: US100) |
| `%APPDATA%\mt5bot\logs\quant_runner.log` | Log do Modo Quant |
| `%APPDATA%\mt5bot\logs\bot_AAAAMMDD.log` | Logs do Maestro/Cérebro |

O bot é **stateless**: se o PC reiniciar, ele relê as posições direto do MT5 e continua de onde parou.

---

## 🚨 Emergência: como parar tudo

1. **Pare o robô** para ele não reabrir posições: **Ctrl+C** na janela do `bot.bat quant`, ou `/quit` no Maestro.
2. **Feche as posições do robô:** `bot.bat panic` (ou `/quit close-all` no Maestro).
3. Se o PC travar: as posições abertas pelo robô já têm **SL no servidor da corretora**. Feche manualmente pelo MT5 (inclusive pelo celular) se precisar.

---

## 🔬 Backtest e pesquisa de estratégias

**Backtest do Setup Russo** (só lê o histórico):

```powershell
bot.bat backtest HK50 3
```

**Refazer a pesquisa quant** (com o MT5 aberto; não envia ordens):

```powershell
cd tools\quant_research
python fetch.py JP225,US500,FR40,AU200,HK50,USOIL+,ETHUSD,EU50,UK100   # baixa candles
python meta.py                                                          # custos e valor do ponto
python research.py HK50,US500 M15,H1,H4,D1 r_all.json                   # grade (~1 min)
python analyze.py r_all.json                                            # robustez dentro x fora da amostra
python deep.py                                                          # ano a ano + spread 1,5x
```

**Pesquisa ampla (rodada 3):** 337 ativos de margem baixa, 31 famílias de estratégias, sazonalidade de horário/dia/data, *lead-lag* entre ativos e pares, com protocolo pré-registrado, FDR, *walk-forward*, Deflated Sharpe e Monte Carlo de ruína. Roda sozinha e retoma de onde parou:

```powershell
cd tools\quant_research
python pipeline2.py              # tudo; veja ESTADO_PESQUISA.md e RESULTADOS2.md
python check_ema9_filters.py US500 M15 2026-10-23   # testa a regra da MME9 num dia e no histórico
python check_horner.py GBPUSD H1                    # onda MME34 + ângulo do relógio (Raghee Horner)
```

Se o download parar por falta de disco: feche o MT5, rode `python clean_mt5_cache.py` e reabra. Método e resultados: guia técnico, cap. 14.

Antes de mudar uma rota, exija: lucro **nos dois períodos**, a maioria das variações da família positiva, queda máxima que caiba no seu saldo e resultado que se mantém com spread 1,5×.

---

## 🤖 Machine Learning (XGBoost)

Nos setups clássicos, cada sinal leva um "retrato" do mercado: distâncias das médias, ADX, ATR, IFR, microestrutura do candle, horário e outras variáveis. Um modelo **XGBoost** estima a probabilidade de acerto e **veta** o trade abaixo de `ML_MIN_WIN_PROB`. Os sinais vetados continuam sendo acompanhados como "ordens fantasma" e viram dados de treino.

- Modelos: `models/mt5bot_xgboost_<ATIVO>_v*.json`.
- Retreinar: `bot.bat train`.
- O Modo Quant **não** usa o XGBoost (não fez parte da validação).

---

## 📲 Notificações no Telegram

O logger envia alertas ao Telegram se as variáveis `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID` existirem. O `.env.example` explica como obter o token (@BotFather) e o chat id. O bot **não carrega o arquivo `.env` sozinho**, então defina as variáveis no Windows:

```powershell
setx TELEGRAM_BOT_TOKEN "123456789:ABC..."
setx TELEGRAM_CHAT_ID "123456789"
# feche e reabra o terminal
```

---

## 📓 Diário de sinais: teste o seu olho

Viu um sinal no gráfico e acha que ele vai pagar? **Anote antes de saber o resultado.** O robô mede depois e, com o tempo, diz se o seu critério tem vantagem real ou se é sorte. É assim que uma leitura de gráfico vira (ou não) uma estratégia automática.

### Como anotar (passo a passo)

1. **Com o mercado aberto e o MT5 ligado**, assim que o candle do sinal **fechar**, abra o terminal na pasta do MT5Bot.
2. Rode, trocando pelos seus dados:
   ```powershell
   bot.bat anotar US500 M15 venda bom "tendência forte (relógio 1h), volume alto, cruzou a MME9"
   ```
   Formato: `bot.bat anotar ATIVO TEMPO_GRÁFICO compra|venda bom|ruim "por que"`.
   - **ATIVO:** o nome igual ao do MT5 (`US500`, `HK50`, `EURUSD`...).
   - **TEMPO GRÁFICO:** `M1`, `M5`, `M15`, `M30`, `H1`, `H4` ou `D1`.
   - **bom ou ruim:** a sua aposta. Anote **também os sinais que você acha ruins**: é a comparação entre os dois grupos que mostra se o seu olho separa os bons dos ruins.
   - **Por que:** o que você viu (tendência, ângulo, volume, horário, VWAP). Isso vira a regra do robô depois.
   - Opcional: `--alvo 1` para alvo de 1× o risco (o padrão é 2×).
   - Sem argumentos (`bot.bat anotar`), ele pergunta tudo.
3. O robô grava **sozinho** a hora exata e o preço de entrada do momento (ask na compra, bid na venda). O stop é a **mínima** do último candle fechado (compra) ou a **máxima** (venda), e o alvo é 2× essa distância.
4. Veja os resultados quando quiser:
   ```powershell
   bot.bat diario
   ```
   Ele confere cada anotação com os candles de 1 minuto do MT5: bateu o alvo, bateu o stop ou ainda está aberta. Depois de 5 dias sem decisão, a anotação expira pelo preço do momento.

### Regras para o teste valer

- **Nunca anote depois de ver o resultado.** O sistema grava a hora, e anotar com o preço já andando estraga a medição. Com o mercado fechado, ele recusa a anotação.
- **Anote todos os sinais que você notou**, não só os que "parecem bons". Escolher só os melhores depois é o viés que o diário existe para evitar.
- **Não apague anotações ruins.** O arquivo `%APPDATA%\mt5bot\diario_sinais.csv` pode ser aberto no Excel, mas não edite os resultados.
- **Tenha paciência:** com menos de 30 sinais "bom" encerrados, a sorte explica quase qualquer resultado. O `bot.bat diario` avisa quando há amostra suficiente.

### Como ler o resultado

```
Sinais 'bom': 34 encerrados, acerto 47% (empate exige 33%), resultado $+0.85, chance de ser sorte 3%
Sinais 'ruim': 21 encerrados, acerto 24% (empate exige 33%), resultado $-0.40, chance de ser sorte 84%
```

- **Empate exige:** o acerto mínimo para não perder, dado o alvo (alvo 2× → 33%; alvo 1× → 50%).
- **Chance de ser sorte:** a probabilidade de acertar tanto por acaso (teste binomial). **Abaixo de 5%** com resultado positivo, o seu olho mostra vantagem, e o próximo passo é transformar o seu "por que" em regra de robô e testá-la no histórico com `tools/quant_research`.

---

## 🏗️ Arquitetura

```
┌──────────────────────┐   JSON (stdin/stdout)   ┌───────────────────────────────┐
│  Maestro (Go, TUI)   │ ──────────────────────▶ │  Cérebro (Python)             │
│  supervisiona workers│ ◀────────────────────── │  interfaces/brain_worker.py   │
│  /add /study /quit   │                         │   └─ execution_manager        │
└──────────────────────┘                         │       ├─ rota quant ──▶ quant_manager
                                                 │       └─ clássico   ──▶ strategy + filtros + IA
┌──────────────────────┐                         │                               │
│ tools/quant_runner.py│ ──── manage_cycle ────▶ │  executor ──▶ MetaTrader 5    │
│   (bot.bat quant)    │                         └───────────────────────────────┘
└──────────────────────┘
```

- **Só o Python fala com o MT5.** O Maestro fica fora do caminho da ordem.
- **Stateless:** cada ciclo deduz o estado a partir das posições e ordens no MT5.

```
mt5_bot/
├── mt5bot/
│   ├── core/          config.py (todos os parâmetros), launcher, logger
│   ├── engine/        strategy.py (setups clássicos), quant_setups.py, indicators, scoring, trailing
│   ├── execution/     execution_manager.py, quant_manager.py, executor.py (ordens)
│   ├── risk/          risk_calculator.py (lote, travas, horários)
│   ├── data/          tracker.py (trades reais), paper_tracker.py (virtuais/rejeições)
│   └── mentorship/    ml_xgboost.py, supervisor, optimizer, simulator
├── interfaces/        brain_worker.py (worker chamado pelo Maestro)
├── maestro/           Maestro em Go (TUI); o maestro.exe é gerado por bot.bat build
├── tools/             bot.bat tools, quant_runner.py, quant_research/, backtest.py
├── memoria/           memória permanente do projeto (wiki + RAG BM25)
├── tests/             suíte pytest (MT5 simulado)
└── bot.bat            canivete de comandos
```

---

## 🩺 Solução de problemas

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| `MT5: Falha` / `Falha ao conectar no MT5` | Terminal fechado ou deslogado | Abra o MT5, faça login e rode `bot.bat diagnose` |
| Erro de ordem `10027` | **Algo Trading** desligado | Ligue o botão Algo Trading (verde) |
| Erro `10016` (invalid stops) | SL muito perto do preço | O Modo Quant já confere o *stops level*; no Maestro, veja o ATR/timeframe |
| `SPREAD FILTER REJECTED` | Spread acima do limite (baixa liquidez) | Normal fora do horário principal; ajuste `SYMBOL_MAX_SPREAD_POINTS` se fizer sentido |
| `perda no SL $X > limite` | Trade arriscaria mais de 2% do saldo | É a trava de margem funcionando (ex.: HK50 com ATR muito alto, ou o saldo caiu abaixo do que a rota permite) |
| `SEM MARGEM` | Margem livre insuficiente para a reserva | Feche outras posições ou aumente o saldo |
| `SINAL EXPIRADO` | O bot ligou depois da abertura do candle seguinte | Normal; ele espera o próximo sinal |
| `AGUARDANDO MERCADO` | Mercado fechado ou candle seguinte ainda não abriu | Aguarde (ex.: HK50 abre domingo ~22:15 BRT) |
| `GARAGE LOCK` | Saldo abaixo do mínimo do ativo no Maestro | Veja `MIN_BALANCE_REQUIREMENTS` |
| `HORÁRIO FECHADO` | Fora da janela do ativo no Maestro | Veja `SYMBOL_TRADING_HOURS` |
| `bot.bat` não é reconhecido no PowerShell | O PowerShell não executa scripts da pasta atual sem prefixo | Use `.\bot.bat quant` |

---

## 🧪 Desenvolvimento

```powershell
bot.bat test                       # ou: python -m pytest -q
```

- Os testes usam um **MT5 simulado** (`tests/conftest.py`) e não precisam do terminal aberto.
- Toda mudança de lógica precisa de teste (`tests/test_*.py`).
- Logue com `logging`, nunca com `print()` no caminho de produção.
- Manual técnico: [`docs/manual/`](docs/manual/README.md) · Como contribuir: [`CONTRIBUTING.md`](CONTRIBUTING.md) · Histórico de versões: [`CHANGELOG.md`](CHANGELOG.md) · Arquitetura detalhada: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

> [!NOTE]
> **Desenvolvendo com IA?** Leia primeiro o [`AGENTS.md`](AGENTS.md). O projeto tem uma **memória permanente RAG** (`memoria/`) com os livros-fonte das estratégias e todas as decisões de arquitetura. Consulte com `bot.bat ask "sua pergunta"`.

---

<div align="center">

**Licença MIT** · Feito por [Fabio Dornele](https://github.com/fabiodrneles)

*Não corra atrás do preço. Deixe a matemática e a gestão de risco cuidarem do resto.*

</div>
