<#
.SYNOPSIS
  Roda localmente os mesmos passos do CI do GitHub (spec 001 FR-6).

.DESCRIPTION
  Lint (ruff) -> pytest -> Maestro (go vet, go test, build para Windows).
  Para no primeiro passo que falhar e devolve codigo de saida != 0.
  Uso:  powershell -ExecutionPolicy Bypass -File tools\ci.ps1      (ou: bot.bat ci)
#>
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Step([string]$name, [scriptblock]$cmd) {
    Write-Host ""
    Write-Host "==> $name" -ForegroundColor DarkYellow
    & $cmd
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FALHOU: $name (codigo $LASTEXITCODE)" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

Step "Lint (ruff)" { python -m ruff check . }
Step "Testes Python (pytest + cobertura)" { python -m coverage run -m pytest -q }
Step "Cobertura (piso no pyproject)" { python -m coverage report --format=total }
Step "Pacote (wheel + import)" { python tools/check_wheel.py }

Push-Location (Join-Path $root "maestro")
try {
    Step "Maestro: go vet" { go vet ./... }
    Step "Maestro: go test" { go test ./... }
    Step "Maestro: build Windows" { $env:GOOS = "windows"; $env:GOARCH = "amd64"; go build -o $env:TEMP\maestro-ci.exe . }
} finally {
    Remove-Item Env:GOOS, Env:GOARCH -ErrorAction SilentlyContinue
    Pop-Location
}

Write-Host ""
Write-Host "CI local: tudo verde." -ForegroundColor Green
exit 0
