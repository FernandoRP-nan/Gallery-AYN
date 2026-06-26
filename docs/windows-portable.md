# Galería AYN — build portable para Windows (.exe)

El objetivo es una **carpeta** `dist/GaleriaAYN/` con `GaleriaAYN.exe` y DLLs, que puedas **comprimir en .zip** y pasar a quien use **Windows 10/11 64 bits**.

## Qué necesitas (solo quien construye el zip)

- **Windows** x64 (PyInstaller genera el `.exe` para Windows; no se puede cruzar desde Linux sin contenedor/Wine extra).
- **Python 3.10+** instalado y en el `PATH`.
- **Node.js** (para `npm run build` del frontend).

## Pasos

1. Clona o copia el repositorio en el PC Windows.
2. Abre **PowerShell** en la raíz del repo y ejecuta:

   ```powershell
   .\scripts\build-windows-portable.ps1
   ```

   O manualmente:

   ```powershell
   cd webui
   npm ci
   npm run build
   cd ..
   pip install pyinstaller pillow pywebview
   pyinstaller --clean GaleriaAYN.spec
   ```

3. Salida: carpeta **`dist\GaleriaAYN\`**. Dentro está **`GaleriaAYN.exe`**.
4. **Comprime toda la carpeta** `GaleriaAYN` en un `.zip` y compártela. Los amigos **no** deben borrar DLLs ni mover solo el `.exe` fuera de esa carpeta (modo *onedir*).

### Avisos legales (obligatorio al distribuir el zip)

El script de build copia automáticamente en `dist\GaleriaAYN\`:

| Archivo | Contenido |
|---------|-----------|
| `LICENSE.txt` | Licencia MIT de Galería AYN |
| `LEGAL-THIRD_PARTY.md` | Componentes de terceros (Python, PyWebView, ffmpeg, etc.) |
| `COPYING.LGPLv2.1.txt` | Resumen y enlace a LGPL (ffmpeg) |
| `tools\ffmpeg\licenses\` | Textos de licencia del build de ffmpeg |

**No elimines** estos archivos del zip. Si publicas en GitHub Releases, enlaza también el repositorio como fuente del código de la aplicación.

Detalle completo: **[docs/THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)**.

## Qué necesitan tus amigos (solo quien recibe el zip)

- **Windows 10/11** de 64 bits.
- **.NET Framework 4.7.2 o superior** (PyWebView en Windows usa pythonnet). En Windows 10/11 suele estar ya instalado; si falta: Panel de control → Programas → Activar o desactivar las características de Windows → **.NET Framework 3.5 (incluye 4.x)**.
- **WebView2** (Microsoft Edge WebView2 Runtime). En la mayoría de equipos ya está instalado; si la ventana no carga la interfaz, que instalen el runtime desde Microsoft: buscar “WebView2 Runtime Download”.
- Si el **.zip se descargó** (WhatsApp, correo, navegador): antes de extraer, clic derecho en el `.zip` → **Propiedades** → marcar **Desbloquear** → Aceptar. Si ya lo extrajo sin desbloquear, borre la carpeta, desbloquee el zip y vuelva a extraer (o ejecute de nuevo un build reciente del programa, que intenta desbloquear solo al arrancar).

Opcional: **Visual C++ Redistributable** (x64) si Windows avisa de DLLs faltantes: [VC++ Redistributable](https://learn.microsoft.com/es-es/cpp/windows/latest-supported-vc-redist).

### Vídeos (.avi, .mkv, etc.) no reproducen / «ffmpeg no encontrado»

El visor integrado **transcodifica** formatos que WebView2 no reproduce directamente (p. ej. AVI de 700 MB). Para eso hace falta **ffmpeg** y **ffprobe**:

1. **Builds oficiales (CI o `build-windows-portable.ps1`):** el script descarga ffmpeg essentials y lo copia a `tools\ffmpeg\` **junto a `GaleriaAYN.exe`**. No hace falta instalar nada extra si usas el zip generado así.
2. **Manual (solo si compilaste sin el script):** crear `tools\ffmpeg\` junto al `.exe` y copiar `ffmpeg.exe` y `ffprobe.exe` desde [gyan.dev/ffmpeg](https://www.gyan.dev/ffmpeg/builds/) («release essentials»).
3. **Alternativa:** instalar ffmpeg en el sistema y añadirlo al **PATH** de Windows, o definir `ORGANIZADOR_FFMPEG_DIR` apuntando a la carpeta que contiene `ffmpeg.exe`.

Los **MP4 H.264** suelen reproducirse sin ffmpeg. Para cualquier otro formato, sin ffmpeg verás un mensaje claro en la app; usa **Abrir con reproductor del sistema** como alternativa.

En **Ajustes → Vídeo** puedes elegir perfil rápido/calidad, altura máxima y aceleración por hardware (NVENC/QSV/AMF). La **primera reproducción** de un vídeo grande puede tardar (transcodificación en «Procesos activos» con % de avance); las siguientes usan caché en `%LOCALAPPDATA%` o `%USERPROFILE%\.cache\organizador-ayn\om-transcode\`.

### «Failed to load Python DLL» / `python312.dll` / ruta con `Temp` y `.zip`

Eso casi siempre significa **no** estar usando la carpeta descomprimida:

1. **No abrir el `.exe` desde dentro del archivo `.zip`** (Explorador de archivos muestra el zip como carpeta, pero los archivos viven en una ruta temporal tipo `...\AppData\Local\Temp\..._GaleriaAYN.zip.ca6\...`). Ahí faltan DLLs o no cargan bien → `LoadLibrary: No se puede encontrar el módulo especificado`.
2. **Solución:** clic derecho en el `.zip` → **Extraer todo…** → elegir por ejemplo `Escritorio\GaleriaAYN\` → entrar en esa carpeta y ejecutar **`GaleriaAYN.exe`**. Debe existir junto al `.exe` la carpeta **`_internal`** con las DLL.
3. Si tras extraer bien sigue el error, instalar **Visual C++ Redistributable x64** (enlace arriba).

### «No se encuentra el archivo» / `ERR_FILE_NOT_FOUND` al abrir la ventana

La interfaz se sirve por **http://127.0.0.1** (servidor embebido), no como `file://`. Si ves esta página en blanco con ese código:

1. **Extraer el zip completo** (misma regla que arriba: no ejecutar desde dentro del `.zip`).
2. Comprobar que en `_internal\webui\dist\` existen `index.html` y la carpeta `assets\`.
3. **Reconstruir el portable** con el script actual (`.\scripts\build-windows-portable.ps1`): builds anteriores a la corrección de rutas podían fallar así en Windows.
4. Si persiste: instalar **WebView2 Runtime** y revisar que el antivirus no bloquee la carpeta.

### `Python.Runtime.dll` / `Failed to resolve Python.Runtime.Loader.Initialize`

No es un fallo de WebView2: es **pythonnet** (.NET) al cargar la ventana nativa de PyWebView.

1. **Desbloquear el zip** (muy frecuente): clic derecho en el `.zip` → Propiedades → **Desbloquear** → extraer de nuevo en carpeta vacía. Windows marca los archivos descargados y .NET no puede cargar `Python.Runtime.dll`.
2. Comprobar **.NET Framework ≥ 4.7.2** (ver requisitos arriba).
3. Usar un **build reciente** del portable (el programa desbloquea `_internal` al iniciar; builds viejos no).
4. Ruta sin rarezas: evitar ejecutar desde `Downloads\GaleriaAYN (1)\` mezclando varias copias; una carpeta limpia p. ej. `C:\GaleriaAYN\` suele ir mejor.

CI: workflow [`.github/workflows/build-windows-portable.yml`](.github/workflows/build-windows-portable.yml) (artifact en `main`; **Release** al pushear un tag `v*`).

## Publicar versión estable (GitHub Releases)

Para que amigos y usuarios descarguen un zip **permanente** desde la pestaña **Releases** del repositorio:

1. Asegúrate de que `main` tiene el código que quieres publicar (`git push`).
2. Crea un tag semver con prefijo `v`:

   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

3. GitHub Actions ejecuta el workflow **Build Windows portable** en un runner Windows.
4. Al terminar, aparece un **Release** `v1.0.0` con el asset **`GaleriaAYN-v1.0.0-portable.zip`**.

Comparte el enlace directo del release, por ejemplo:

`https://github.com/FernandoRP-nan/Gallery-AYN/releases/latest`

(o la URL con tag concreto: `.../releases/tag/v1.0.0`).

### Qué ocurre en cada tipo de push

| Evento | Resultado |
|--------|-----------|
| Push a `main` (cambios en código/UI) | Artifact temporal (30 días) en *Actions* — para probar builds |
| Push de tag `v1.0.0`, `v1.2.3`, … | **Release** público con el zip portable |
| *Run workflow* manual | Solo artifact (no crea release) |

Para una versión nueva, incrementa el tag (`v1.0.1`, `v1.1.0`, …). No reutilices un tag ya publicado.

## Actualizar el portable después de cambios en el código

1. `git pull`
2. En el PC Windows: repetir el script de build (incluye `npm run build` + PyInstaller).
3. Volver a generar el `.zip` de `dist\GaleriaAYN`.

## Notas

- **SmartScreen** puede avisar la primera vez en un `.exe` sin firma digital; es normal en proyectos personales. Firmar el ejecutable (certificado de código) evita el aviso, pero tiene coste y trámites.
- El nombre del ejecutable y la carpeta es **GaleriaAYN** (sin acentos) para evitar problemas con herramientas antiguas.

## «Se ve una versión vieja de la interfaz» (en quien recibe el .zip)

La aplicación usa **solo** la interfaz web (Svelte). Si PyWebView no puede iniciar, verás un **mensaje de error** (ya no se abre en silencio la interfaz antigua en Tk).

El `.exe` **no** descarga la UI desde internet: **incrusta una copia de `webui/dist` del momento en que ejecutaste PyInstaller**.

Si tus amigos ven pantallas antiguas en builds **anteriores**, a veces era porque:

1. **Fallback a Tk:** en versiones viejas, si fallaba WebView se abría la UI clásica en Python; parecía otra versión. Con builds recientes solo hay ventana web o error explícito (y WebView2 suele figurar como «ya instalado» en Complementos de Windows; si aun así falla, revisar antivirus o el mensaje de error).

Si tus amigos ven pantallas antiguas en el **mismo zip**, casi siempre es porque:

1. **No se ejecutó `npm run build`** con el código actual **antes** de `pyinstaller`, o se compiló desde una carpeta sin los últimos cambios.
2. Se subió un **.zip antiguo** (misma carpeta `dist/GaleriaAYN` de otro día).
3. PyInstaller reutilizó caché: usar siempre `pyinstaller --clean GaleriaAYN.spec` (el script de PowerShell ya lo hace).

**Qué hacer cada vez que quieras publicar una versión nueva**

1. `git pull` (o copia los archivos nuevos).
2. `cd webui` → `npm ci` → `npm run build`.
3. Borra salidas viejas: en la raíz del repo, elimina las carpetas **`dist`** y **`build`** (las de PyInstaller en la raíz, no `webui/dist`).
4. `pyinstaller --clean GaleriaAYN.spec`.
5. Comprime **de nuevo** toda la carpeta `dist\GaleriaAYN` y envía ese zip.

En el pie de la aplicación verás una **fecha corta (AAAA-MM-DD)** de compilación del interfaz: debe coincidir con el día en que hiciste el `npm run build`. Si en tu PC ves una fecha reciente y en el de un amigo una antigua, no están usando el mismo zip o no reemplazaron la carpeta entera al descomprimir.

### Sigo viendo interfaz vieja en otro PC (y tú ves la nueva)

Suele ser **caché de Microsoft Edge WebView2**: el motor puede reutilizar JS/CSS de una ejecución anterior aunque el `.exe` sea nuevo. A partir de la versión que incluye `?v=` en la URL del `index.html` (y meta `no-store` en la web), esto debería reducirse mucho.

Si aun así pasa, en el PC del que recibe:

1. **Cerrar** la app, **borrar** cualquier carpeta vieja llamada `GaleriaAYN` (Escritorio, Descargas, etc.).
2. **Descomprimir el zip en una carpeta nueva y vacía** (no “mezclar” encima de una copia anterior).
3. Abrir **solo** el `GaleriaAYN.exe` de esa carpeta (no un acceso directo antiguo).

4. (Opcional) Borrar datos de WebView2 para el host local: cerrar la app, ejecutar en **cmd**:
   `rmdir /s /q "%LOCALAPPDATA%\GaleriaAYN"`  
   (si existe; el nombre exacto puede variar según versión de pywebview). Luego volver a abrir el `.exe`.
