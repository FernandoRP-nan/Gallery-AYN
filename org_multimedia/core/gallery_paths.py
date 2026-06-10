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
    # Procesar la lista de prioridades de ordenamiento
    raw_modes = [x.strip().lower() for x in (mode or "name").split(",")]
    # Filtrar los modos válidos
    sort_keys = []
    for m in raw_modes:
        if m in ("mtime", "date", "fecha"):
            sort_keys.append("mtime")
        elif m in ("type", "tipo"):
            sort_keys.append("type")
        elif m in ("name", "nombre"):
            sort_keys.append("name")

    # Si por alguna razón queda vacío, forzar ordenar por nombre
    if not sort_keys:
        sort_keys = ["name"]

    # Agregar "name" como criterio final implícito de desempate para asegurar orden estable
    if "name" not in sort_keys:
        sort_keys.append("name")

    def make_sort_key(p: Path) -> tuple:
        key_parts = []
        for sk in sort_keys:
            if sk == "mtime":
                try:
                    key_parts.append(p.stat().st_mtime_ns)
                except OSError:
                    key_parts.append(0)
            elif sk == "type":
                # Vídeos tienen valor 1, imágenes valor 0 para ordenamiento (o viceversa)
                is_video = p.suffix.lower() in MediaOrganizer.VIDEO_EXTENSIONS
                key_parts.append(1 if is_video else 0)
            elif sk == "name":
                key_parts.append(str(p).lower())
        return tuple(key_parts)

    return sorted(paths, key=make_sort_key)
