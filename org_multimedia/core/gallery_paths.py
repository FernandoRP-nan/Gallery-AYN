"""Escaneo de carpetas para la galeria."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
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


def list_subdirs_recursive(root: Path) -> list[Path]:
    """Subcarpetas en cualquier profundidad bajo root (excluye ocultas tipo .thumbnails)."""
    base = root.resolve()
    out: list[Path] = []
    try:
        for p in base.rglob("*"):
            if not p.is_dir():
                continue
            try:
                rel = p.relative_to(base)
            except ValueError:
                continue
            if any(part.startswith(".") for part in rel.parts):
                continue
            out.append(p)
    except OSError:
        pass
    out.sort(key=lambda x: str(x.relative_to(base)).lower())
    return out


def grouped_section_label(root: Path, folder: Path) -> str:
    """Etiqueta de sección: ruta relativa (p. ej. Otaku/Waifus) o nombre si es hijo directo."""
    try:
        rel = folder.resolve().relative_to(root.resolve())
    except ValueError:
        return folder.name
    text = rel.as_posix()
    return text if text else folder.name


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
        with os.scandir(root) as it:
            for entry in it:
                if not entry.is_file(follow_symlinks=False):
                    continue
                if Path(entry.name).suffix.lower() in exts:
                    out.append(Path(entry.path))
    except OSError:
        pass
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


def _prefetch_path_stats(
    paths: list[Path],
    cache: dict[Path, os.stat_result | None],
    *,
    max_workers: int | None = None,
) -> None:
    """Precarga stat() en paralelo (5600X / discos grandes)."""
    if len(paths) <= 512:
        return
    workers = max_workers or min(12, max(4, os.cpu_count() or 4))

    def stat_one(p: Path) -> tuple[Path, os.stat_result | None]:
        try:
            return p, p.stat()
        except OSError:
            return p, None

    chunk = max(64, len(paths) // (workers * 4))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for p, st in pool.map(stat_one, paths, chunksize=chunk):
            cache[p] = st


def sort_image_paths(paths: list[Path], mode: str, *, stat_workers: int | None = None) -> list[Path]:
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
        elif m in ("ctime", "creacion", "creation", "created"):
            is_desc = direction != "asc"
            sort_keys.append(("ctime", is_desc))
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

    # Orden estable con stat() cacheado; precarga paralela si hace falta mtime/ctime.
    stat_cache: dict[Path, os.stat_result | None] = {}
    needs_stat = any(sk in ("mtime", "ctime") for sk, _ in sort_keys)
    if needs_stat:
        _prefetch_path_stats(paths, stat_cache, max_workers=stat_workers)

    def _stat_cached(p: Path) -> os.stat_result | None:
        if p not in stat_cache:
            try:
                stat_cache[p] = p.stat()
            except OSError:
                stat_cache[p] = None
        return stat_cache[p]

    result = paths.copy()
    for sk, is_desc in reversed(sort_keys):
        if sk == "mtime":
            def get_mtime(p: Path, _desc=is_desc):
                st = _stat_cached(p)
                val = st.st_mtime_ns if st is not None else 0
                return -val if _desc else val
            result.sort(key=get_mtime)
        elif sk == "ctime":
            def get_ctime(p: Path, _desc=is_desc):
                st = _stat_cached(p)
                val = st.st_ctime_ns if st is not None else 0
                return -val if _desc else val
            result.sort(key=get_ctime)
        elif sk == "type":
            def get_type(p: Path, _desc=is_desc):
                val = 1 if p.suffix.lower() in MediaOrganizer.VIDEO_EXTENSIONS else 0
                return -val if _desc else val
            result.sort(key=get_type)
        elif sk == "name":
            def get_name(p: Path, _desc=is_desc):
                return str(p).lower()
            result.sort(key=get_name, reverse=is_desc)

    return result
