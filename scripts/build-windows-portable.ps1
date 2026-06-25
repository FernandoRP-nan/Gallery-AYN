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

# Evita mezclar un .exe nuevo con assets viejos en caché de PyInstaller
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }

Write-Host "== PyInstaller ==" -ForegroundColor Cyan
python -m pip install --upgrade pip
pip install pyinstaller pillow pywebview

python -m PyInstaller --clean --noconfirm "$Root\GaleriaAYN.spec"

Write-Host "== ffmpeg (portable) ==" -ForegroundColor Cyan
& "$Root\scripts\fetch-ffmpeg-windows.ps1"
$DestFfmpeg = Join-Path $Root "dist\GaleriaAYN\tools\ffmpeg"
New-Item -ItemType Directory -Force -Path $DestFfmpeg | Out-Null
Copy-Item -Force (Join-Path $Root "tools\ffmpeg\ffmpeg.exe") (Join-Path $DestFfmpeg "ffmpeg.exe")
Copy-Item -Force (Join-Path $Root "tools\ffmpeg\ffprobe.exe") (Join-Path $DestFfmpeg "ffprobe.exe")

Write-Host ""
Write-Host "Listo: $Root\dist\GaleriaAYN\GaleriaAYN.exe" -ForegroundColor Green
Write-Host "Comprime la carpeta dist\GaleriaAYN en un .zip para compartir." -ForegroundColor Green
