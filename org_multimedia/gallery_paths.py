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
    """Orden estable: `name` por ruta; `mtime` por fecha de modificación."""
    m = (mode or "name").strip().lower()
    if m in ("mtime", "date", "fecha"):
        def key(p: Path) -> tuple:
            try:
                return (p.stat().st_mtime_ns, str(p).lower())
            except OSError:
                return (0, str(p).lower())

        return sorted(paths, key=key)
    return sorted(paths, key=lambda x: str(x).lower())
