@echo off
setlocal
rem Funciona de qualquer pasta (atalhos do instalador) e usa o Python
rem embutido da instalacao quando existir (spec 002 FR-4).
cd /d "%~dp0"
set "PY=python"
if exist "%~dp0python\python.exe" set "PY=%~dp0python\python.exe"
if defined MT5BOT_PYTHON set "PY=%MT5BOT_PYTHON%"
set "CMD=%~1"
set "ARG1=%~2"
set "ARG2=%~3"

if "%CMD%"=="" (
    echo.
    echo ==============================================
    echo        MT5BOT - CANIVETE SUIÇO ^(CLI^)
    echo ==============================================
    echo Uso: bot.bat [comando]
    echo.
    echo Comandos disponiveis:
    echo   diagnose    - Checa MT5, saldo e erros no bot.log
    echo   market      - Mostra spread, tick_value e margem dos ativos
    echo   config      - Mostra configuracoes vitais de risco e setups ^(--edit abre o config.toml^)
    echo   positions   - Mostra trades abertos ^(Reais e Fantasmas^)
    echo   performance - Mostra PnL e WinRate dos ultimos 7 dias
    echo   hardware    - Mostra uso de CPU e RAM
    echo   tail        - Le as ultimas 15 linhas do bot.log
    echo   panic       - Fecha TODAS as ordens do robo instantaneamente
    echo   ask         - Pesquisa na Memoria RAG ^(ex: bot ask "setup russo"^)
    echo   train       - Roda o script de treinamento de IA localmente
    echo   backtest    - Roda backtest ^(ex: bot backtest HK50 1^)
    echo   test        - Roda os testes unitarios
    echo   ci          - Roda localmente os mesmos passos do CI ^(lint, testes, Maestro^)
    echo   build       - Compila o Maestro ^(maestro\maestro.exe^)
    echo   setup       - Assistente: confere MT5, conta e risco; libera conta REAL
    echo   quant       - Liga as rotas quant ^(HK50 H4 PULLB / US500 D1 RSI2MR^)
    echo   dashboard   - Abre o painel web ao vivo no navegador
    echo ==============================================
    exit /b 0
)

if /i "%CMD%"=="diagnose" (
    "%PY%" tools\diagnose.py
    goto :fim
)

if /i "%CMD%"=="market" (
    "%PY%" tools\market_status.py
    goto :fim
)

if /i "%CMD%"=="config" (
    "%PY%" tools\show_config.py %ARG1% %ARG2%
    goto :fim
)

if /i "%CMD%"=="positions" (
    "%PY%" tools\show_positions.py
    goto :fim
)

if /i "%CMD%"=="performance" (
    "%PY%" tools\show_performance.py
    goto :fim
)

if /i "%CMD%"=="hardware" (
    "%PY%" tools\system_resources.py
    goto :fim
)

if /i "%CMD%"=="tail" (
    "%PY%" tools\tail_logs.py
    goto :fim
)

if /i "%CMD%"=="panic" (
    "%PY%" tools\panic.py
    goto :fim
)

if /i "%CMD%"=="ask" (
    if "%ARG1%"=="" (
        echo Forneca uma pergunta. Ex: bot ask "como funciona o setup russo?"
        exit /b 1
    )
    "%PY%" memoria\scripts\query_memory.py "%ARG1%"
    goto :fim
)

if /i "%CMD%"=="train" (
    "%PY%" tools\train_xgboost.py
    goto :fim
)

if /i "%CMD%"=="backtest" (
    if "%ARG1%"=="" (
        echo Ativo e meses em branco. Rodando HK50 por 1 mes.
        "%PY%" tools\backtest.py --symbol HK50 --months 1
    ) else (
        if "%ARG2%"=="" (
            "%PY%" tools\backtest.py --symbol %ARG1% --months 1
        ) else (
            "%PY%" tools\backtest.py --symbol %ARG1% --months %ARG2%
        )
    )
    goto :fim
)

if /i "%CMD%"=="setup" (
    "%PY%" tools\setup_wizard.py
    goto :fim
)

if /i "%CMD%"=="quant" (
    "%PY%" tools\quant_runner.py
    goto :fim
)

if /i "%CMD%"=="dashboard" (
    "%PY%" -m interfaces.dashboard
    goto :fim
)

if /i "%CMD%"=="build" (
    pushd "%~dp0maestro"
    go build -o maestro.exe .
    popd
    goto :fim
)

if /i "%CMD%"=="ci" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\ci.ps1"
    goto :fim
)

if /i "%CMD%"=="test" (
    "%PY%" -m pytest -q
    goto :fim
)

echo Comando invalido: %CMD%
echo Digite "bot.bat" para ver a lista de comandos.
exit /b 1

:fim
rem Fora de bloco ( ): aqui %ERRORLEVEL% e o codigo real do ultimo comando.
exit /b %ERRORLEVEL%
