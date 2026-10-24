# 003 — Dados e configuração do usuário

- **Prioridade:** P0
- **Status:** Done
- **Código afetado:** `mt5bot/core/config.py`, `mt5bot/core/logger.py`, `tools/quant_runner.py`, `mt5bot/data/*`, novo `mt5bot/core/paths.py`
- **Resolve:** A5, A6

## Contexto

Instalado, o programa fica numa pasta que o usuário não deve editar. Configurações, logs e estado precisam morar na pasta de dados do usuário.

## Estado atual (verificado)

- A configuração só muda editando `mt5bot/core/config.py`.
- O `quant_runner.py` grava em `<raiz>/logs/quant_runner.log`; o `logger.py` grava em `logs/`.
- Os trades já ficam em `%APPDATA%\mt5bot\trades.json` (correto).

## Requisitos funcionais

- **FR-1** MUST existir um módulo único de caminhos (`paths.py`): dados em `%APPDATA%\mt5bot` (Windows), `~/.local/share/mt5bot` (Linux) e `~/Library/Application Support/mt5bot` (macOS).
- **FR-2** Logs e estado MUST ir para `<dados>/logs` e `<dados>/state.json`.
- **FR-3** Um `<dados>/config.toml` opcional MUST sobrepor os valores de `config.py` (rotas quant, `max_risk_pct`, limites de risco), validando tipos e faixas. Um valor inválido MUST gerar erro claro, e o padrão é mantido.
- **FR-4** O `bot.bat config` e o dashboard MUST mostrar de onde vem cada valor (padrão ou `config.toml`).
- **FR-5** SHOULD existir `bot.bat config --edit`, que cria o `config.toml` comentado e o abre no editor.

## Critérios de aceite

- **AC-1** Dado um `config.toml` com `[routes.US500] max_risk_pct = 5`, quando o robô inicia, então o limite efetivo do US500 é 5%.
- **AC-2** Dado `max_risk_pct = 500`, quando o robô inicia, então ele recusa o valor com uma mensagem que cita o arquivo e a chave, e usa o padrão.
- **AC-3** Dado o programa instalado numa pasta somente leitura, quando o Modo Quant roda, então os logs aparecem em `<dados>/logs`.

## Fora de escopo

- Edição da configuração pelo dashboard web (a web continua somente leitura nesta fase).

## Decisões

- —
