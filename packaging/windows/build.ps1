<#
.SYNOPSIS
  Gera o instalador Windows do MT5Bot (spec 002 FR-2, D2).

.DESCRIPTION
  1. Baixa o Python embutido oficial (python.org) e configura o ._pth.
  2. Instala as dependencias de runtime dentro dele (wheels win_amd64).
  3. Compila o Maestro (Go).
  4. Copia so os arquivos versionados no git (nada de lixo local).
  5. Compila o instalador com o Inno Setup (ISCC).

  Uso:  powershell -ExecutionPolicy Bypass -File packaging\windows\build.ps1
  Saida: dist\MT5Bot-Setup-<versao>.exe
#>
param(
    [string]$PythonVersion = "3.12.10",
    [string]$OutDir = "dist"
)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $root

$version = (Select-String -Path pyproject.toml -Pattern '^version = "(.+)"').Matches[0].Groups[1].Value
$stage = Join-Path $root "build\installer\MT5Bot"
Write-Host "MT5Bot $version -> $stage" -ForegroundColor DarkYellow
if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
New-Item -ItemType Directory -Force $stage | Out-Null

# 1) Python embutido -----------------------------------------------------------
$pyDir = Join-Path $stage "python"
$zip = Join-Path $env:TEMP "python-$PythonVersion-embed-amd64.zip"
if (-not (Test-Path $zip)) {
    Invoke-WebRequest "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-embed-amd64.zip" -OutFile $zip
}
Expand-Archive $zip -DestinationPath $pyDir
$tag = ($PythonVersion.Split(".")[0..1] -join "")
# ._pth: stdlib, site-packages e a pasta da aplicacao (..) para "python -m interfaces.brain_worker".
@("python$tag.zip", ".", "Lib\site-packages", "..", "import site") |
    Set-Content -Encoding ascii (Join-Path $pyDir "python$tag._pth")

# 2) Dependencias de runtime ------------------------------------------------------
# xgboost-cpu: mesmo modulo `xgboost`, sem o runtime de GPU (2 MB em vez de >100 MB).
$deps = @("MetaTrader5>=5.0.45", "pandas>=2.0", "numpy>=1.24", "pytz>=2023.3", "xgboost-cpu>=2.1", "psutil>=5.9")
python -m pip install --disable-pip-version-check --no-compile -q `
    --only-binary=:all: --platform win_amd64 --python-version ($PythonVersion.Split(".")[0..1] -join ".") --implementation cp `
    --target (Join-Path $pyDir "Lib\site-packages") @deps
if ($LASTEXITCODE -ne 0) { throw "pip falhou" }

# 3) Maestro ----------------------------------------------------------------------
New-Item -ItemType Directory -Force (Join-Path $stage "maestro") | Out-Null
Push-Location maestro
try {
    $env:GOOS = "windows"; $env:GOARCH = "amd64"
    go build -trimpath -ldflags "-s -w" -o (Join-Path $stage "maestro\maestro.exe") .
    if ($LASTEXITCODE -ne 0) { throw "go build falhou" }
} finally { Pop-Location }

# 4) Arquivos versionados da aplicacao ------------------------------------------------
$files = git ls-files mt5bot interfaces tools models memoria bot.bat mt5bot.bat pyproject.toml `
    README.md README.en.md LICENSE CHANGELOG.md .env.example
foreach ($f in $files) {
    if ($f -like "tools/quant_research/*") { continue }  # pesquisa: so no repositorio
    $dest = Join-Path $stage $f
    New-Item -ItemType Directory -Force (Split-Path $dest) | Out-Null
    Copy-Item $f $dest
}

# 5) Inno Setup -------------------------------------------------------------------------
$iscc = @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe") |
    Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { throw "Inno Setup 6 nao encontrado (instale: choco install innosetup)" }
New-Item -ItemType Directory -Force $OutDir | Out-Null
& $iscc /Qp "/DAppVersion=$version" "/DStageDir=$stage" "/DRepoRoot=$root" "/O$(Resolve-Path $OutDir)" `
    (Join-Path $PSScriptRoot "mt5bot.iss")
if ($LASTEXITCODE -ne 0) { throw "ISCC falhou" }

$setup = Join-Path (Resolve-Path $OutDir) "MT5Bot-Setup-$version.exe"
$mb = [math]::Round((Get-Item $setup).Length / 1MB, 1)
Write-Host "OK: $setup ($mb MB)" -ForegroundColor Green
