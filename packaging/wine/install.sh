#!/usr/bin/env bash
# MT5Bot para Linux e macOS via Wine — EXPERIMENTAL (spec 002 FR-6, decisao D1).
#
# A biblioteca oficial MetaTrader5 do Python so existe para Windows. Por isso o
# MT5Bot roda INTEIRO dentro de um prefixo Wine, junto com o terminal MT5:
# o Python embutido, o Maestro e o MT5 conversam como se estivessem no Windows.
#
# Uso:  bash install.sh            # prepara o prefixo, baixa e abre o instalador do MT5
#       bash install.sh --no-mt5   # so instala o MT5Bot (o MT5 voce instala depois)
# Depois:  mt5bot setup | mt5bot quant | mt5bot dashboard | mt5bot maestro | mt5bot diagnose
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PREFIX="${MT5BOT_WINEPREFIX:-$HOME/.mt5bot-wine}"
BIN_DIR="${MT5BOT_BIN_DIR:-$HOME/.local/bin}"
MT5_URL="https://download.mql5.com/cdn/web/metaquotes.software.corp/mt5/mt5setup.exe"
WITH_MT5=1
for arg in "$@"; do
    case "$arg" in
        --no-mt5) WITH_MT5=0 ;;
        -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    esac
done

say() { printf '\033[38;5;208m==>\033[0m %s\n' "$*"; }

if ! command -v wine >/dev/null 2>&1; then
    echo "Wine nao encontrado."
    echo "  Ubuntu/Debian: sudo apt install wine64   (ou: sudo apt install wine)"
    echo "  Fedora:        sudo dnf install wine"
    echo "  macOS:         brew install --cask wine-stable"
    exit 1
fi
if [ ! -d "$HERE/MT5Bot" ]; then
    echo "Pasta MT5Bot nao encontrada ao lado deste script. Extraia o .tar.gz inteiro."
    exit 1
fi

export WINEPREFIX="$PREFIX" WINEDEBUG=-all
if [ ! -d "$PREFIX" ]; then
    say "Criando o prefixo Wine em $PREFIX (pode levar alguns minutos)"
    wineboot --init >/dev/null 2>&1 || true
fi

DEST="$PREFIX/drive_c/MT5Bot"
say "Copiando o MT5Bot para $DEST"
mkdir -p "$DEST"
cp -R "$HERE/MT5Bot/." "$DEST/"

say "Criando o comando 'mt5bot' em $BIN_DIR"
mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/mt5bot" <<EOF
#!/usr/bin/env bash
# Gerado pelo install.sh do MT5Bot (experimental, via Wine).
export WINEPREFIX="$PREFIX" WINEDEBUG=-all
if [ "\${1:-}" = "maestro" ]; then
    shift
    exec wine cmd /c 'C:\\MT5Bot\\mt5bot.bat' "\$@"
fi
exec wine cmd /c 'C:\\MT5Bot\\bot.bat' "\$@"
EOF
chmod +x "$BIN_DIR/mt5bot"

if [ "$WITH_MT5" = 1 ]; then
    say "Baixando o instalador oficial do MetaTrader 5"
    tmp="$(mktemp -d)"
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL -o "$tmp/mt5setup.exe" "$MT5_URL"
    else
        wget -q -O "$tmp/mt5setup.exe" "$MT5_URL"
    fi
    say "Abrindo o instalador do MT5 no Wine: conclua a instalacao e faca login na corretora"
    wine "$tmp/mt5setup.exe" || true
fi

case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *) echo; echo "Adicione $BIN_DIR ao PATH (ex.: echo 'export PATH=\"$BIN_DIR:\$PATH\"' >> ~/.bashrc)";;
esac
echo
say "Pronto (EXPERIMENTAL). Abra o MT5 no Wine, faca login e rode: mt5bot setup"
echo "    O MT5 fica em: $PREFIX/drive_c/Program Files/MetaTrader 5/terminal64.exe"
echo "    Abrir o MT5:   WINEPREFIX=$PREFIX wine \"C:\\\\Program Files\\\\MetaTrader 5\\\\terminal64.exe\""
