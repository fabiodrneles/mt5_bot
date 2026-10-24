<#
.SYNOPSIS
  Smoke test do instalador (spec 002 AC-2): instala em silencio, roda o que foi
  instalado e desinstala, conferindo que os dados do usuario sobrevivem (FR-7).
#>
param([Parameter(Mandatory = $true)][string]$Setup)
$ErrorActionPreference = "Stop"

function Check([bool]$ok, [string]$msg) {
    if (-not $ok) { Write-Host "FALHOU: $msg" -ForegroundColor Red; exit 1 }
    Write-Host "ok  $msg" -ForegroundColor Green
}

# Roda um processo com tempo limite e devolve (codigo, saida). O MT5 nao existe
# no runner, entao nada pode ficar travado esperando por ele.
function Run([string]$exe, [string[]]$argv, [int]$timeout = 180) {
    $out = Join-Path $env:TEMP ("smoke-" + [guid]::NewGuid() + ".txt")
    $p = Start-Process $exe -ArgumentList $argv -NoNewWindow -PassThru `
        -RedirectStandardOutput $out -RedirectStandardError "$out.err"
    if (-not $p.WaitForExit($timeout * 1000)) { $p.Kill(); throw "tempo esgotado: $exe $argv" }
    $text = (Get-Content $out, "$out.err" -Raw -ErrorAction SilentlyContinue) -join "`n"
    return @($p.ExitCode, $text)
}

$sizeMB = [math]::Round((Get-Item $Setup).Length / 1MB, 1)
Check ($sizeMB -le 200) "instalador com $sizeMB MB (limite 200 MB, NFR-1)"

$dir = Join-Path $env:TEMP "MT5Bot-smoke"
$p = Start-Process $Setup -ArgumentList "/VERYSILENT", "/SUPPRESSMSGBOXES", "/CURRENTUSER", "/NORESTART", "/DIR=`"$dir`"" -Wait -PassThru
Check ($p.ExitCode -eq 0) "instalacao silenciosa sem administrador (exit $($p.ExitCode))"

$py = Join-Path $dir "python\python.exe"
foreach ($f in @($py, "$dir\maestro\maestro.exe", "$dir\bot.bat", "$dir\mt5bot\core\config.py", "$dir\models")) {
    Check (Test-Path $f) "instalado: $f"
}

$importAll = "import importlib,pkgutil,mt5bot,interfaces,xgboost,pandas,MetaTrader5;" +
    "n=[m.name for p in (mt5bot,interfaces) for m in pkgutil.walk_packages(p.__path__,p.__name__+'.')];" +
    "[importlib.import_module(x) for x in n];print(len(n),'modulos ok')"
$r = Run $py @("-c", "`"$importAll`"")
Check ($r[0] -eq 0) "Python embutido importa todos os modulos: $($r[1].Trim())"

$r = Run $py @("$dir\tools\quant_runner.py", "--once", "--plain")
Check ($r[1] -notmatch "Traceback|ImportError|ModuleNotFoundError") "Modo Quant roda sem erro de importacao"
Check (($r[0] -eq 0) -or ($r[1] -match "Falha ao conectar no MT5")) "Modo Quant: conecta ou explica que o MT5 nao esta aberto (exit $($r[0]))"

$r = Run "$dir\maestro\maestro.exe" @("--version")
Check ($r[1] -match "MT5Bot v\d") "Maestro: $($r[1].Trim())"

$r = Run "cmd.exe" @("/c", "`"$dir\bot.bat`" config")
Check ($r[0] -eq 0 -and $r[1] -match "ROTAS QUANT") "bot.bat config usa o Python embutido (exit $($r[0]))"

# FR-7: desinstalacao silenciosa preserva os dados do usuario.
$data = Join-Path $env:APPDATA "mt5bot"
New-Item -ItemType Directory -Force $data | Out-Null
Set-Content (Join-Path $data "smoke-marker.txt") "nao apagar"
$p = Start-Process "$dir\unins000.exe" -ArgumentList "/VERYSILENT", "/SUPPRESSMSGBOXES" -Wait -PassThru
Start-Sleep -Seconds 3
Check ($p.ExitCode -eq 0) "desinstalacao silenciosa (exit $($p.ExitCode))"
Check (-not (Test-Path "$dir\bot.bat")) "programa removido"
Check (Test-Path (Join-Path $data "smoke-marker.txt")) "dados do usuario preservados"

Write-Host "Smoke do instalador: tudo verde." -ForegroundColor Green
