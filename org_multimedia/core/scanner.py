"""Lógica de escaneo y búsqueda de archivos."""

from pathlib import Path

from .gallery_paths import natural_sort_key, path_natural_sort_key
from .media_organizer import MediaOrganizer

# Extensiones multimedia para la galería
GALLERY_MEDIA_EXTENSIONS: frozenset[str] = frozenset(
    MediaOrganizer.IMAGE_EXTENSIONS | MediaOrganizer.VIDEO_EXTENSIONS
)

def list_subdirs(root: Path) -> list[Path]:
    """Lista subdirectorios inmediatos de forma ordenada."""
    out: list[Path] = []
    try:
        if root.exists() and root.is_dir():
            for p in root.iterdir():
                if p.is_dir():
                    out.append(p)
    except OSError:
        pass
    out.sort(key=path_natural_sort_key)
    return out

def scan_media_flat(root: Path, extensions: frozenset[str] | None = None) -> list[Path]:
    """Escaneo no recursivo de medios."""
    exts = extensions if extensions is not None else GALLERY_MEDIA_EXTENSIONS
    out: list[Path] = []
    try:
        if root.exists() and root.is_dir():
            for p in root.iterdir():
                if p.is_file() and p.suffix.lower() in exts:
                    out.append(p)
    except OSError:
        pass
    return out

def scan_media_recursive(root: Path, extensions: frozenset[str] | None = None) -> list[Path]:
    """Escaneo recursivo de medios."""
    exts = extensions if extensions is not None else GALLERY_MEDIA_EXTENSIONS
    out: list[Path] = []
    try:
        if root.exists() and root.is_dir():
            for p in root.rglob("*"):
                if p.is_file() and p.suffix.lower() in exts:
                    out.append(p)
    except OSError:
        pass
    return out

def sort_paths(paths: list[Path], mode: str) -> list[Path]:
    """Ordenación de rutas por nombre o mtime."""
    m = (mode or "name").strip().lower()
    if m in ("mtime", "date", "fecha"):
        def key(p: Path) -> tuple:
            try:
                return (p.stat().st_mtime_ns, natural_sort_key(str(p)))
            except OSError:
                return (0, natural_sort_key(str(p)))
        return sorted(paths, key=key)
    return sorted(paths, key=path_natural_sort_key)
