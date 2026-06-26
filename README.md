# Organizador Multimedia (Galería AYN)

Aplicación de escritorio para **explorar, organizar y mover** colecciones de fotos y vídeos en **Linux (Fedora KDE)** y **Windows**. Combina un backend en **Python** con una interfaz **Svelte + Vite** embebida en **PyWebView** (o, opcionalmente, **Qt WebEngine** en KDE).

## Qué hace

### Galería

- Miniaturas **progresivas LQ → HQ** (rápidas al abrir, nítidas en segundo plano).
- **Paginación** o **scroll sin límite** con carga por tandas, ventana deslizante en RAM y **índice en disco** (reapertura rápida de carpetas grandes).
- **Scroll virtual** en rejilla y en **masonry** (muro por proporción real de cada imagen).
- **Masonry compacto** (opcional en Ajustes): sin hueco vertical entre filas.
- Vistas: subcarpetas recursivas, **agrupar por carpeta**, **línea de tiempo** (meses/días), orden multi-criterio.
- **Rail lateral de fechas**: salto instantáneo; prefetch al hacer scroll y al volver hacia arriba.
- Barra de **marcadores** y carpetas recientes/ancladas.

### Modo edición

- Selección múltiple (clic, rango, Ctrl).
- **Destinos** en árbol (carpetas y subcarpetas); barra flotante y arrastrar/soltar.
- Mover archivos sin salir de la galería; menú contextual (copiar ruta/miniatura, eliminar, metadatos).

### Vista previa y pantalla completa

- Panel lateral de **vista previa** (imagen o vídeo).
- **Zoom** a pantalla completa con carrusel, mini-mapa y rotación/recorte (Pillow; SVG sin recorte).
- **Vídeo**: perfiles de transcodificación (turbo/rápido/calidad), aceleración HW opcional, autoreproducir configurable.

### Organización e «Desorden»

- **Organizador** por reglas (fechas, tipos, CBZ, carpetas destino, etc.) con opción de **agrupar similares por contenido visual** (aHash).
- Pestaña **Desorden**: clusters de fotos sueltas, similitud «más como esta», sugerencias al **final de la galería** (desde carpeta desorden → carpeta actual).

### Ajustes y rendimiento

- Modal de ajustes por pestañas: **Apariencia**, **Miniaturas**, **Organización** (destinos + marcadores), **Sugerencias**, **Vídeo**, **Avanzado** (workers, overscan, ventana deslizante), **Atajos**, **Depuración**.
- Temas: Medianoche, Océano, Brasas, Bosque, Papel claro.
- Presets de rendimiento para PCs modestos o potentes (p. ej. Ryzen + 32 GB).
- **Panel de depuración** opcional (scroll, saltos, tandas LQ/HQ) para diagnosticar carpetas enormes.

Los ajustes se guardan en `~/.config/organizador_multimedia/settings.json` (Linux) o el equivalente en Windows.

## Requisitos

| Componente | Versión / notas |
|------------|-----------------|
| **Python** | ≥ 3.10 |
| **Pillow** | generación de miniaturas |
| **pywebview** | ventana con interfaz web embebida |
| **Node.js + npm** | solo para desarrollar o compilar la UI (`webui/`) |
| **PyQt6 + PyQt6-WebEngine + qtpy** | opcional, recomendado en Fedora KDE (`pip install -e ".[qt]"`) |
| **ffmpeg / ffprobe** | opcional; transcodificación y diagnóstico de vídeo en el visor |

### Dependencias del sistema (Fedora, orientativo)

```bash
sudo dnf install python3 python3-pip nodejs npm
# Opcional, para Qt WebEngine:
sudo dnf install python3-qt6 python3-qt6-webengine
```

## Instalación

### 1. Clonar e instalar Python

```bash
git clone https://github.com/FernandoRP-nan/Organizador-Fedora-KDE.git
cd Organizador-Fedora-KDE

python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -e ".[qt]"
```

> Sin `[qt]` también funciona con el motor GTK/WebKit de pywebview; en KDE suele ir mejor Qt (`ORGANIZADOR_PREFER_QT=1`).

### 2. Compilar la interfaz web

```bash
cd webui
npm ci
npm run build
cd ..
```

La aplicación carga `webui/dist/index.html` si existe (también se versiona en el repo para ejecutar sin Node).

### 3. Ejecutar

```bash
python3 organizador_multimedia.py
# o
python3 -m org_multimedia
# o, tras pip install -e:
organizador
```

Con Qt WebEngine explícito:

```bash
ORGANIZADOR_PREFER_QT=1 python3 -m org_multimedia
```

## Windows

En Windows el flujo es el mismo (Python + build de `webui/`); el **.exe portable** solo se genera **en un PC Windows x64** (PyInstaller no cruza desde Linux sin entorno extra).

### Ejecutar desde código (desarrollo o uso local)

En **PowerShell** desde la raíz del repositorio:

```powershell
git clone https://github.com/FernandoRP-nan/Organizador-Fedora-KDE.git
cd Organizador-Fedora-KDE

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -e .

cd webui
npm ci
npm run build
cd ..

python organizador_multimedia.py
```

| Componente | Notas |
|------------|--------|
| **Python** | 3.10 o superior |
| **Node.js + npm** | Para compilar la UI |
| **WebView2 Runtime** | Lo usa PyWebView |
| **ffmpeg / ffprobe** | Opcional; `tools\ffmpeg\` o PATH |

Guía completa del portable: **[docs/windows-portable.md](docs/windows-portable.md)**.

### Compilar portable (.exe)

```powershell
.\scripts\build-windows-portable.ps1
```

Salida: **`dist\GaleriaAYN\`** → comprimir **toda la carpeta** en un `.zip`.

CI: workflow [`.github/workflows/build-windows-portable.yml`](.github/workflows/build-windows-portable.yml).

### Integración en Fedora KDE (menú y autostart)

Ver [docs/desktop-fedora-kde.md](docs/desktop-fedora-kde.md):

```bash
./scripts/install-desktop-kde.sh
./scripts/install-desktop-kde.sh --autostart
```

## Desarrollo de la UI

```bash
cd webui
npm install
npm run dev
```

En otra terminal, con la app Python (Vite en `http://127.0.0.1:5173` si no hay `webui/dist`):

```bash
source .venv/bin/activate
python3 organizador_multimedia.py
```

Detalle en [webui/README.md](webui/README.md).

## Estructura del proyecto

```
organizador_multimedia.py   # Punto de entrada
org_multimedia/
  api/                      # Bridge PyWebView ↔ Python (galería, destinos, desorden…)
  core/                     # Ajustes, rutas, miniaturas, transcodificación, índice en disco
  ia/                       # Similitud visual (aHash) para desorden y organizador
  app_webview.py            # Arranque PyWebView + servidor de medios local
webui/                      # Frontend Svelte + Vite (fuente en src/, build en dist/)
docs/                       # Documentación adicional
scripts/                    # KDE, Windows portable, ffmpeg
packaging/                  # Entrada PyInstaller Windows
```

## Documentación adicional

- [Integración Fedora KDE](docs/desktop-fedora-kde.md)
- [Roadmap de funcionalidades](docs/ROADMAP-FEATURES.md)
- [Build portable Windows](docs/windows-portable.md)
- [Avisos legales y terceros](docs/THIRD_PARTY_NOTICES.md)

## Licencia

Este proyecto se distribuye bajo la licencia **MIT**. Ver [LICENSE](LICENSE).

### Distribución del .exe portable (Windows)

Si compartes el zip de `dist\GaleriaAYN\`, incluye los archivos legales del build (`LICENSE.txt`, `LEGAL-THIRD_PARTY.md`, licencias de ffmpeg). Ver **[docs/THIRD_PARTY_NOTICES.md](docs/THIRD_PARTY_NOTICES.md)** y **[docs/windows-portable.md](docs/windows-portable.md)**.

### Dependencias y binarios de terceros

- **Python / npm**: Pillow, pywebview, Svelte, Vite, etc. (MIT, Apache-2.0, BSD…).
- **PyQt6** (opcional, extra `[qt]`): licencia **GPL v3** de Qt — si enlazas o distribuyes con Qt, aplica la GPL a tu distribución.
- **ffmpeg** (opcional / portable Windows): licencia **LGPL v2.1+** según build; incluye aviso y enlace al código fuente si redistribuyes el binario.
