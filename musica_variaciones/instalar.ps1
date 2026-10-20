$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Ace = Join-Path $Root "ACE-Step-1.5"

if (-not (Test-Path -LiteralPath $Ace)) {
    git clone --depth 1 https://github.com/ACE-Step/ACE-Step-1.5.git $Ace
}

Push-Location $Ace
try {
    uv sync
} finally {
    Pop-Location
}

Write-Host "Instalacion terminada. Abre 'Abrir Variador de Musica.cmd'."
