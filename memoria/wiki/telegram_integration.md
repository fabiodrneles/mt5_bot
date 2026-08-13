# Integração com Telegram e Alertas

## Visão Geral
O MT5Bot possui um sistema de monitoramento e alertas integrado ao Telegram. Esse sistema foi projetado para avisar o gestor do robô sobre eventos críticos, como **rejeição de ordens (Risk Shield)**, erros de conexão com a corretora e disjuntores de segurança, sem a necessidade de olhar para o MetaTrader 5 constantemente.

## Arquitetura de "Falha Silenciosa" (Fail-Safe)
A integração (`logger.py`) foi construída sob os princípios da engenharia institucional:
1. **Thread Separada (Assíncrono):** O envio das mensagens ocorre em uma Thread isolada em background. Isso garante que a rede lenta do Telegram não atrase o fluxo principal de leitura de preços e envio de ordens do robô.
2. **Falha Silenciosa:** Se a internet cair, a API do Telegram falhar ou o limite de mensagens for atingido, o robô ignora o erro e continua rodando o setup. O Telegram **nunca** causará a interrupção do robô.
3. **Modo Dorminhoco (Opt-in):** O código verifica no início da execução se as chaves (Tokens) existem. Se elas não estiverem preenchidas no arquivo `.env`, o código aborta a execução do Telegram de forma invisível. O robô continua 100% funcional sem avisos de erro, esperando o usuário configurar no futuro.

## Como Configurar (Ativação)
Para acordar a funcionalidade, o operador deve criar um arquivo `.env` na raiz do projeto (ou renomear o `.env.example`) e inserir as chaves oficiais.

### Passo a passo:
1. Abra o Telegram e procure por `@BotFather`.
2. Envie o comando `/newbot`, dê um nome ao seu bot de alertas e copie o `TOKEN` gerado.
3. Procure pelo bot `@userinfobot` no Telegram, inicie-o e copie o seu `Id` pessoal numérico.
4. Preencha o arquivo `.env` no projeto com os dados:
```env
TELEGRAM_BOT_TOKEN="123456789:ABCdefGHIjklMNOpqrSTUvwxYZ"
TELEGRAM_CHAT_ID="seu_chat_id_numerico_aqui"
```
5. Reinicie o script do MT5Bot. Ele começará a enviar alertas críticos automaticamente.

## Níveis de Alerta
- **`WARNING` (Aviso):** Ordens bloqueadas pelo Risk Shield (ex: Correlação Simultânea acionada, Gap de Abertura muito alto).
- **`ERROR` (Erro Crítico):** Erros graves de Python, perda de acesso de margem, problemas imprevistos da API do MT5.
