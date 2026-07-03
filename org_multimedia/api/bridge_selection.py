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

from ..core.fs_path import resolve_dir_path, resolve_existing_path, resolve_file_path
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

class SelectionBridgeMixin:
    def gallery_toggle_select(self, path: str) -> dict:
        p = Path(path)
        with self.lock:
            if p in self.selected:
                self.selected.discard(p)
            else:
                self.selected.add(p)
            return {"state": self._gallery_state(), "items": self._build_gallery_items()}

    def gallery_apply_selection_delta(self, add_paths: list[str], remove_paths: list[str]) -> dict:
        """Aplica altas/bajas de selección en lote para gestos de rango (A->B)."""
        with self.lock:
            for raw in add_paths or []:
                s = str(raw).strip()
                if not s:
                    continue
                self.selected.add(Path(s))
            for raw in remove_paths or []:
                s = str(raw).strip()
                if not s:
                    continue
                self.selected.discard(Path(s))
            return {"state": self._gallery_state(), "items": self._build_gallery_items()}

    def gallery_select_page(self) -> dict:
        with self.lock:
            s, e = self._slice()
            self.selected = set(self.ordered_paths[s:e])
            return {"state": self._gallery_state(), "items": self._build_gallery_items()}

    def gallery_clear_selection(self) -> dict:
        with self.lock:
            self.selected.clear()
            return {"state": self._gallery_state(), "items": self._build_gallery_items()}

    def gallery_invert_selection(self) -> dict:
        with self.lock:
            self.selected = {p for p in self.ordered_paths if p not in self.selected}
            return {"state": self._gallery_state(), "items": self._build_gallery_items()}

    def gallery_delete_selected(self) -> dict:
        """Elimina del disco las imágenes seleccionadas en la galería."""
        deleted = 0
        errors = 0
        deleted_paths: list[str] = []
        with self.lock:
            for src in list(self.selected):
                try:
                    if src.is_dir():
                        shutil.rmtree(src)
                        deleted += 1
                        deleted_paths.append(str(src))
                    elif src.is_file():
                        src.unlink()
                        deleted += 1
                        deleted_paths.append(str(src))
                except Exception:
                    errors += 1
            self.selected.clear()
        if errors > 0:
            data = self.gallery_reload(clear_thumb_cache=False)
        else:
            data = self.gallery_reindex_delta(deleted_paths)
        data["deleteResult"] = {"deleted": deleted, "errors": errors}
        return data

    def gallery_delete_paths(self, paths: list[str]) -> dict:
        """Elimina una lista explícita de rutas (archivos o carpetas)."""
        deleted = 0
        errors = 0
        deleted_paths: list[str] = []
        folder_deleted = False
        unique_raw = []
        seen: set[str] = set()
        for raw in paths or []:
            s = str(raw).strip()
            if not s or s in seen:
                continue
            seen.add(s)
            unique_raw.append(s)
        with self.lock:
            for raw in unique_raw:
                try:
                    try:
                        src = resolve_file_path(raw)
                    except ValueError:
                        src = resolve_dir_path(raw)
                    if src.is_dir():
                        shutil.rmtree(src)
                        deleted += 1
                        folder_deleted = True
                    elif src.is_file():
                        src.unlink()
                        deleted += 1
                        deleted_paths.append(str(src))
                except Exception:
                    errors += 1
            self.selected = {p for p in self.selected if p.exists()}
        if folder_deleted or errors > 0:
            data = self.gallery_reload(clear_thumb_cache=False)
        else:
            data = self.gallery_reindex_delta(deleted_paths)
        data["deleteResult"] = {"deleted": deleted, "errors": errors}
        return data

    def gallery_move_path(self, src_path: str, dest_path: str) -> dict:
        """Mueve una sola imagen a un destino desde fullscreen."""
        moved = 0
        errors = 0
        moved_paths: list[str] = []
        src = Path(src_path).expanduser().resolve()
        dest_dir = Path(dest_path).expanduser().resolve()
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
            if src.is_file():
                target = ensure_unique_destination(dest_dir / src.name)
                if src.resolve() != target.resolve():
                    shutil.move(str(src), str(target))
                    moved = 1
                    moved_paths.append(str(src))
                    self._last_gallery_move = (target, src)
        except Exception:
            errors = 1
        if errors > 0 or moved == 0:
            data = self.gallery_reload(clear_thumb_cache=False)
        else:
            data = self.gallery_reindex_delta(moved_paths)
        data["moveResult"] = {"moved": moved, "errors": errors}
        return data

    def gallery_undo_last_move(self) -> dict:
        """Revierte el último movimiento hecho desde fullscreen."""
        moved = 0
        errors = 0
        pair = self._last_gallery_move
        if pair is not None:
            cur_path, prev_path = pair
            try:
                if cur_path.is_file():
                    prev_path.parent.mkdir(parents=True, exist_ok=True)
                    target = ensure_unique_destination(prev_path)
                    shutil.move(str(cur_path), str(target))
                    moved = 1
                self._last_gallery_move = None
            except Exception:
                errors = 1
        data = self.gallery_reload(clear_thumb_cache=False)
        data["moveResult"] = {"moved": moved, "errors": errors}
        return data

    def gallery_rename_path(self, path: str, new_name: str) -> dict:
        """Renombra archivo o carpeta (solo el nombre, no la ruta completa)."""
        raw_name = str(new_name or "").strip()
        if not raw_name:
            raise ValueError("El nombre no puede estar vacío.")
        src = resolve_existing_path(path)
        if src.is_file() and "." not in raw_name and src.suffix:
            raw_name = raw_name + src.suffix
        target = src.parent / raw_name
        if target.exists():
            raise ValueError("Ya existe un elemento con ese nombre.")
        try:
            src.rename(target)
        except OSError as exc:
            raise ValueError(f"No se pudo renombrar: {exc}") from exc
        data = self.gallery_reload(clear_thumb_cache=False)
        data["renameResult"] = {"previousPath": str(src), "newPath": str(target), "newName": target.name}
        return data

    def gallery_delete_folder(self, path: str) -> dict:
        """Elimina una carpeta y todo su contenido."""
        folder = resolve_dir_path(path)
        try:
            shutil.rmtree(folder)
        except OSError as exc:
            raise ValueError(f"No se pudo eliminar la carpeta: {exc}") from exc
        data = self.gallery_reload(clear_thumb_cache=False)
        data["deleteResult"] = {"deleted": 1, "errors": 0}
        return data
