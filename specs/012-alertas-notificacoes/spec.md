# 012 — Alertas e notificações

- **Prioridade:** P1
- **Status:** Draft
- **Código afetado:** `mt5bot/core/logger.py` → novo `mt5bot/core/notify.py`, `mt5bot/core/user_config.py`, `setup_wizard.py`, `bot.bat`
- **Resolve:** G11 · R8

## Contexto

Quem usa um robô não fica olhando a tela. O alerta no celular é o que separa "descobri o problema na hora" de "descobri no fim do mês". A função do Telegram já existe em `logger.py:45`, mas está solta: lê o `.env`, só manda avisos e erros de log, e não tem eventos de negócio.

## Requisitos funcionais

- **FR-1** MUST existir um módulo `notify.py` com uma fila e uma *thread* única de envio (sem criar uma *thread* por mensagem), com limite de taxa (no máximo 20 mensagens/minuto, agrupando o excesso).
- **FR-2** Canais: Telegram (MUST) e e-mail SMTP (MAY). O canal é configurado em `[notify]` no `config.toml`; o segredo vem do cofre (spec 014).
- **FR-3** Eventos MUST ter nível e ser filtráveis: posição aberta e fechada (com resultado em $ e R), kill switch (007), reconexão e falha de reconexão (008), SL não confirmado (008, `CRITICAL`), rota pausada (011), erro não tratado e **resumo diário** (horário configurável: trades, resultado, patrimônio, *drawdown*, estado das rotas).
- **FR-4** MUST existir `bot.bat notify --test`, que manda uma mensagem de teste e diz claramente se falhou e por quê.
- **FR-5** O assistente de primeiro uso (spec 006) SHOULD oferecer a configuração do Telegram.
- **FR-6** Falha no envio MUST NOT afetar o trading: só um aviso no log, sem nova tentativa infinita.
- **FR-7** Mensagens MUST NOT conter o *token*, o número completo da conta nem caminhos do usuário.

## Critérios de aceite

- **AC-1** Dado o Telegram fora do ar (mock com *timeout*), quando uma posição abre, então o ciclo de trading termina no mesmo tempo (±100 ms) e há um aviso no log.
- **AC-2** Dados 100 eventos num segundo, então saem no máximo 20 mensagens no minuto e a última diz quantas foram agrupadas.
- **AC-3** Dado `[notify] min_level = "critical"`, uma posição aberta não gera mensagem; um SL não confirmado gera.
- **AC-4** O resumo diário mostra os mesmos números do dashboard (fonte única: `telemetry`).
- **AC-5** Nenhuma mensagem gerada nos testes contém o *token* configurado.

## Fora de escopo

- Comandos recebidos pelo Telegram (controlar o robô pelo celular): exige autenticação forte e fica para uma spec própria.

## Decisões

- —
