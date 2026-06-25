# Copia avisos legales al portable Windows (dist\GaleriaAYN\).
param(
    [string]$PortableDir = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
if (-not $PortableDir) {
    $PortableDir = Join-Path $Root "dist\GaleriaAYN"
}

if (-not (Test-Path $PortableDir)) {
    Write-Error "No existe la carpeta portable: $PortableDir"
}

Write-Host "== Avisos legales en portable ==" -ForegroundColor Cyan

Copy-Item -Force (Join-Path $Root "LICENSE") (Join-Path $PortableDir "LICENSE.txt")
Copy-Item -Force (Join-Path $Root "docs\THIRD_PARTY_NOTICES.md") (Join-Path $PortableDir "LEGAL-THIRD_PARTY.md")
Copy-Item -Force (Join-Path $Root "packaging\legal\COPYING.LGPLv2.1.txt") (Join-Path $PortableDir "COPYING.LGPLv2.1.txt")

$FfmpegLegal = Join-Path $PortableDir "tools\ffmpeg\licenses"
if (Test-Path $FfmpegLegal) {
    Write-Host "Licencias ffmpeg ya en: $FfmpegLegal" -ForegroundColor DarkGray
} else {
    Write-Warning "No se encontró tools\ffmpeg\licenses\ — ejecuta fetch-ffmpeg-windows.ps1 antes del build."
}

Write-Host "Legal listo en: $PortableDir" -ForegroundColor Green
