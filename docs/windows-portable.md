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
