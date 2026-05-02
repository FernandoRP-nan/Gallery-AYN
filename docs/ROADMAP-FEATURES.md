# Roadmap de funcionalidades (Galería AYN / Organizador)

Documento de seguimiento para las mejoras solicitadas. Las fases son orientativas; el orden puede ajustarse según dependencias técnicas.

## Fase A — Vista y galería

| Estado | Ítem |
|--------|------|
| Hecho (parcial) | Menú **Vista** junto a **Edición**: incluir imágenes de subcarpetas (recursivo), orden por nombre o por fecha de archivo |
| Hecho (parcial) | **Agrupar por carpeta**: secciones por subcarpeta + raíz, doble clic abre carpeta; en modo Edición arrastrar (Ctrl) al encabezado mueve al destino |
| Hecho (parcial) | Vista **línea de tiempo**: secciones por **mes** (fecha de modificación); marcas por **día** cuando la celda de miniatura supera ~130 px (solo cliente) |
| Hecho (parcial) | **Colores dominantes** por sección (tinte en cabecera según color medio de hasta 3 imágenes; opción en Vista) |

## Fase B — Pantalla completa y edición

| Hecho (parcial) | Modo **editar** (icono lápiz en barra fullscreen): recorte, rotación básica (persistencia en disco vía Pillow) |
| Pendiente | **IA de mejora de calidad** en modo editar |
| Hecho (parcial) | Reproducción de **vídeo** en vista previa y fullscreen (`file://` vía PyWebView; codecs según motor) |
| Hecho (parcial) | Ampliar formatos: **SVG** en galería y vista previa (`file://`); rotación/recorte desactivados (vectorial) |

## Fase C — Organización e IA

| Pendiente | **Organizar con IA** en el modal de organizar (además de reglas actuales) |
| Pendiente | Carpeta **desorden**: sugerencias por similitud (estilo Pinterest) y mover a la carpeta actual con un clic |
| Pendiente | **Recibir archivos** del móvil hacia la carpeta de desorden (diseño: WebDAV, carpeta compartida, QR, etc.) |

## Fase D — UX y sistema

| Hecho (parcial) | **i18n**: `es.ts` ampliado con **`status`** (barra de estado); modales/overlay en `webui/src/components/` (`ConfirmDeleteModal`, `LoadOverlay`, `SettingsModal`) |
| Hecho (parcial) | **Temas de color** en ajustes (Medianoche, Océano, Brasas, Bosque, Papel claro; persistencia `web_ui_theme`) |
| Hecho (parcial) | **Clic derecho** en imagen: copiar miniatura/ruta, eliminar, mover a destinos, modal de metadatos (tamaño, fecha); copiar “imagen” al portapapeles solo cuando hay miniatura generada |
| Hecho | Modal confirmar **desanclar marcador** (y **Guardar marcador**): atajos globales no actúan con el diálogo abierto |
| Hecho (parcial) | Windows: **selección con flechas** en fullscreen: carrusel solo hace scroll si el thumb activo queda cortado; resaltado con tokens de tema (`--om-accent-glow`) |
| Hecho (parcial) | **Refactor**: `ConfirmDeleteModal`, `LoadOverlay`, `SettingsModal` (+ `settings/*.svelte`, `settings/panel.css`); `App.svelte` como shell principal |

## Notas

- La **interfaz Tk** quedó fuera del flujo principal; solo web + mensajes de error.
- **Vídeo / codecs** en Windows suele apoyarse en WebView2 / elementos `<video>` y formatos que el motor soporte; extensiones raras pueden requerir transcodificación en backend (futuro).
