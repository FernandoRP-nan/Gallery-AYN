# Organizador Multimedia (Galería AYN)

Aplicación de escritorio para **explorar, organizar y mover** colecciones de fotos y vídeos en Linux (Fedora KDE) y Windows. Combina un backend en **Python** con una interfaz web embebida (**Svelte + Vite**) dentro de **PyWebView** (o Qt WebEngine).

## Qué hace

- **Galería** de imágenes y vídeos con miniaturas progresivas (baja calidad → alta calidad), paginación o scroll ilimitado y ajuste de tamaño de miniaturas.
- **Modo edición**: seleccionar archivos y moverlos a **carpetas destino** (con agrupación en carpetas y barra de acceso rápido).
- **Marcadores** de rutas frecuentes, también organizables en carpetas.
- **Vista previa** lateral, visor a pantalla completa, rotación y recorte básico de imágenes.
- **Organizador** por reglas (fechas, carpetas destino, duplicados, etc.).
- Vistas avanzadas: subcarpetas recursivas, agrupar por carpeta, línea de tiempo, temas de color.

Los ajustes se guardan en `~/.config/organizador_multimedia/settings.json`.

## Requisitos

| Componente | Versión / notas |
|------------|-----------------|
| **Python** | ≥ 3.10 |
| **Pillow** | generación de miniaturas |
| **pywebview** | ventana con interfaz web embebida |
| **Node.js + npm** | solo para desarrollar o compilar la UI (`webui/`) |
| **PyQt6 + PyQt6-WebEngine + qtpy** | opcional, recomendado en Fedora KDE (`pip install -e ".[qt]"`) |
| **ffmpeg / ffprobe** | opcional, diagnóstico y transcodificación de vídeo en el visor |

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

La aplicación carga `webui/dist/index.html` si existe.

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

En Windows el flujo es el mismo (Python + build de `webui/`); el **.exe portable** solo se puede generar **en un PC Windows x64** (PyInstaller no cruza desde Linux sin entorno extra).

### Ejecutar desde código (desarrollo o uso local)

En **PowerShell** desde la raíz del repositorio:

```powershell
git clone https://github.com/FernandoRP-nan/Organizador-Fedora-KDE.git
cd Organizador-Fedora-KDE

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -e .
# Opcional: pip install pywebview pillow

cd webui
npm ci
npm run build
cd ..

python organizador_multimedia.py
```

Requisitos en el equipo:

| Componente | Notas |
|------------|--------|
| **Python** | 3.10 o superior, en el `PATH` |
| **Node.js + npm** | Para compilar la UI (`webui/`) |
| **WebView2 Runtime** | Lo usa PyWebView; suele estar ya en Windows 10/11 |
| **ffmpeg / ffprobe** | Opcional; necesario para transcodificar vídeos en el visor (AVI, MKV, etc.) |

Para vídeo, puedes instalar ffmpeg en el `PATH` o colocar `ffmpeg.exe` y `ffprobe.exe` en `tools\ffmpeg\` junto al programa.

### Compilar portable (.exe para compartir)

1. Clona el repo en un **PC Windows 64 bits** con **Python 3.10+** y **Node.js**.
2. En PowerShell, en la raíz del repo:

   ```powershell
   .\scripts\build-windows-portable.ps1
   ```

   El script ejecuta `npm run build`, PyInstaller (`GaleriaAYN.spec`) y copia **ffmpeg** a `dist\GaleriaAYN\tools\ffmpeg\`.

3. Salida: carpeta **`dist\GaleriaAYN\`** con **`GaleriaAYN.exe`**. Comprime **toda la carpeta** en un `.zip` (modo *onedir*: no mover solo el `.exe` fuera de la carpeta).

Build manual equivalente:

```powershell
cd webui
npm ci
npm run build
cd ..
pip install pyinstaller pillow pywebview
pyinstaller --clean GaleriaAYN.spec
.\scripts\fetch-ffmpeg-windows.ps1
# Copiar tools\ffmpeg\*.exe a dist\GaleriaAYN\tools\ffmpeg\
```

Requisitos para quien **recibe** el zip, solución de problemas (SmartScreen, WebView2, «ffmpeg no encontrado», etc.): **[docs/windows-portable.md](docs/windows-portable.md)**.

CI: el workflow `.github/workflows/build-windows-portable.yml` puede generar el artefacto en GitHub Actions (runner `windows-latest`).

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

En otra terminal, con la app Python apuntando al dev server (por defecto `http://127.0.0.1:5173`):

```bash
source .venv/bin/activate
python3 organizador_multimedia.py
```

Detalle en [webui/README.md](webui/README.md).

## Estructura del proyecto

```
organizador_multimedia.py   # Punto de entrada
org_multimedia/             # Backend Python (API, galería, ajustes)
webui/                      # Frontend Svelte + Vite
docs/                       # Documentación adicional
scripts/                    # Instalación en KDE, lanzadores
```

## Documentación adicional

- [Integración Fedora KDE](docs/desktop-fedora-kde.md)
- [Roadmap de funcionalidades](docs/ROADMAP-FEATURES.md)
- [Build portable Windows](docs/windows-portable.md)

## Licencia

Revisa el repositorio para la licencia aplicable. Si aún no hay archivo `LICENSE`, añádelo antes de publicar como proyecto abierto.
