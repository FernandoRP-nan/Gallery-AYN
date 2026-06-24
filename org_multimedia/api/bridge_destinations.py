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

class DestinationsBridgeMixin:
    def destination_move_selected(self, dest_path: str) -> dict:
        dest_dir = Path(dest_path).expanduser().resolve()
        dest_dir.mkdir(parents=True, exist_ok=True)
        moved = 0
        errors = 0
        moved_paths: list[str] = []
        with self.lock:
            for src in list(self.selected):
                try:
                    target = ensure_unique_destination(dest_dir / src.name)
                    if src.resolve() == target.resolve():
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(src), str(target))
                    moved += 1
                    moved_paths.append(str(src))
                except Exception:
                    errors += 1
            self.selected.clear()
        if errors > 0:
            data = self.gallery_reload(clear_thumb_cache=False)
        else:
            data = self.gallery_reindex_delta(moved_paths)
        data["moveResult"] = {"moved": moved, "errors": errors}
        return data

    def destination_move_paths(self, src_paths: list[str], dest_path: str) -> dict:
        """Mueve rutas explícitas a un destino (útil para cola en frontend)."""
        dest_dir = Path(dest_path).expanduser().resolve()
        dest_dir.mkdir(parents=True, exist_ok=True)
        moved = 0
        errors = 0
        moved_paths: list[str] = []
        unique_raw: list[str] = []
        seen: set[str] = set()
        for raw in src_paths or []:
            s = str(raw).strip()
            if not s or s in seen:
                continue
            seen.add(s)
            unique_raw.append(s)
        with self.lock:
            for raw in unique_raw:
                try:
                    src = Path(raw).expanduser().resolve()
                    if not src.is_file():
                        continue
                    target = ensure_unique_destination(dest_dir / src.name)
                    if src.resolve() == target.resolve():
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(src), str(target))
                    moved += 1
                    moved_paths.append(str(src))
                except Exception:
                    errors += 1
            moved_src = {Path(x).expanduser().resolve() for x in unique_raw}
            self.selected = {p for p in self.selected if p not in moved_src and p.exists()}
        if errors > 0:
            data = self.gallery_reload(clear_thumb_cache=False)
        else:
            data = self.gallery_reindex_delta(moved_paths)
        data["moveResult"] = {"moved": moved, "errors": errors}
        return data

    def destination_preview(self, dest_path: str, scale: float, width: int) -> dict:
        folder = Path(dest_path).expanduser().resolve()
        paths = scan_images_flat(folder) if folder.is_dir() else []
        thumb = _thumb_px_from_dest_scale(float(scale))
        cols = max(2, min(10, int(max(400, width) // (thumb + 34))))
        items = []
        for p in paths:
            items.append(
                {
                    "name": p.name,
                    "path": str(p),
                    "thumbDataUrl": _dest_thumb_jpeg_data_url_contain(
                        p, max(48, int(thumb * 0.55)), quality=40
                    ),
                    "thumbQuality": "lq",
                }
            )
        return {"items": items, "cols": cols}

    def destination_thumb_hq(self, path: str, scale: float) -> dict:
        p = Path(path).expanduser().resolve()
        thumb = _thumb_px_from_dest_scale(float(scale))
        return {
            "path": str(p),
            "thumbDataUrl": _dest_thumb_jpeg_data_url_contain(p, int(round(thumb * 1.35)), quality=96),
            "thumbQuality": "hq",
        }

    def destination_move_from_preview(self, src_paths: list[str]) -> dict:
        """Mueve imágenes seleccionadas del modal de destino a la carpeta cargada en galería."""
        if not self.gallery_folder or not self.gallery_folder.is_dir():
            raise ValueError("No hay carpeta cargada en Ruta para recibir los archivos.")
        dest_dir = self.gallery_folder.resolve()
        moved = 0
        errors = 0
        unique_raw = []
        seen: set[str] = set()
        for raw in src_paths or []:
            s = str(raw).strip()
            if not s or s in seen:
                continue
            seen.add(s)
            unique_raw.append(s)
        with self.lock:
            for raw in unique_raw:
                try:
                    src = Path(raw).expanduser().resolve()
                    if not src.is_file():
                        continue
                    if src.parent.resolve() == dest_dir:
                        continue
                    target = ensure_unique_destination(dest_dir / src.name)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(src), str(target))
                    moved += 1
                except Exception:
                    errors += 1
        data = self.gallery_reload(clear_thumb_cache=False)
        data["moveResult"] = {"moved": moved, "errors": errors}
        return data

    def _destinations_list(self) -> list:
        """Si en JSON quedó null o tipo inválido, setdefault no crea lista y falla el append."""
        d = self.settings.get("destinations")
        if not isinstance(d, list):
            d = []
            self.settings["destinations"] = d
        return d

    def destinations_get(self) -> dict:
        # Solo dicts planos serializables (evita sorpresas en el bridge Qt).
        out: list[dict[str, str]] = []
        for x in self._destinations_list():
            if isinstance(x, dict):
                out.append(
                    {
                        "label": str(x.get("label", "")),
                        "path": str(x.get("path", "")),
                    }
                )
        return {"destinations": out}

    def destinations_add(self, label: str, path: str) -> dict:
        p = str(Path(path).expanduser().resolve())
        label = label.strip() or Path(p).name
        dests = self._destinations_list()
        for x in dests:
            if isinstance(x, dict) and str(x.get("path", "")) == p:
                return self.destinations_get()
        dests.append({"label": label, "path": p})
        save_app_settings(self.settings)
        return self.destinations_get()

    def destinations_remove(self, idx: int) -> dict:
        dests = self._destinations_list()
        if 0 <= idx < len(dests):
            dests.pop(idx)
            save_app_settings(self.settings)
        return self.destinations_get()

    def destinations_edit(self, idx: int, label: str, path: str) -> dict:
        dests = self._destinations_list()
        if 0 <= idx < len(dests):
            p = str(Path(path).expanduser().resolve())
            label = label.strip() or Path(p).name
            dests[idx] = {"label": label, "path": p}
            save_app_settings(self.settings)
        return self.destinations_get()

    def destinations_reorder(self, from_idx: int, to_idx: int) -> dict:
        dests = self._destinations_list()
        n = len(dests)
        if n <= 1:
            return self.destinations_get()
        if not (0 <= from_idx < n and 0 <= to_idx < n):
            return self.destinations_get()
        if from_idx == to_idx:
            return self.destinations_get()
        # Reordenar sin perder contenido ni metadatos del destino.
        item = dests.pop(from_idx)
        dests.insert(to_idx, item)
        save_app_settings(self.settings)
        return self.destinations_get()
