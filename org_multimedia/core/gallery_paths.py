"""Escaneo de carpetas para la galeria."""

from __future__ import annotations

import os
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .media_organizer import MediaOrganizer

# Imágenes + vídeo para la galería web (misma lista ordenada que `sort_image_paths`).
GALLERY_MEDIA_EXTENSIONS: frozenset[str] = frozenset(
    MediaOrganizer.IMAGE_EXTENSIONS | MediaOrganizer.VIDEO_EXTENSIONS
)

_OUTER_QUOTES = ('"', "'")
_BROWSER_COPY_SUFFIX_RE = re.compile(r"\s+\(\d+\)$")
# Series «X (Y)» / «X (Y)_Z»: no son sufijo de copia del navegador.
_SPACED_SERIES_STEM_RE = re.compile(r"^\d+\s+\(\d+\)(?:_\d+)?$")


def normalize_filename_for_sort(name: str) -> str:
    """Quita comillas externas y sufijos « (n) » de copia del navegador."""
    text = str(name or "").strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in _OUTER_QUOTES:
        text = text[1:-1].strip()
    if not text:
        return text
    path = Path(text)
    stem = path.stem
    if not _SPACED_SERIES_STEM_RE.fullmatch(stem):
        stem = _BROWSER_COPY_SUFFIX_RE.sub("", stem)
    return f"{stem}{path.suffix}" if path.suffix else stem


def natural_sort_key(text: str) -> tuple:
    """Clave de orden numérico natural (p. ej. 2.jpg antes que 10.jpg)."""
    parts = re.split(r"(\d+)", normalize_filename_for_sort(text).casefold())
    key: list[tuple[int, int | str]] = []
    for part in parts:
        if not part:
            continue
        if part.isdigit():
            key.append((0, int(part)))
        else:
            key.append((1, part))
    return tuple(key)


def path_natural_sort_key(path: Path) -> tuple:
    out: list[tuple[int, int | str]] = []
    for i, part in enumerate(path.parts):
        if i:
            out.append((1, "/"))
        out.extend(natural_sort_key(part))
    return tuple(out)


def smart_prefix_bucket(name: str) -> str:
    """Prefijo de sección (legado); preferir work_packages para agrupación."""
    from .work_packages import stem_structure_fingerprint

    norm = normalize_filename_for_sort(name)
    stem = Path(norm).stem if norm else ""
    return stem_structure_fingerprint(stem) if stem else "?"


def smart_prefix_section_sort_key(bucket: str) -> tuple[int, int | str]:
    """Orden de secciones: numéricas, letras, resto."""
    b = str(bucket or "?")
    if b.isdigit():
        return (0, int(b))
    if len(b) == 1 and b.isalpha():
        return (1, b.upper())
    return (2, b.casefold())


def list_subdirs(root: Path) -> list[Path]:
    out: list[Path] = []
    try:
        for p in root.iterdir():
            if p.is_dir():
                out.append(p)
    except OSError:
        pass
    out.sort(key=path_natural_sort_key)
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
    out.sort(key=lambda p: natural_sort_key(str(p.relative_to(base))))
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
    out.sort(key=path_natural_sort_key)
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
    out.sort(key=path_natural_sort_key)
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
    out.sort(key=path_natural_sort_key)
    return out


def scan_all_files_flat(root: Path) -> list[Path]:
    """Archivos visibles en esta carpeta (no recursivo, excluye ocultos)."""
    out: list[Path] = []
    try:
        with os.scandir(root) as it:
            for entry in it:
                if not entry.is_file(follow_symlinks=False):
                    continue
                if entry.name.startswith("."):
                    continue
                out.append(Path(entry.path))
    except OSError:
        pass
    out.sort(key=path_natural_sort_key)
    return out


def scan_all_files_recursive(root: Path) -> list[Path]:
    """Todos los archivos visibles bajo `root` (incluye subcarpetas, excluye ocultos)."""
    base = root.resolve()
    out: list[Path] = []
    try:
        for p in base.rglob("*"):
            if not p.is_file():
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
    out.sort(key=path_natural_sort_key)
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


class InvertedString:
    """Clase de utilidad para invertir la comparación de cadenas en tuplas compuestas."""
    def __init__(self, s: str):
        self.s = s
    def __lt__(self, other: InvertedString) -> bool:
        return self.s > other.s
    def __le__(self, other: InvertedString) -> bool:
        return self.s >= other.s
    def __gt__(self, other: InvertedString) -> bool:
        return self.s < other.s
    def __ge__(self, other: InvertedString) -> bool:
        return self.s <= other.s
    def __eq__(self, other: InvertedString) -> bool:
        return self.s == other.s
    def __ne__(self, other: InvertedString) -> bool:
        return self.s != other.s


def _natural_sort_directed(path: Path, desc: bool) -> tuple:
    parts = list(natural_sort_key(normalize_filename_for_sort(path.name)))
    if not desc:
        return tuple(parts)
    inverted: list[tuple[int, int | str]] = []
    for kind, val in parts:
        if kind == 0 and isinstance(val, int):
            inverted.append((0, -val))
        else:
            inverted.append((kind, val))
    return tuple(inverted)


def sort_mode_uses_exif(mode: str) -> bool:
    """True si el orden compuesto requiere leer EXIF."""
    for m_raw in (mode or "").split(","):
        m = m_raw.strip().split(":")[0].lower()
        if m in ("exif", "exifdate", "photo", "foto", "captura", "exif_month", "month_exif", "mes_exif", "mes"):
            return True
    return False


def sort_image_paths(
    paths: list[Path],
    mode: str,
    *,
    stat_workers: int | None = None,
    allow_cluster: bool = True,
    sort_config: WorkPackageSortConfig | None = None,
) -> list[Path]:
    """Orden compuesto por tupla: cada criterio con dirección independiente."""
    from .work_packages import (
        WorkPackageSortConfig,
        cluster_work_packages,
        directed_number_key,
        filename_numeric_indices,
        flatten_work_packages,
        grouping_stem,
        should_cluster_after_sort,
    )

    cfg = sort_config or WorkPackageSortConfig()
    cfg = cfg.with_paths(paths) if cfg.use_dynamic_regex else cfg

    raw_modes = [x.strip().lower() for x in (mode or "name").split(",")]

    sort_keys: list[tuple[str, bool]] = []
    for m_raw in raw_modes:
        parts = m_raw.split(":")
        m = parts[0]
        direction = parts[1] if len(parts) > 1 else None

        if m in ("mtime", "date", "fecha"):
            sort_keys.append(("mtime", direction != "asc"))
        elif m in ("ctime", "creacion", "creation", "created"):
            sort_keys.append(("ctime", direction != "asc"))
        elif m in ("exif", "exifdate", "photo", "foto", "captura"):
            sort_keys.append(("exif", direction != "asc"))
        elif m in ("exif_month", "month_exif", "mes_exif", "mes"):
            sort_keys.append(("exif_month", direction != "asc"))
        elif m in ("type", "tipo"):
            sort_keys.append(("type", direction == "desc"))
        elif m in ("name_base", "base", "num_base", "principal"):
            sort_keys.append(("name_base", direction == "desc"))
        elif m in ("name_suffix", "suffix", "num_suffix", "secundario", "parentesis"):
            sort_keys.append(("name_suffix", direction == "desc"))
        elif m in ("name", "nombre"):
            sort_keys.append(("name", direction == "desc"))
        elif m in ("name_lex", "normal", "lexicografico"):
            sort_keys.append(("name_lex", direction == "desc"))
        elif m in ("random", "aleatorio", "azar"):
            sort_keys.append(("random", direction == "desc"))

    if not sort_keys:
        sort_keys = [("name", False)]

    if not any(k[0] in ("name", "name_lex", "random") for k in sort_keys):
        sort_keys.append(("name", False))

    stat_cache: dict[Path, os.stat_result | None] = {}
    needs_stat = any(sk in ("mtime", "ctime") for sk, _ in sort_keys)
    needs_exif = any(sk in ("exif", "exif_month") for sk, _ in sort_keys)
    if needs_stat:
        _prefetch_path_stats(paths, stat_cache, max_workers=stat_workers)
    if needs_exif:
        from .image_exif import prefetch_exif_timestamps

        prefetch_exif_timestamps(paths, max_workers=stat_workers or 8)

    def _stat_cached(p: Path) -> os.stat_result | None:
        if p not in stat_cache:
            try:
                stat_cache[p] = p.stat()
            except OSError:
                stat_cache[p] = None
        return stat_cache[p]

    def _composite_key(p: Path) -> tuple:
        out: list = []
        stem = grouping_stem(p)
        base, suffix, tertiary = filename_numeric_indices(stem, cfg)
        for sk, is_desc in sort_keys:
            if sk == "name_base":
                out.extend(directed_number_key(base, is_desc))
            elif sk == "name_suffix":
                out.extend(directed_number_key(suffix, is_desc))
                if tertiary:
                    out.extend(directed_number_key(tertiary, is_desc))
            elif sk == "name":
                out.append(_natural_sort_directed(p, is_desc))
            elif sk == "name_lex":
                val = normalize_filename_for_sort(p.name).casefold()
                out.append(val if not is_desc else InvertedString(val))
            elif sk == "random":
                import hashlib
                h = hashlib.md5(p.name.encode("utf-8")).hexdigest()
                out.append(h if not is_desc else InvertedString(h))
            elif sk == "mtime":
                st = _stat_cached(p)
                val = st.st_mtime_ns if st is not None else 0
                out.append(-val if is_desc else val)
            elif sk == "ctime":
                st = _stat_cached(p)
                val = st.st_ctime_ns if st is not None else 0
                out.append(-val if is_desc else val)
            elif sk == "exif":
                from .image_exif import path_photo_timestamp_ns

                val = path_photo_timestamp_ns(str(p))
                out.append(-val if is_desc else val)
            elif sk == "exif_month":
                from .image_exif import path_exif_year_month_int

                val = path_exif_year_month_int(str(p))
                out.append(-val if is_desc else val)
            elif sk == "type":
                val = 1 if p.suffix.lower() in MediaOrganizer.VIDEO_EXTENSIONS else 0
                out.append(-val if is_desc else val)
        return tuple(out)

    result = sorted(paths, key=_composite_key)

    if should_cluster_after_sort(sort_keys, allow_cluster=allow_cluster) and not cfg.use_dynamic_regex:
        result = flatten_work_packages(
            cluster_work_packages(result, sort_config=cfg),
            sort_config=cfg,
        )

    return result
