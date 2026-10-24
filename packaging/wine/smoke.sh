#!/usr/bin/env bash
# Smoke test do pacote Linux/macOS (Wine) — spec 002 FR-6.
# Extrai o .tar.gz, roda o install.sh e executa o MT5Bot de verdade dentro do Wine.
set -uo pipefail

TAR="$(ls dist/MT5Bot-*-wine.tar.gz | head -1)"
WORK="$(mktemp -d)"
fail() { echo "FALHOU: $*"; exit 1; }
ok() { echo "ok  $*"; }

tar -xzf "$TAR" -C "$WORK" || fail "extrair $TAR"
ok "pacote extraido: $(du -sh "$TAR" | cut -f1)"

export MT5BOT_WINEPREFIX="$WORK/prefix" MT5BOT_BIN_DIR="$WORK/bin"
bash "$WORK/install.sh" --no-mt5 > "$WORK/install.log" 2>&1 || { cat "$WORK/install.log"; fail "install.sh"; }
ok "install.sh --no-mt5"

export WINEPREFIX="$WORK/prefix" WINEDEBUG=-all
# Sem dialogos de instalacao do Mono/Gecko (ninguem clica no CI) e um wineserver
# persistente, para cada chamada nao recriar o ambiente do zero (issue #47).
export WINEDLLOVERRIDES="mscoree,mshtml=;winemenubuilder.exe=d"
wineserver -p 900
# Sem depurador automatico: um crash no Wine deve falhar na hora, e nao deixar o
# winedbg parado ate o timeout (foi assim que a issue #47 se escondeu).
wine reg delete 'HKLM\Software\Microsoft\Windows NT\CurrentVersion\AeDebug' /v Debugger /f >/dev/null 2>&1 || true
ok "$(wine --version)"
APP="$WORK/prefix/drive_c/MT5Bot"
[ -f "$APP/python/python.exe" ] && [ -f "$APP/maestro/maestro.exe" ] && [ -x "$WORK/bin/mt5bot" ] || fail "arquivos instalados"
ok "MT5Bot copiado para o prefixo e comando mt5bot criado"

# Roda o Python embutido com limite de tempo e mostra codigo de saida e duracao.
pyrun() {
    local t0=$SECONDS
    out="$(cd "$APP" && timeout "$1" wine python/python.exe "${@:2}" 2>&1)"; rc=$?
    echo "    (rc=$rc em $((SECONDS - t0))s)"
}
pyrun 180 -c "print('py', 6*7)"
echo "$out" | grep -q "py 42" || { echo "$out" | tail -20; WINEDEBUG=err+all pyrun 120 -c "print(1)"; echo "$out" | tail -40; fail "Python embutido inicia no Wine"; }
ok "Python embutido inicia no Wine"
pyrun 300 -c "import numpy, pandas; print('np', numpy.__version__, 'pd', pandas.__version__)"
echo "$out" | grep -q "^np " || { echo "$out" | tail -30; fail "numpy e pandas no Wine"; }
ok "$(echo "$out" | grep '^np ' | tr -d '')"

IMPORT_ALL="import importlib,pkgutil,mt5bot,interfaces,xgboost,pandas,MetaTrader5; n=[m.name for p in (mt5bot,interfaces) for m in pkgutil.walk_packages(p.__path__,p.__name__+'.')]; [importlib.import_module(x) for x in n]; print(len(n),'modulos ok')"
pyrun 600 -c "$IMPORT_ALL"
echo "$out" | grep -q "modulos ok" || { echo "$out" | tail -20; fail "Python embutido no Wine importa todos os modulos"; }
ok "Python embutido no Wine: $(echo "$out" | grep 'modulos ok' | tr -d '\r')"

out="$(cd "$APP" && timeout 600 wine python/python.exe 'C:\MT5Bot\tools\quant_runner.py' --once --plain 2>&1)"
echo "$out" | grep -Eq "Traceback|ImportError|ModuleNotFoundError" && { echo "$out" | tail -20; fail "Modo Quant sem erro de importacao"; }
echo "$out" | grep -Eq "Falha ao conectar no MT5|Quant runner conectado" || { echo "$out" | tail -20; fail "Modo Quant responde"; }
ok "Modo Quant roda no Wine (sem terminal MT5: explica e sai)"

out="$(timeout 600 "$WORK/bin/mt5bot" config 2>&1)"
echo "$out" | grep -q "ROTAS QUANT" || { echo "$out" | tail -20; fail "mt5bot config"; }
ok "comando mt5bot -> bot.bat no Wine"

out="$(cd "$APP" && timeout 120 wine maestro/maestro.exe --version 2>&1)"
echo "$out" | grep -q "MT5Bot v" || { echo "$out"; fail "Maestro no Wine"; }
ok "Maestro no Wine: $(echo "$out" | tr -d '\r')"

wineserver -k || true
echo "Smoke Wine: tudo verde."
