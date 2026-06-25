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

from ..core.fs_path import normalize_path_string, resolve_dir_path

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

class SystemBridgeMixin:
    def get_initial_state(self) -> dict:
        dest_payload = self._destinations_payload() if hasattr(self, "_destinations_payload") else {"destinations": [], "toolbarFolderId": ""}
        marker_payload = self._markers_payload() if hasattr(self, "_markers_payload") else {"markers": [], "toolbarFolderId": "", "pinnedFolders": []}
        return {
            "settings": self.settings,
            "gallery": self._gallery_state(),
            "destinations": dest_payload.get("destinations", []),
            "destToolbarFolderId": dest_payload.get("toolbarFolderId", ""),
            "markers": marker_payload.get("markers", []),
            "markerToolbarFolderId": marker_payload.get("toolbarFolderId", ""),
            "pinnedFolders": marker_payload.get("pinnedFolders", []),
        }

    def settings_patch(self, data: dict) -> dict:
        self.settings.update(data)
        save_app_settings(self.settings)
        return {"settings": self.settings}

    def dialog_pick_folder(self, start_path: str = "") -> dict:
        """Abre el selector de carpeta del sistema (ventana PyWebView)."""
        try:
            import webview
            from webview import FileDialog
        except Exception as exc:
            return {"path": None, "cancelled": True, "error": str(exc)}
        if not webview.windows:
            return {"path": None, "cancelled": True, "error": "sin_ventana"}
        win = webview.windows[0]
        directory = ""
        raw = (start_path or "").strip()
        if raw:
            try:
                expanded = resolve_dir_path(raw)
                directory = str(expanded)
            except (OSError, ValueError):
                directory = ""
        result = win.create_file_dialog(FileDialog.FOLDER, directory=directory)
        if not result:
            return {"path": None, "cancelled": True}
        first = result[0] if isinstance(result, (list, tuple)) else result
        return {"path": str(first), "cancelled": False}

    def ping(self) -> dict:
        return {"ok": True, "ts": time.time()}

    def _merge_recent_folder(self, path_str: str) -> None:
        """Mantiene hasta 20 rutas únicas (más reciente primero) para acceso rápido en la UI."""
        try:
            p = str(Path(path_str).resolve())
        except (OSError, ValueError):
            return
        if not p:
            return
        prev = self.settings.get("gallery_recent_folders")
        if not isinstance(prev, list):
            prev = []
        unique = [str(x) for x in prev if str(x) != p]
        unique.insert(0, p)
        self.settings["gallery_recent_folders"] = unique[:20]

    def _pinned_folders(self) -> list[str]:
        if hasattr(self, "_markers_tree"):
            from ..core.item_tree import flatten_marker_paths

            return flatten_marker_paths(self._markers_tree())
        pins = self.settings.get("gallery_pinned_folders")
        if not isinstance(pins, list):
            pins = []
            self.settings["gallery_pinned_folders"] = pins
        return [str(x) for x in pins if str(x).strip()]

    def gallery_pin_folder(self, raw_path: str) -> dict:
        if hasattr(self, "markers_add"):
            return self.markers_add(raw_path, "", "")
        p = str(resolve_dir_path(raw_path))
        pins = self._pinned_folders()
        if p not in pins:
            pins.insert(0, p)
            self.settings["gallery_pinned_folders"] = pins[:40]
            save_app_settings(self.settings)
        return {"pinnedFolders": list(self.settings.get("gallery_pinned_folders", []))}

    def gallery_unpin_folder(self, raw_path: str) -> dict:
        p = str(resolve_dir_path(raw_path))
        pins = [x for x in self._pinned_folders() if x != p]
        self.settings["gallery_pinned_folders"] = pins
        save_app_settings(self.settings)
        return {"pinnedFolders": pins}

    def gallery_open_external(self, path: str) -> dict:
        """Abre el archivo con la aplicación predeterminada del sistema (p. ej. Dragon Player)."""
        import subprocess

        from ..core.fs_path import resolve_file_path

        try:
            p = resolve_file_path(path)
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}
        try:
            subprocess.Popen(
                ["xdg-open", str(p)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
