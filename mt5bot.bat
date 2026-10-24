@echo off
cd /d "%~dp0maestro"
if not exist maestro.exe (
    where go >nul 2>nul
    if errorlevel 1 (
        echo maestro.exe nao encontrado e o Go nao esta instalado.
        echo Baixe o instalador em https://github.com/fabiodrneles/mt5_bot/releases
        echo ou instale o Go ^(https://go.dev/dl^) e rode: bot.bat build
        exit /b 1
    )
    echo Compilando o Maestro pela primeira vez...
    go build -o maestro.exe . || exit /b 1
)
rem Caminho explicito: nao depende do cmd procurar na pasta atual.
.\maestro.exe %*
