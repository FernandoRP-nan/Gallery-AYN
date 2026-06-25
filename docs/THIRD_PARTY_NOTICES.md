# Avisos legales y componentes de terceros

**Galería AYN / Organizador Multimedia**  
Copyright (c) 2025-2026 FernandoRP

El código fuente de esta aplicación se distribuye bajo la licencia **MIT**. Ver el archivo [`LICENSE`](../LICENSE) en la raíz del repositorio.

Este documento describe **software de terceros** incluido o usado al ejecutar o distribuir el **.exe portable para Windows**. Si redistribuyes el zip generado por PyInstaller, **debes incluir** este archivo (o una copia equivalente) junto al ejecutable.

---

## 1. Resumen del paquete portable Windows

| Componente | ¿Incluido en el zip? | Licencia |
|------------|----------------------|----------|
| Galería AYN (código propio + UI compilada) | Sí | MIT |
| Intérprete Python + bibliotecas empaquetadas (PyInstaller) | Sí | Varies (ver §2) |
| **ffmpeg** / **ffprobe** | Sí (`tools/ffmpeg/`) | **LGPL v2.1+** |
| WebView2 Runtime | No (instalado en el sistema) | Microsoft |
| .NET Framework | No (instalado en el sistema) | Microsoft |
| PyQt6 | No en el portable Windows | GPL v3 (solo extra opcional en Linux) |

---

## 2. Bibliotecas Python empaquetadas (PyInstaller)

El build portable incluye, entre otras, dependencias con estas licencias habituales:

| Proyecto | Licencia | Enlace |
|----------|----------|--------|
| **Python** | PSF License | https://docs.python.org/3/license.html |
| **PyWebView** | BSD 3-Clause | https://github.com/r0x0r/pywebview |
| **Pillow** | HPND License | https://github.com/python-pillow/Pillow |
| **pythonnet** | MIT | https://github.com/pythonnet/pythonnet |
| **PyInstaller** (solo build) | GPL v2 + excepción | https://pyinstaller.org |

Las licencias completas de cada paquete están en los metadatos del proyecto en PyPI o en su repositorio. El bundle `_internal/` de PyInstaller contiene los binarios correspondientes.

---

## 3. ffmpeg y ffprobe (LGPL v2.1+) — **importante si distribuyes el .exe**

Los binarios **ffmpeg.exe** y **ffprobe.exe** (build *essentials* de [gyan.dev](https://www.gyan.dev/ffmpeg/builds/)) se copian a:

```text
GaleriaAYN/tools/ffmpeg/
```

### 3.1 Obligaciones al redistribuir ffmpeg (LGPL)

Si incluyes estos ejecutables en tu zip **sin modificar** el código de ffmpeg:

1. **Incluir** una copia de la **GNU LGPL v2.1** (incluida en `tools/ffmpeg/licenses/` o en este repositorio).
2. **Incluir** los textos de licencia que vienen con el build de ffmpeg (`LICENSE`, `COPYING.LGPLv2.1`, etc.).
3. **Informar** a los usuarios finales de que ffmpeg está bajo LGPL y dónde está el código fuente.
4. **Ofrecer acceso al código fuente** de ffmpeg:
   - Código fuente oficial: https://github.com/FFmpeg/FFmpeg  
   - Builds usados (essentials): https://www.gyan.dev/ffmpeg/builds/  
   - Puedes añadir en tu release un enlace a esta página o incluir el archivo `.zip` de *source* de la misma versión.

Si **modificas** ffmpeg y redistribuyes el binario, debes publicar el código fuente de **tu versión modificada** bajo LGPL.

### 3.2 Separabilidad

ffmpeg se invoca como **proceso externo** (subprocess). La aplicación no enlaza estáticamente la librería libav*. Esto facilita el cumplimiento de LGPL: puedes sustituir `tools/ffmpeg/*.exe` por builds equivalentes sin recompilar Galería AYN.

---

## 4. Interfaz web (Svelte / Vite)

La UI se compila a archivos estáticos en `webui/dist/` e se embebe en el portable. Dependencias de desarrollo principales:

| Proyecto | Licencia |
|----------|----------|
| **Svelte** | MIT |
| **Vite** | MIT |

No se distribuyen por separado; forman parte del bundle web incluido en `_internal/webui/dist/`.

---

## 5. Componentes del sistema (no incluidos en el zip)

### WebView2 Runtime

PyWebView en Windows usa **Microsoft Edge WebView2**. El runtime lo instala el usuario o ya viene en Windows 10/11. Aplica la [licencia de software de Microsoft](https://www.microsoft.com/es-es/legal/terms-of-use).

### .NET Framework

PyWebView/pythonnet puede requerir **.NET Framework 4.7.2+** en el equipo destino. Licencia Microsoft.

---

## 6. Marcas registradas

*Galería AYN*, *Organizador Multimedia* y nombres de terceros (Microsoft, Windows, Edge, WebView2, Python, ffmpeg, etc.) son marcas de sus respectivos titulares. Este proyecto no está afiliado ni respaldado por ellos.

---

## 7. Sin garantía

El software se proporciona **«TAL CUAL»**, sin garantías de ningún tipo. Ver la licencia MIT en `LICENSE`.

---

## 8. Contacto

Incidencias y código fuente del proyecto:  
https://github.com/FernandoRP-nan/Organizador-Fedora-KDE
