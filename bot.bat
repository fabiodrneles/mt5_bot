@echo off
setlocal
set "CMD=%~1"
set "ARG1=%~2"
set "ARG2=%~3"

if "%CMD%"=="" (
    echo.
    echo ==============================================
    echo        MT5BOT - CANIVETE SUIÇO (CLI)
    echo ==============================================
    echo Uso: bot.bat [comando]
    echo.
    echo Comandos disponiveis:
    echo   diagnose    - Checa MT5, saldo e erros no bot.log
    echo   market      - Mostra spread, tick_value e margem dos ativos
    echo   config      - Mostra configuracoes vitais de risco e setups
    echo   positions   - Mostra trades abertos (Reais e Fantasmas)
    echo   performance - Mostra PnL e WinRate dos ultimos 7 dias
    echo   hardware    - Mostra uso de CPU e RAM
    echo   tail        - Le as ultimas 15 linhas do bot.log
    echo   panic       - Fecha TODAS as ordens do robo instantaneamente
    echo   ask         - Pesquisa na Memoria RAG (ex: bot ask "setup russo")
    echo   train       - Roda o script de treinamento de IA localmente
    echo   backtest    - Roda backtest (ex: bot backtest HK50 1)
    echo   test        - Roda os testes unitarios
    echo ==============================================
    exit /b 0
)

if /i "%CMD%"=="diagnose" (
    python tools\diagnose.py
    exit /b %ERRORLEVEL%
)

if /i "%CMD%"=="market" (
    python tools\market_status.py
    exit /b %ERRORLEVEL%
)

if /i "%CMD%"=="config" (
    python tools\show_config.py
    exit /b %ERRORLEVEL%
)

if /i "%CMD%"=="positions" (
    python tools\show_positions.py
    exit /b %ERRORLEVEL%
)

if /i "%CMD%"=="performance" (
    python tools\show_performance.py
    exit /b %ERRORLEVEL%
)

if /i "%CMD%"=="hardware" (
    python tools\system_resources.py
    exit /b %ERRORLEVEL%
)

if /i "%CMD%"=="tail" (
    python tools\tail_logs.py
    exit /b %ERRORLEVEL%
)

if /i "%CMD%"=="panic" (
    python tools\panic.py
    exit /b %ERRORLEVEL%
)

if /i "%CMD%"=="ask" (
    if "%ARG1%"=="" (
        echo Forneca uma pergunta. Ex: bot ask "como funciona o setup russo?"
        exit /b 1
    )
    python memoria\scripts\query_memory.py "%ARG1%"
    exit /b %ERRORLEVEL%
)

if /i "%CMD%"=="train" (
    python tools\train_xgboost.py
    exit /b %ERRORLEVEL%
)

if /i "%CMD%"=="backtest" (
    if "%ARG1%"=="" (
        echo Ativo e meses em branco. Rodando HK50 por 1 mes.
        python tools\backtest.py --symbol HK50 --months 1
    ) else (
        if "%ARG2%"=="" (
            python tools\backtest.py --symbol %ARG1% --months 1
        ) else (
            python tools\backtest.py --symbol %ARG1% --months %ARG2%
        )
    )
    exit /b %ERRORLEVEL%
)

if /i "%CMD%"=="test" (
    pytest -q
    exit /b %ERRORLEVEL%
)

echo Comando invalido: %CMD%
echo Digite "bot.bat" para ver a lista de comandos.
exit /b 1
