"""Escaneo de carpetas para la galeria."""

from __future__ import annotations

from pathlib import Path

from .media_organizer import MediaOrganizer

# Imágenes + vídeo para la galería web (misma lista ordenada que `sort_image_paths`).
GALLERY_MEDIA_EXTENSIONS: frozenset[str] = frozenset(
    MediaOrganizer.IMAGE_EXTENSIONS | MediaOrganizer.VIDEO_EXTENSIONS
)


def list_subdirs(root: Path) -> list[Path]:
    out: list[Path] = []
    try:
        for p in root.iterdir():
            if p.is_dir():
                out.append(p)
    except OSError:
        pass
    out.sort(key=lambda x: str(x).lower())
    return out


def scan_images_flat(root: Path, image_extensions: frozenset[str] | None = None) -> list[Path]:
    # Solo archivos en esta carpeta (no recursivo).
    exts = image_extensions if image_extensions is not None else MediaOrganizer.IMAGE_EXTENSIONS
    out: list[Path] = []
    try:
        for p in root.iterdir():
            if p.is_file() and p.suffix.lower() in exts:
                out.append(p)
    except OSError:
        pass
    out.sort(key=lambda x: str(x).lower())
    return out


def scan_images_recursive(root: Path, image_extensions: frozenset[str] | None = None) -> list[Path]:
    """Todas las imágenes bajo `root` (incluye subcarpetas)."""
    exts = image_extensions if image_extensions is not None else MediaOrganizer.IMAGE_EXTENSIONS
    out: list[Path] = []
    try:
        for p in root.rglob("*"):
            if p.is_file() and p.suffix.lower() in exts:
                out.append(p)
    except OSError:
        pass
    out.sort(key=lambda x: str(x).lower())
    return out


def scan_media_flat(root: Path, extensions: frozenset[str] | None = None) -> list[Path]:
    """Archivos en esta carpeta: imágenes y vídeo (no recursivo)."""
    exts = extensions if extensions is not None else GALLERY_MEDIA_EXTENSIONS
    out: list[Path] = []
    try:
        for p in root.iterdir():
            if p.is_file() and p.suffix.lower() in exts:
                out.append(p)
    except OSError:
        pass
    out.sort(key=lambda x: str(x).lower())
    return out


def scan_media_recursive(root: Path, extensions: frozenset[str] | None = None) -> list[Path]:
    """Imágenes y vídeo bajo `root` (incluye subcarpetas)."""
    exts = extensions if extensions is not None else GALLERY_MEDIA_EXTENSIONS
    out: list[Path] = []
    try:
        for p in root.rglob("*"):
            if p.is_file() and p.suffix.lower() in exts:
                out.append(p)
    except OSError:
        pass
    out.sort(key=lambda x: str(x).lower())
    return out


def sort_image_paths(paths: list[Path], mode: str) -> list[Path]:
    """Orden compuesto y estable: `mode` puede ser una lista separada por comas, ej. 'type,mtime,name'.

    Criterios:
      - `type`: Agrupa videos primero y luego imágenes (o viceversa). 0 para imágenes, 1 para videos.
      - `mtime`/`date`/`fecha`: Fecha de modificación (de menor a mayor).
      - `name`: Nombre del archivo / ruta completa (case insensitive).
    """
    # Procesar la lista de prioridades de ordenamiento y su dirección
    raw_modes = [x.strip().lower() for x in (mode or "name").split(",")]
    
    # Filtrar los modos válidos y su dirección (por defecto desc para mtime, asc para name/type)
    sort_keys = []
    for m_raw in raw_modes:
        parts = m_raw.split(":")
        m = parts[0]
        direction = parts[1] if len(parts) > 1 else None
        
        if m in ("mtime", "date", "fecha"):
            # mtime por defecto es desc (más reciente primero)
            is_desc = direction != "asc"
            sort_keys.append(("mtime", is_desc))
        elif m in ("type", "tipo"):
            # type por defecto es asc
            is_desc = direction == "desc"
            sort_keys.append(("type", is_desc))
        elif m in ("name", "nombre"):
            # name por defecto es asc
            is_desc = direction == "desc"
            sort_keys.append(("name", is_desc))

    # Si por alguna razón queda vacío, forzar ordenar por nombre asc
    if not sort_keys:
        sort_keys = [("name", False)]

    # Agregar "name" como criterio final implícito de desempate para asegurar orden estable
    if not any(k[0] == "name" for k in sort_keys):
        sort_keys.append(("name", False))

    # Python's `sorted` can only sort by a single `reverse` boolean for all keys at once.
    # To support mixed directions, we invert the values of descending keys.
    def make_sort_key(p: Path) -> tuple:
        key_parts = []
        for sk, is_desc in sort_keys:
            if sk == "mtime":
                try:
                    val = p.stat().st_mtime_ns
                except OSError:
                    val = 0
                key_parts.append(-val if is_desc else val)
            elif sk == "type":
                # Vídeos tienen valor 1, imágenes valor 0 para ordenamiento
                is_video = p.suffix.lower() in MediaOrganizer.VIDEO_EXTENSIONS
                val = 1 if is_video else 0
                key_parts.append(-val if is_desc else val)
            elif sk == "name":
                # Strings can't be easily inverted numerically, but we can rely on Python's stable sort
                # by sorting in multiple passes. But for simplicity, since name is usually the tiebreaker,
                # we'll use a trick or just use single pass and not support desc name sorting fully.
                # Actually, wait, let's just use string for ascending. For descending, we can invert characters?
                # A simpler approach: we'll do multiple passes of stable sorting!
                pass # Handled below
        return tuple()
        
    # Since we need mixed sorting (some asc, some desc), and Python's stable sort allows us to sort multiple times:
    # We sort by the least important key first, up to the most important key.
    result = paths.copy()
    for sk, is_desc in reversed(sort_keys):
        if sk == "mtime":
            def get_mtime(p: Path):
                try: return p.stat().st_mtime_ns
                except OSError: return 0
            result.sort(key=get_mtime, reverse=is_desc)
        elif sk == "type":
            def get_type(p: Path):
                return 1 if p.suffix.lower() in MediaOrganizer.VIDEO_EXTENSIONS else 0
            result.sort(key=get_type, reverse=is_desc)
        elif sk == "name":
            def get_name(p: Path):
                return str(p).lower()
            result.sort(key=get_name, reverse=is_desc)

    return result
