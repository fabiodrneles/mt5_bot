@echo off
echo =======================================================
echo          MT5 BOT - PALEX QUANTITATIVE MOTOR
echo =======================================================
echo.
echo Iniciando o Maestro (Golang) que orquestrara os Brains...
echo.

cd maestro
go run main.go worker.go

pause
