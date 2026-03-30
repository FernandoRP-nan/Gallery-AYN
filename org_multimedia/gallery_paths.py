"""Escaneo de carpetas para la galeria (no recursivo)."""

from __future__ import annotations

from pathlib import Path

from .media_organizer import MediaOrganizer


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
