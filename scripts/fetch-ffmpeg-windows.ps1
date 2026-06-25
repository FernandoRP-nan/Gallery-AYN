# Descarga ffmpeg/ffprobe (build essentials) para empaquetar en el portable Windows.
# Salida: tools\ffmpeg\ffmpeg.exe y ffprobe.exe
param(
    [string]$OutDir = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
if (-not $OutDir) {
    $OutDir = Join-Path $Root "tools\ffmpeg"
}

$ZipUrl = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
$Staging = Join-Path $Root "tools\ffmpeg-download"
$ZipPath = Join-Path $Staging "ffmpeg-essentials.zip"

Write-Host "== Descargando ffmpeg essentials ==" -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $Staging | Out-Null
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

if (-not (Test-Path $ZipPath)) {
    Invoke-WebRequest -Uri $ZipUrl -OutFile $ZipPath -UseBasicParsing
}

$ExtractDir = Join-Path $Staging "extract"
if (Test-Path $ExtractDir) { Remove-Item -Recurse -Force $ExtractDir }
Expand-Archive -Path $ZipPath -DestinationPath $ExtractDir -Force

$BinDir = Get-ChildItem -Path $ExtractDir -Recurse -Directory -Filter "bin" |
    Where-Object { Test-Path (Join-Path $_.FullName "ffmpeg.exe") } |
    Select-Object -First 1
if (-not $BinDir) {
    Write-Error "No se encontró ffmpeg.exe dentro del zip descargado."
}

Copy-Item -Force (Join-Path $BinDir.FullName "ffmpeg.exe") (Join-Path $OutDir "ffmpeg.exe")
Copy-Item -Force (Join-Path $BinDir.FullName "ffprobe.exe") (Join-Path $OutDir "ffprobe.exe")

# Licencias LGPL del build (obligatorio si redistribuyes los .exe)
$BuildRoot = $BinDir.Parent
$LegalDest = Join-Path $OutDir "licenses"
New-Item -ItemType Directory -Force -Path $LegalDest | Out-Null
foreach ($name in @("LICENSE", "COPYING.LGPLv2.1", "COPYING.LGPLv3", "COPYING.GPLv2", "COPYING.GPLv3")) {
    $src = Join-Path $BuildRoot.FullName $name
    if (Test-Path $src) {
        Copy-Item -Force $src (Join-Path $LegalDest $name)
    }
}
$NestedLicenses = Join-Path $BuildRoot.FullName "licenses"
if (Test-Path $NestedLicenses) {
    Copy-Item -Force -Recurse (Join-Path $NestedLicenses "*") $LegalDest -ErrorAction SilentlyContinue
}

Write-Host "ffmpeg listo en: $OutDir" -ForegroundColor Green
