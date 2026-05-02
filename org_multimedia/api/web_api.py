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


from .bridge_system import SystemBridgeMixin
from .bridge_organizer import OrganizerBridgeMixin
from .bridge_gallery import GalleryBridgeMixin
from .bridge_selection import SelectionBridgeMixin
from .bridge_destinations import DestinationsBridgeMixin
from .bridge_editor import EditorBridgeMixin

class WebApi(SystemBridgeMixin, OrganizerBridgeMixin, GalleryBridgeMixin, SelectionBridgeMixin, DestinationsBridgeMixin, EditorBridgeMixin):
    def __init__(self) -> None:
        self.settings = load_app_settings()
        self.gallery_folder: Path | None = None
        self.ordered_paths: list[Path] = []
        self.subfolders: list[Path] = []
        self.gallery_total_bytes = 0
        self._gallery_bytes_gen = 0
        self.selected: set[Path] = set()
        self.gallery_page = 0
        self.gallery_unlimited_loaded = 0
        self.lock = threading.RLock()
        # Candado solo para la caché de miniaturas (los workers no deben tomar `self.lock` mientras el hilo principal construye la página).
        self._thumb_cache_lock = threading.Lock()
        self._organizer_job: dict | None = None
        self._last_gallery_move: tuple[Path, Path] | None = None
        # Caché (ruta, tamaño, perfil) -> (mtime, data_url)
        self._thumb_cache: dict[tuple[str, int, str], tuple[float, str | None]] = {}
        # [start, end), ruta de carpeta de sección, etiqueta (solo modo agrupar por carpeta).
        self._gallery_section_spans: list[tuple[int, int, str, str]] = []
        # [start, end), clave YYYY-MM, etiqueta visible (solo modo línea de tiempo).
        self._gallery_timeline_spans: list[tuple[int, int, str, str]] = []