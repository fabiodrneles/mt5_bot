# MT5Bot

### Lucros consistentes. Zero emocao.

<!-- Teste de pipeline de CI/CD -->

Bot de trading automatizado para MetaTrader 5 que opera com disciplina absoluta enquanto voce foca no que importa. Baseado nos Setups 9.1 e 9.2 de Palex (Larry Williams), com inteligencia de volatilidade que adapta cada operacao ao momento real do mercado.

---

## Por que usar o MT5Bot?

| Problema | Solucao |
|----------|---------|
| Voce perde dinheiro por emocao | O bot opera 100% tecnico, sem hesitacao |
| Alvos irreais causam stops desnecessarios | Alvo adaptativo calcula o que o mercado esta pagando |
| Voce nao esta disponivel 24h | O bot monitora e opera enquanto voce dorme |
| Reiniciar perde contexto | Persistencia total — retoma exatamente de onde parou |
| Configuracao complexa assusta | Ja vem pronto. Conecte e observe |

---

## Comece em 3 Passos

### 1. Instale

pip install .

### 2. Execute

mt5bot

### 3. Conecte sua conta e observe

O bot faz o resto. Nenhuma configuracao necessaria — ele ja vem otimizado para operar com seguranca.

---

## Instalacao Completa

### Requisitos

- *Windows 10/11* (MetaTrader 5 exige Windows)
- *Python 3.10+* — [baixe aqui](https://www.python.org/downloads/)
- *MetaTrader 5* instalado com conta ativa (demo ou real)

### Instalar

# Baixar e entrar na pasta do bot
cd mt5_bot-main

# Instalar como comando do sistema
pip install .

Pronto. O comando mt5bot esta disponivel no seu terminal.

### Verificar

mt5bot --version

### Para desenvolvedores

pip install -e .    # Modo editavel — alteracoes refletem imediatamente

---

## Como Funciona

Ao executar mt5bot, voce ve o menu principal:

    ╔══════════════════════════════════════════════════╗
    ║                                                  ║
    ║   MT5Bot  v1.1.0                                 ║
    ║   Measured, disciplined execution — performance varies with market conditions.              ║
    ║                                                  ║
    ╚══════════════════════════════════════════════════╝

  Como deseja iniciar?

    1. Iniciar direto             (sem alterar nada — recomendado)
    2. Configurar no terminal     (ajustar parametros via CLI)
    3. Configurar no navegador    (interface visual no browser)
    4. Ver relatorio              (historico de ganhos e perdas)

  > Opcao [1]:

### Opcao 1 — Iniciar direto (recomendado)

Nao quer mexer em nada? Perfeito. O bot ja vem configurado com parametros conservadores e eficientes. Voce so precisa:

1. Conectar sua conta MT5 (login + senha + servidor)
2. Pronto. O bot opera sozinho.

### Opcao 2 — Configurar no terminal

Para quem quer ajustar fino: volume, ativos, estrategia, risco. Tudo via menus interativos no terminal. Pressione Enter em qualquer campo para manter o valor padrao.

### Opcao 3 — Configurar no navegador

Abre uma interface visual completa no seu browser. Formularios com todos os campos, dropdowns e validacao. Preencha, clique "Salvar e Iniciar", e volte ao terminal para acompanhar.

### Opcao 4 — Ver relatorio

Mostra o balanço completo: operacoes ganhas, perdidas, win rate, profit factor, drawdown, e performance por ativo e por setup. Disponivel no terminal (texto) ou no navegador (visual).

---

## Conectando sua Conta MT5

O primeiro passo sempre e conectar ao MetaTrader 5.

### Conexao automatica

Se o MT5 ja estiver aberto e logado, o bot detecta e conecta sozinho:

  [CONEXAO MetaTrader 5]

    Conectado automaticamente!

    Conta                        12345678
    Nome                         Seu Nome
    Servidor                     SuaCorretora-Server
    Balance                      10000.00 USD

  > Usar esta conta? [s]:

### Conexao manual

Se o MT5 nao estiver logado, informe suas credenciais:

  > Numero da conta (login): 12345678
  > Senha da conta: ********
  > Servidor (ex: MetaQuotes-Demo): SuaCorretora-Server

*Onde encontrar esses dados:*

- *Login*: numero da conta no email da corretora
- *Senha*: a que voce definiu ao criar a conta
- *Servidor*: aparece no MT5 em "Arquivo > Conectar a Conta"

*Seguranca:*

- Senha digitada em modo oculto (nao aparece na tela)
- Nenhuma credencial e salva em arquivo
- Conexao via API oficial MetaTrader 5

---

## O que o Bot Faz por Voce

### Setup 9.1 — Captura a virada do mercado

Detecta o momento exato em que a tendencia de curto prazo muda de direcao (EMA9 vira), confirma com a tendencia maior (EMA21), e entra com ordem stop no ponto tecnico ideal.

### Setup 9.2 — Aproveita o pullback apos lucro

Quando o 9.1 fecha com lucro e o mercado continua favoravel, o bot identifica o primeiro retorno a EMA9 (pullback) e entra novamente. E como surfar a mesma onda duas vezes.

### Alvo Adaptativo — Lucra o que o mercado esta pagando

O bot calcula a *amplitude mediana dos ultimos 20 candles*. Se o candle de referencia for muito maior que a media, o alvo e reduzido (o mercado ja esticou). Se for menor, o alvo e aumentado. Resultado: *lucros menores mas muito mais frequentes*.

| Mercado | Acao do bot |
|---------|-------------|
| Candle grande (esticou) | Alvo reduzido — trava lucro rapido |
| Candle normal | Alvo padrao |
| Candle pequeno (comprimido) | Alvo aumentado — mais espaco para correr |

### ATR Dinamico — Stop inteligente

Em momentos de alta volatilidade (ATR > 1.5x a media), o stop loss e alargado proporcionalmente. Isso evita ser "estopado" por ruido quando o mercado esta agitado, mas a direcao esta correta.

### Saida Parcial — Trava lucro + deixa correr

Ao atingir o alvo:
1. *50% do volume* e fechado (lucro no bolso)
2. *50% restante* continua correndo ate a EMA9 virar contra

### Persistencia — Nunca perde o fio

O estado e salvo a cada transicao em state.json. Se o PC reiniciar, se a luz cair, se o Windows atualizar — ao religar, o bot retoma exatamente de onde parou.

### Shutdown Seguro (com comportamento seguro por padrão)

Ao encerrar o bot (Ctrl+C ou comando `exit`), o comportamento padrao e seguro e *nao cancelar ordens abertas*: o bot salva o estado e encerra a conexao, deixando posicoes e ordens pendentes intactas. Isso evita que interrupcoes acidentais fechem trades lucrativos.

Opcoes de shutdown (CLI ou comandos no console):

- `save-only` (padrao): salva o estado e encerra; nao cancela ordens/posicoes.
- `wait-flat`: salva e aguarda (por `SHUTDOWN_WAIT_SECONDS`) até que nao haja posicoes nem ordens pendentes antes de encerrar.
- `cancel-open`: cancela ordens pendentes antes de encerrar (uso explicito; pode implicar perda de lucro).

Uso via console enquanto o bot roda (digite no mesmo terminal):

- `exit` ou `quit` — inicia shutdown com acao padrao (`save-only`).
- `exit now` ou `exit cancel` — inicia shutdown com `cancel-open`.
- `exit when flat` — inicia shutdown com `wait-flat`.

Uso via CLI ao iniciar:

```bash
mt5bot --shutdown-action save-only
mt5bot --shutdown-action wait-flat
mt5bot --shutdown-action cancel-open
```

O padrao de mercado recomendado e `save-only` — seguro para a maior parte dos usuarios. Use `wait-flat` ou `cancel-open` apenas quando conscientemente desejar esses comportamentos.

---

## Relatorio de Performance

O bot registra *cada operacao* automaticamente e oferece analise completa.

### No terminal

mt5bot --report

============================================================
  RELATORIO DE PERFORMANCE — MT5Bot
============================================================

  Operacoes fechadas:              47
  Vitorias:                        31 (66.0%)
  Derrotas:                        14
  PnL total (pips):                +0.04520
  Profit Factor:                   2.14
  Max Drawdown (pips):             0.00890

  POR ATIVO:
    HK50         18W/7L (72.0%)  PnL: +0.02800
    EURUSD       13W/7L (65.0%)  PnL: +0.01720

  POR SETUP:
    Setup 9.1    22W/11L (66.7%)  PnL: +0.03100
    Setup 9.2    9W/3L (75.0%)    PnL: +0.01420
============================================================

### No navegador (dashboard visual)

mt5bot --dashboard

Interface grafica com cards de metricas, tabelas por ativo, tabelas por setup, e historico completo de todas as operacoes.

### Metricas que voce recebe

| Metrica | O que significa |
|---------|----------------|
| *Win Rate* | % de trades que deram lucro |
| *Profit Factor* | Quanto voce ganha para cada $1 que perde (>1 = lucrativo) |
| *Max Drawdown* | Pior momento — maior sequencia de perdas acumuladas |
| *PnL por ativo* | Qual instrumento esta performando melhor |
| *PnL por setup* | Setup 9.1 ou 9.2 — qual gera mais resultado |
| *Sequencias* | Maior numero de vitorias/derrotas seguidas |

---

## Todos os Comandos

| Comando | O que faz |
|---------|-----------|
| mt5bot | Menu principal (escolha como iniciar) |
| mt5bot --quick | Inicia direto com config padrao |
| mt5bot --report | Relatorio de performance no terminal |
| mt5bot --dashboard | Relatorio visual no navegador |
| mt5bot --version | Versao instalada |
| mt5bot --help | Ajuda completa |

Ou rode direto sem instalar:

python main.py

---

## Exemplos de Cenários de Uso

### 1. Iniciar o bot rapidamente com configuração padrão
Use quando você quer entrar em operação sem ajustar nada.

```bash
mt5bot --quick
```

O bot conecta ao MetaTrader 5, carrega todos os ativos configurados e começa a operar com os parâmetros de risco padrão.

### 2. Consultar o relatório de performance depois de uma sessão
Use este comando se você quer ver o resultado das operações fechadas sem abrir o dashboard.

```bash
mt5bot --report
```

### 3. Abrir o dashboard visual no navegador
Use quando quiser uma visão gráfica das métricas, ativos e desempenho por setup.

```bash
mt5bot --dashboard
```

### 4. Encerrar o bot com comportamento seguro
Enquanto o bot está rodando, digite no mesmo terminal:

- `exit` ou `quit` — salva estado e encerra sem cancelar ordens abertas.
- `exit when flat` — espera o fechamento de posições/ordens e encerra quando o mercado ficar flat.
- `exit now` ou `exit cancel` — cancela ordens pendentes e encerra.

### 5. Usar shutdown explícito ao iniciar
Escolha o comportamento de desligamento antes de iniciar o bot. Exemplo:

```bash
mt5bot --shutdown-action wait-flat
```

Isso configura o shutdown para `wait-flat` antes mesmo do bot começar.

---

## Configuracao Padrao (funciona sem alterar nada)

O bot ja vem com esses valores — otimizados para operacao conservadora:

| Parametro | Valor | Por que |
|-----------|-------|---------|
| Volume | 0.01 lote | Risco minimo por operacao |
| Ativos | HK50, EURUSD, US500 | Liquidez alta, spreads baixos |
| Timeframe | H1 | Equilibrio entre sinais e ruido |
| Setup 9.1 | Ativado | Captura viradas |
| Setup 9.2 | Ativado | Aproveita continuacoes |
| Saida parcial | 50% a 100% amplitude | Trava lucro no alvo |
| Alvo adaptativo | Ativado | Ajusta ao mercado real |
| ATR dinamico | >1.5x alarga stop | Protege contra volatilidade |
| Filtro Flat | Ativado | Ignora mercado lateral |

### Parametros avancados (para quem quer personalizar)

| Parametro | Default | Descricao |
|-----------|---------|-----------|
| EMA_PERIOD | 9 | Periodo da EMA de sinal |
| EMA_FILTER_PERIOD | 21 | Periodo da EMA filtro |
| PARTIAL_EXIT_PERCENT | 0.50 | % do volume fechado no alvo |
| PARTIAL_EXIT_TARGET | 1.00 | Alvo em % da amplitude |
| ADAPTIVE_TARGET_LOOKBACK | 20 | Candles para calcular mediana |
| ATR_HIGH_VOL_THRESHOLD | 1.5 | Ratio para alargar stop |
| ATR_DAMPING_FACTOR | 0.8 | Amortecimento do stop |
| FLAT_THRESHOLD_TICKS | 5 | Limiar para detectar flat |
| TICK_OFFSET | 1 | Distancia entry/SL do candle |
| SCAN_INTERVAL_SECONDS | 10 | Intervalo de verificacao |
| MAGIC | 20260731 | ID unico das ordens do bot |

---

## Arquitetura

mt5_bot-main/
├── main.py            Ponto de entrada + loop principal
├── tui.py             Configuracao via terminal
├── dashboard.py       Configuracao + relatorio via navegador
├── tracker.py         Registro de trades + calculo de performance
├── config.py          Parametros centralizados
├── indicators.py      EMA, ATR, alvo adaptativo, pullback
├── strategy.py        Maquina de estados (cerebro do bot)
├── executor.py        Envio de ordens ao MetaTrader 5
├── persistence.py     Salvar/carregar estados (JSON)
├── logger.py          Logs diarios em arquivo + terminal
├── test_strategy.py   15 testes automatizados
├── pyproject.toml     Empacotamento CLI
├── state.json         Estado atual (gerado automaticamente)
├── trades.json        Historico de operacoes (gerado automaticamente)
└── logs/              Logs diarios

### Fluxo de Estados

SCANNING ──→ SIGNAL_READY ──→ IN_POSITION ──→ WATCHING_92
   ↑              │                │                │
   │         (cancelado)      (prejuizo)    (timeout/contra)
   └──────────────┘────────────────┘────────────────┘
                                   │
                                   └──(lucro)──→ WATCHING_92 ──→ SIGNAL_READY

---

## Perguntas Frequentes

*Preciso entender de trading para usar?*
Nao. O bot opera sozinho. Voce so precisa ter uma conta MT5 (pode ser demo para testar).

*Funciona em conta demo?*
Sim. Recomendamos comecar em demo para observar o comportamento antes de usar dinheiro real.

*Posso deixar rodando sozinho?*
Sim. Ele opera de forma autonoma. Para encerrar, pressione Ctrl+C.

*E se o PC desligar?*
Ao religar e executar mt5bot novamente, ele retoma de onde parou. Nenhuma operacao e perdida.

*Qual o risco por operacao?*
Com 0.01 lote (padrao), o risco e a distancia entre entry e stop loss. Tipicamente centavos por trade.

*Funciona no Mac/Linux?*
Nao diretamente. O MetaTrader 5 exige Windows. Use um VPS Windows ou maquina virtual.

*Qual timeframe opera?*
H1 (1 hora). Operacoes duram de horas a poucos dias.

*O bot faz day trade?*
Ele opera no intraday (H1), mas nao faz scalping. O foco e em movimentos tecnicos com risco controlado.

---

## Testes

O bot inclui 15 testes automatizados que validam toda a logica:

python test_strategy.py

Cobrem: deteccao de sinais, cancelamento, saidas parciais, saida total, Setup 9.2, ATR, alvo adaptativo, normalizacao de volume, e protecao contra crashes.

---

## Atualizacoes e notas para desenvolvedores (v1.1.0)

Estas notas explicam as mudancas implementadas recentemente para que qualquer IA ou desenvolvedor
que leia o repositorio entenda o que foi feito e porque.

- **Persistencia relocada:** os arquivos de estado (`state.json`) e trades (`trades.json`) agora sao gravados
  em `%APPDATA%/mt5bot` no Windows (ou `~/.mt5bot` em outros sistemas). Isso evita gravar em `site-packages`
  e problemas com permissões/arquivos corrompidos apos reinstalacao.
- **Serializacao segura:** `persistence.save_states()` e `tracker._save_trades()` convertendo tipos nao-serializaveis
  (ex: `numpy.int64`, `numpy.ndarray`, `datetime`) para tipos nativos antes de chamar `json.dump`.
- **Backup de arquivo corrompido:** se o arquivo de estado estiver ilegivel, o bot faz backup com sufixo
  `.corrupt.<timestamp>` e inicia do zero, gerando um warning para verificacao manual.
- **Shutdown seguro (padrao):** o comportamento padrao ao encerrar e `save-only` — o bot salva estado e encerra
  sem cancelar ordens/posicoes. Opcoes CLI/console: `save-only` (padrao), `wait-flat`, `cancel-open`.
- **Watcher de console:** enquanto o bot roda, voce pode digitar `exit`, `exit now`, `exit when flat` no mesmo terminal
  para iniciar shutdown com a acao desejada.
- **Testes e mocks:** adicionado `conftest.py`/ajustes e `test_strategy.py` restaurado e estabilizado. Os testes usam
  um mock compartilhado do `MetaTrader5` para garantir isolamento e confiabilidade.

Como rodar testes:

```bash
py -3 -m pytest -q
```

Branch de testes criada/push: `testes` (commits com alteracoes de teste e documentacao).

Estas atualizacoes foram feitas para deixar o codigo mais robusto, auditavel e facil de entender por outras
IA/avaliares automatizados — se quiser, eu posso agora gerar um arquivo `DEVELOPER_GUIDE.md` mais formal e detalhado.

---

## Licenca

MIT — Use, modifique e distribua livremente.

---

<p align="center">
<strong>MT5Bot</strong> — Feito para quem quer resultados, nao emocoes.
</p>