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

## Qué necesitan tus amigos (solo quien recibe el zip)

- **Windows 10/11** de 64 bits.
- **WebView2** (Microsoft Edge WebView2 Runtime). En la mayoría de equipos ya está instalado; si la ventana no carga la interfaz, que instalen el runtime desde Microsoft: buscar “WebView2 Runtime Download”.

Opcional: **Visual C++ Redistributable** si Windows avisa de DLLs faltantes (poco frecuente con builds recientes).

## Actualizar el portable después de cambios en el código

1. `git pull`
2. En el PC Windows: repetir el script de build (incluye `npm run build` + PyInstaller).
3. Volver a generar el `.zip` de `dist\GaleriaAYN`.

## Notas

- **SmartScreen** puede avisar la primera vez en un `.exe` sin firma digital; es normal en proyectos personales. Firmar el ejecutable (certificado de código) evita el aviso, pero tiene coste y trámites.
- El nombre del ejecutable y la carpeta es **GaleriaAYN** (sin acentos) para evitar problemas con herramientas antiguas.

## «Se ve una versión vieja de la interfaz» (en quien recibe el .zip)

El `.exe` **no** descarga la UI desde internet: **incrusta una copia de `webui/dist` del momento en que ejecutaste PyInstaller**.

Si tus amigos ven pantallas antiguas, casi siempre es porque:

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
