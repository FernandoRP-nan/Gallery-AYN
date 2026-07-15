#!/usr/bin/env bash
# Genera notas de release: bloque portable + changelog entre tags.
set -euo pipefail

TAG="${1:?Uso: generate-release-notes.sh <tag> [zip-name]}"
ZIP_NAME="${2:-GaleriaAYN-${TAG}-portable.zip}"
REPO="${GITHUB_REPOSITORY:-FernandoRP-nan/Gallery-AYN}"

previous_tag() {
  git tag -l 'v*' --sort=v:refname | awk -v target="$TAG" '$0 == target { exit } { prev = $0 } END { print prev }'
}

PREV="$(previous_tag)"

cat <<EOF
## Galería AYN — portable Windows (x64)

Descarga **\`${ZIP_NAME}\`**, extrae **toda la carpeta** y ejecuta \`GaleriaAYN.exe\`.

Requisitos en el PC destino: Windows 10/11 64 bits, WebView2 y .NET Framework 4.7.2+.
Si el zip viene de internet: Propiedades → **Desbloquear** antes de extraer.

Guía completa: [docs/windows-portable.md](https://github.com/${REPO}/blob/${TAG}/docs/windows-portable.md)

## Changelog

EOF

if [[ -z "${PREV}" ]]; then
  cat <<'CHANGELOG'
Primera versión estable de Galería AYN.

### Galería y navegación
- Interfaz web embebida (PyWebView) con galería virtual, masonry y scroll sin límite
- Rail de fechas, precarga progresiva al subir/bajar y saltos fluidos por scrollbar
- Índice en disco, miniaturas LQ/HQ con crossfade y caché en memoria
- Agrupación por carpeta, línea de tiempo y sugerencias desde carpeta desorden
- Paginación configurable, ordenación y panel de procesos en curso

### Vista previa y pantalla completa
- Panel lateral con zoom, pan y carrusel de miniaturas
- Transcodificación progresiva de vídeo con perfiles y autoreproducir
- Modo edición con selección, destinos, arrastre y vista previa de carpetas destino
- Visor fullscreen con vídeo, destinos flotantes y mover sin recargar la galería

### Destinos, marcadores y organización
- Gestores de destinos y marcadores en ajustes
- Mover selección con actualización optimista (delta) y rollback
- Carpetas ancladas, historial de navegación y rutas recientes

### Apariencia y ajustes
- Temas, escala de miniaturas, calidad LQ/HQ y pestañas de ajustes reorganizadas
- Masonry compacto, etiquetas en miniaturas y barra de ruta

### Distribución Windows
- Build portable con PyInstaller, ffmpeg empaquetado y CI en GitHub Actions
- Licencia MIT, avisos legales y publicación automática en Releases al etiquetar `v*`
CHANGELOG
  printf '\n\n'
  echo "**Full Changelog**: https://github.com/${REPO}/commits/${TAG}"
else
  git log "${PREV}..${TAG}" --pretty=format:'- %s' --no-merges --reverse
  printf '\n\n'
  echo "**Full Changelog**: https://github.com/${REPO}/compare/${PREV}...${TAG}"
fi
