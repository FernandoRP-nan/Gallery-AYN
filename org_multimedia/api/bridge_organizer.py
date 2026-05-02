from __future__ import annotations

"""API bridge para PyWebView (frontend web -> backend Python)."""


import base64

import datetime

import io

import os

import shutil

import threading

import time

from concurrent.futures import ThreadPoolExecutor

from pathlib import Path

from ..core.fs_utils import ensure_unique_destination

from ..core.gallery_images import make_thumbnail_photoimage

from ..core.gallery_paths import (
    list_subdirs,
    scan_images_flat,
    scan_media_flat,
    scan_media_recursive,
    sort_image_paths,
)

from ..core.section_color import accent_hex_from_paths

_MONTH_NAMES_ES = (
    "",
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)

from ..core.media_organizer import MediaOrganizer

from ..core.settings import load_app_settings, save_app_settings

try:
    from PIL import Image, ImageOps
except Exception:  # pragma: no cover
    Image = None
    ImageOps = None

def _save_pil_to_path(im: Image.Image, path: Path) -> None:
    """Guarda una imagen PIL respetando el tipo de archivo cuando es posible."""
    if Image is None:
        raise RuntimeError("Pillow no disponible")
    ext = path.suffix.lower()
    if ext in (".jpg", ".jpeg"):
        rgb = im.convert("RGB") if im.mode in ("RGBA", "P", "LA") else im
        rgb.save(path, format="JPEG", quality=95, optimize=True)
    elif ext == ".png":
        im.save(path, format="PNG", optimize=True)
    elif ext == ".webp":
        im.save(path, format="WEBP", quality=90, method=4)
    elif ext in (".bmp",):
        im.convert("RGB").save(path, format="BMP")
    elif ext in (".gif",):
        im.save(path, format="GIF", save_all=True)
    elif ext in (".tif", ".tiff"):
        im.save(path, format="TIFF", compression="tiff_lzw")
    else:
        im.save(path)

def _thumb_px_from_gallery_scale(scale: float) -> int:
    """Escala lineal 0.01–2.25 → ~80–340 px (zoom-out máximo en miniaturas)."""
    lo, hi = 0.01, 2.25
    px_min, px_max = 48, 400
    s = max(lo, min(hi, float(scale)))
    return int(round(px_min + (s - lo) / (hi - lo) * (px_max - px_min)))

def _thumb_px_from_dest_scale(scale: float) -> int:
    """Vista previa de carpeta destino (rango de escala distinto en la UI)."""
    lo, hi = 0.7, 2.1
    px_min, px_max = 88, 360
    s = max(lo, min(hi, float(scale)))
    return int(round(px_min + (s - lo) / (hi - lo) * (px_max - px_min)))

def _img_to_data_url(path: Path, size: tuple[int, int]) -> str | None:
    if Image is None:
        return None
    try:
        with Image.open(path) as im:
            im = im.convert("RGBA")
            if ImageOps is not None:
                im = ImageOps.fit(im, size, Image.Resampling.LANCZOS, centering=(0.5, 0.5))
            else:
                im.thumbnail(size, Image.Resampling.LANCZOS)
            bio = io.BytesIO()
            im.save(bio, format="PNG")
            payload = base64.b64encode(bio.getvalue()).decode("ascii")
            return f"data:image/png;base64,{payload}"
    except Exception:
        return None

def _img_to_data_url_contain(path: Path, max_w: int, max_h: int) -> str | None:
    """Vista previa mostrando la imagen completa (sin recorte a 1:1)."""
    if Image is None:
        return None
    try:
        mw, mh = max(1, int(max_w)), max(1, int(max_h))
        with Image.open(path) as im:
            im = im.convert("RGBA")
            im.thumbnail((mw, mh), Image.Resampling.LANCZOS)
            bio = io.BytesIO()
            im.save(bio, format="PNG")
            payload = base64.b64encode(bio.getvalue()).decode("ascii")
            return f"data:image/png;base64,{payload}"
    except Exception:
        return None

def _thumb_jpeg_data_url_square(path: Path, size: int, quality: int = 90) -> str | None:
    """Miniatura cuadrada para la rejilla; JPEG reduce mucho el tamaño frente a PNG."""
    if Image is None:
        return None
    try:
        with Image.open(path) as im:
            im = im.convert("RGB")
            if ImageOps is not None:
                im = ImageOps.fit(im, (size, size), Image.Resampling.LANCZOS, centering=(0.5, 0.5))
            else:
                im.thumbnail((size, size), Image.Resampling.LANCZOS)
            bio = io.BytesIO()
            im.save(bio, format="JPEG", quality=quality, optimize=True)
            payload = base64.b64encode(bio.getvalue()).decode("ascii")
            return f"data:image/jpeg;base64,{payload}"
    except Exception:
        return None

def _dest_thumb_jpeg_data_url_contain(path: Path, size: int, quality: int = 90) -> str | None:
    """Miniatura modal destino: encaja en size×size manteniendo proporción."""
    if Image is None:
        return None
    try:
        with Image.open(path) as im:
            im = im.convert("RGB")
            im.thumbnail((size, size), Image.Resampling.LANCZOS)
            bio = io.BytesIO()
            im.save(bio, format="JPEG", quality=quality, optimize=True)
            payload = base64.b64encode(bio.getvalue()).decode("ascii")
            return f"data:image/jpeg;base64,{payload}"
    except Exception:
        return None

class OrganizerBridgeMixin:
    def organizer_start(self, root_path: str, options: dict) -> dict:
        if self._organizer_job and self._organizer_job.get("running"):
            return {"ok": False, "error": "Ya hay una tarea en ejecución."}
        src = Path(os.path.expandvars(os.path.expanduser(root_path))).resolve()
        if not src.is_dir():
            return {"ok": False, "error": "Ruta inválida."}
        cancel_event = threading.Event()
        job: dict = {
            "running": True,
            "progress": {"current": 0, "total": 0, "detail": "Iniciando..."},
            "done": None,
            "cancelEvent": cancel_event,
        }
        self._organizer_job = job

        def worker() -> None:
            try:
                organizer = MediaOrganizer(
                    src,
                    include_organized_scan=bool(options.get("includeOrganized", False)),
                    include_comics_scan=bool(options.get("includeComics", False)),
                    include_pending_scan=bool(options.get("includePending", False)),
                    remove_duplicate_images=bool(options.get("removeDuplicates", False)),
                    group_similar_images=bool(options.get("groupSimilarImages", False)),
                )

                def on_progress(cur: int, total: int, detail: str) -> None:
                    job["progress"] = {"current": cur, "total": total, "detail": detail}

                stats = organizer.organize(progress_callback=on_progress, cancel_event=cancel_event)
                job["done"] = {"cancelled": organizer.cancel_requested, "stats": stats.__dict__}
            except Exception as exc:
                job["done"] = {"cancelled": False, "error": str(exc), "stats": None}
            finally:
                job["running"] = False

        threading.Thread(target=worker, daemon=True).start()
        return {"ok": True}

    def organizer_cancel(self) -> dict:
        if self._organizer_job and self._organizer_job.get("cancelEvent") is not None:
            self._organizer_job["cancelEvent"].set()
        return {"ok": True}

    def organizer_status(self) -> dict:
        if not self._organizer_job:
            return {"running": False, "progress": {"current": 0, "total": 0, "detail": "Sin tarea"}, "done": None}
        out = dict(self._organizer_job)
        out.pop("cancelEvent", None)
        return out
