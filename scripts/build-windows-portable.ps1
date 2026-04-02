# Genera carpeta portable dist\GaleriaAYN\ (Windows x64).
# Ejecutar en PowerShell desde la raíz del repositorio, en una máquina Windows con Python 3.10+.
# Requisitos: Node (npm), pip install pyinstaller pillow pywebview

$ErrorActionPreference = "Stop"
# Este script vive en scripts/ — raíz del repo es el directorio padre
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "== webui (producción) ==" -ForegroundColor Cyan
Push-Location webui
if (-not (Test-Path "node_modules")) { npm ci }
npm run build
Pop-Location

if (-not (Test-Path "webui\dist\index.html")) {
  Write-Error "No se generó webui/dist. Revisa el build de npm."
}

Write-Host "== PyInstaller ==" -ForegroundColor Cyan
python -m pip install --upgrade pip
pip install pyinstaller pillow pywebview

python -m PyInstaller --clean --noconfirm "$Root\GaleriaAYN.spec"

Write-Host ""
Write-Host "Listo: $Root\dist\GaleriaAYN\GaleriaAYN.exe" -ForegroundColor Green
Write-Host "Comprime la carpeta dist\GaleriaAYN en un .zip para compartir." -ForegroundColor Green
