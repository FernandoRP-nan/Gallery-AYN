#!/usr/bin/env bash
# Instala entrada de menú (y opcionalmente inicio automático) en Fedora KDE.
# Uso: ./scripts/install-desktop-kde.sh
#      ./scripts/install-desktop-kde.sh --autostart
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Ruta absoluta canónica (KDE/systemd rechazan Path/WorkingDirectory relativos o mal formados).
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
LAUNCHER="$REPO_ROOT/scripts/organizador-launch.sh"

if [[ ! "$REPO_ROOT" =~ ^/ ]]; then
  echo "Error: no se pudo resolver la ruta absoluta del repositorio: $REPO_ROOT" >&2
  exit 1
fi

chmod +x "$LAUNCHER" 2>/dev/null || true

DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
AUTOSTART_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"
mkdir -p "$DESKTOP_DIR" "$AUTOSTART_DIR"

DESKTOP_ID="org.nanrroti.galeria-ayn.desktop"
OUT="$DESKTOP_DIR/$DESKTOP_ID"

# Sin Path=/WorkingDirectory= en el .desktop: Plasma 6 valida WorkingDirectory y exige ruta absoluta;
# fijamos el cwd con env -C (coreutils) para rutas con espacios.
if ! env -C / true 2>/dev/null; then
  echo "Error: hace falta «env» con soporte -C (coreutils reciente). En Fedora suele venir por defecto." >&2
  exit 1
fi

# Rutas entre comillas por si el clon tiene espacios en el nombre de carpeta.
cat >"$OUT" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Galería AYN
GenericName=Galería y organización de archivos
Comment=Vista de galería y organización multimedia (PyWebView + Qt)
Exec=env -C "$REPO_ROOT" "$LAUNCHER"
Icon=folder-pictures
Terminal=false
Categories=Graphics;AudioVideo;Viewer;
Keywords=gallery;images;organizer;fotos;
StartupNotify=true
EOF

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
fi

echo "Entrada de menú instalada: $OUT"
echo "Busca «Galería AYN» en el lanzador de aplicaciones (Kickoff / KRunner)."

if [[ "${1:-}" == "--autostart" ]]; then
  cp -f "$OUT" "$AUTOSTART_DIR/$DESKTOP_ID"
  echo "Inicio automático activado: $AUTOSTART_DIR/$DESKTOP_ID"
else
  echo "Para arrancar al iniciar sesión: $0 --autostart"
fi
