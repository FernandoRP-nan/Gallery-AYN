"""Caché en disco de miniaturas LQ (JPEG) para reinicios más rápidos."""

from __future__ import annotations

import base64
import hashlib
import os
from pathlib import Path


def _cache_root() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return Path(base) / "organizador_multimedia" / "thumbs_lq"


def thumb_disk_cache_enabled() -> bool:
    from .settings import load_app_settings

    return bool(load_app_settings().get("gallery_thumb_disk_cache_enabled", False))


def _file_stat_key(path: Path) -> tuple[int, int]:
    try:
        st = path.stat()
        return int(st.st_mtime_ns), int(st.st_size)
    except OSError:
        return 0, 0


def make_thumb_cache_id(
    path: Path,
    *,
    variant: str,
    size: int,
    max_w: int,
    max_h: int,
    quality: int,
) -> str:
    mtime_ns, size_b = _file_stat_key(path)
    payload = "|".join(
        [
            str(path.resolve()),
            str(mtime_ns),
            str(size_b),
            variant,
            str(size),
            str(max_w),
            str(max_h),
            str(quality),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def _cache_file(cache_id: str) -> Path:
    return _cache_root() / f"{cache_id}.jpg"


def load_thumb_jpeg(cache_id: str) -> bytes | None:
    cache_path = _cache_file(cache_id)
    if not cache_path.is_file():
        return None
    try:
        data = cache_path.read_bytes()
        return data if len(data) >= 32 else None
    except OSError:
        return None


def save_thumb_jpeg(cache_id: str, jpeg_bytes: bytes) -> None:
    if not jpeg_bytes or len(jpeg_bytes) < 32:
        return
    root = _cache_root()
    root.mkdir(parents=True, exist_ok=True)
    cache_path = _cache_file(cache_id)
    tmp = cache_path.with_suffix(".jpg.part")
    try:
        tmp.write_bytes(jpeg_bytes)
        tmp.replace(cache_path)
    except OSError:
        tmp.unlink(missing_ok=True)


def jpeg_bytes_to_data_url(jpeg_bytes: bytes) -> str:
    payload = base64.b64encode(jpeg_bytes).decode("ascii")
    return f"data:image/jpeg;base64,{payload}"
