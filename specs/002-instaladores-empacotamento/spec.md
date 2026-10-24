# 002 — Instaladores e empacotamento

- **Prioridade:** P0 (Windows) / P2 (macOS, Linux)
- **Status:** Draft
- **Código afetado:** `pyproject.toml`, novo `packaging/` (Inno Setup, scripts Wine), `.github/workflows/release.yml`, `maestro/worker.go`, `mt5bot/core/launcher.py`
- **Resolve:** C2, C3, C4, M6

## Contexto

Para ser um produto, o MT5Bot precisa instalar com dois cliques, sem git, Python ou Go. A lib oficial `MetaTrader5` do Python só existe para Windows; no macOS e no Linux, o próprio terminal MT5 roda via Wine.

## Estado atual (verificado)

- O wheel gerado não contém `mt5bot.mentorship` (importado em `execution_manager.py:10`) e contém módulos antigos de `build/lib`.
- O comando `mt5bot` (launcher) exige `maestro/maestro.exe`, que não vai no pacote.
- O Maestro executa o `python` do PATH (`worker.go:186`).

## Requisitos funcionais

- **FR-1** O `pyproject.toml` MUST descobrir os pacotes automaticamente (`mt5bot*`, `interfaces`), e o wheel MUST importar todos os módulos.
- **FR-2** MUST existir `MT5Bot-Setup-<versão>.exe` (Windows 10/11 x64) que instala: Python embutido com as dependências, o código, o `maestro.exe` compilado, os atalhos "MT5Bot Quant", "MT5Bot Maestro" e "MT5Bot Dashboard", e um desinstalador.
- **FR-3** A instalação MUST funcionar sem permissão de administrador (instalação por usuário, em `%LOCALAPPDATA%\Programs\MT5Bot`).
- **FR-4** O Maestro MUST usar o Python da instalação (variável `MT5BOT_PYTHON` ou caminho relativo), com fallback para o `python` do PATH.
- **FR-5** O workflow de release MUST rodar no push de tag `v*`: CI completo → build → smoke do instalado → publicação com `SHA256SUMS`.
- **FR-6** (conforme D1) MUST existir pacote para Linux e macOS que prepara um prefixo Wine com MT5 + Python para Windows + MT5Bot, rotulado **experimental**.
- **FR-7** O desinstalador MUST preservar os dados do usuário (`%APPDATA%\mt5bot`) e só apagá-los se o usuário marcar essa opção.

## Requisitos não funcionais

- **NFR-1** Instalador Windows com no máximo 200 MB.
- **NFR-2** Instalação em menos de 2 minutos num i3 com 4 GB.

## Critérios de aceite

- **AC-1** Dado o wheel construído no CI, quando se faz `pip install` num venv limpo e se importam todos os módulos de `mt5bot`, então nenhum `ImportError` ocorre.
- **AC-2** Dado o `Setup.exe` no runner Windows, quando instalado em modo silencioso, então `MT5Bot Quant --once` executa e sai com código 0 ou com a mensagem "Falha ao conectar no MT5" (não há MT5 no runner), e nunca com `ImportError`.
- **AC-3** Dada a tag `v2.14.0`, quando o workflow roda, então a Release contém o `Setup.exe`, o pacote Linux/macOS (se D1 = b) e o `SHA256SUMS`, e os hashes conferem.
- **AC-4** Dado o Maestro instalado, quando um robô inicia, então o processo Python é o da instalação.

## Fora de escopo

- Loja da Microsoft (MSIX) e notarização da Apple (dependem de contas pagas; ver D3).
- Rodar o MT5 nativamente no macOS/Linux sem Wine (não existe).

## Decisões

- (aguardando D1, D2, D3)
