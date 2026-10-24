@echo off
echo =======================================================
echo          MT5 BOT - QUANTITATIVE ENGINE
echo =======================================================
echo.
echo Compilando e iniciando o Maestro (Go)...
echo.
cd /d "%~dp0maestro"
rem go run . compila todos os arquivos do pacote (main.go sozinho nao compila).
go run .
pause
