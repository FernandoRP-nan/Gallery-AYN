"""Fecha original EXIF (DateTimeOriginal, tag 36867) para agrupación de paquetes."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from .media_organizer import MediaOrganizer

EXIF_DATETIME_ORIGINAL = 36867
EXIF_DATETIME = 306

_EXIF_IMAGE_EXTENSIONS = frozenset(
    ext for ext in MediaOrganizer.IMAGE_EXTENSIONS if ext not in {".svg"}
)


def _parse_exif_datetime(raw: str) -> int | None:
    text = str(raw or "").strip()
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return int(datetime.strptime(text, fmt).timestamp() * 1_000_000_000)
        except ValueError:
            continue
    return None


@lru_cache(maxsize=16384)
def path_exif_timestamp_ns(path_str: str) -> int | None:
    """Ns desde epoch; None si no hay EXIF legible."""
    path = Path(path_str)
    if path.suffix.lower() not in _EXIF_IMAGE_EXTENSIONS:
        return None
    try:
        from PIL import Image

        with Image.open(path) as im:
            exif = im.getexif()
            if not exif:
                return None
            for tag in (EXIF_DATETIME_ORIGINAL, EXIF_DATETIME):
                val = exif.get(tag)
                if not val:
                    continue
                ns = _parse_exif_datetime(str(val))
                if ns is not None:
                    return ns
    except OSError:
        return None
    except Exception:
        return None
    return None


def path_photo_timestamp_ns(path_str: str) -> int:
    """EXIF DateTimeOriginal/DateTime; respaldo ctime → mtime (ns)."""
    exif = path_exif_timestamp_ns(path_str)
    if exif is not None:
        return exif
    path = Path(path_str)
    try:
        st = path.stat()
    except OSError:
        return 0
    ctime = int(getattr(st, "st_ctime_ns", 0) or 0)
    mtime = int(getattr(st, "st_mtime_ns", 0) or 0)
    if ctime > 0:
        return ctime
    return mtime


def path_exif_year_month(path_str: str) -> tuple[int, int]:
    """Año y mes desde EXIF (o respaldo fs); (1970, 1) si no hay fecha."""
    ns = path_photo_timestamp_ns(path_str)
    if ns <= 0:
        return 1970, 1
    dt = datetime.fromtimestamp(ns / 1_000_000_000)
    return dt.year, dt.month


def path_exif_year_month_int(path_str: str) -> int:
    """Clave YYYYMM para ordenar por mes EXIF."""
    year, month = path_exif_year_month(path_str)
    return year * 100 + month


def prefetch_exif_timestamps(paths: list[Path], *, max_workers: int = 8) -> None:
    """Precarga EXIF en caché (escaneos grandes)."""
    if not paths:
        return
    keys = [str(p) for p in paths]

    def _one(p: Path) -> None:
        path_exif_timestamp_ns(str(p))

    if len(keys) <= 128:
        for p in paths:
            _one(p)
        return
    workers = max(2, min(max_workers, 12))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(_one, paths, chunksize=max(32, len(paths) // (workers * 8))))
