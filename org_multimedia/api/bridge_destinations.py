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

from ..core.item_tree import (
    KIND_DEST,
    KIND_FOLDER,
    find_folder,
    get_children_list,
    migrate_flat_destinations,
    new_folder_id,
    normalize_tree,
    prune_invalid_toolbar_folder,
    remove_folder,
)
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

    def _destinations_tree(self) -> list:
        """Árbol de destinos; migra listas planas legacy al cargar."""
        raw = self.settings.get("destinations")
        if not isinstance(raw, list):
            raw = []
        tree = migrate_flat_destinations(raw)
        if tree != raw:
            self.settings["destinations"] = tree
        return tree

    def _destinations_payload(self) -> dict:
        tree = self._destinations_tree()
        toolbar_id = prune_invalid_toolbar_folder(
            tree, self.settings.get("web_dest_toolbar_folder_id")
        )
        if toolbar_id != self.settings.get("web_dest_toolbar_folder_id"):
            if toolbar_id:
                self.settings["web_dest_toolbar_folder_id"] = toolbar_id
            else:
                self.settings.pop("web_dest_toolbar_folder_id", None)
        return {
            "destinations": tree,
            "toolbarFolderId": toolbar_id or "",
        }

    def destinations_get(self) -> dict:
        return self._destinations_payload()

    def destinations_save_tree(self, tree: list) -> dict:
        self.settings["destinations"] = normalize_tree(tree if isinstance(tree, list) else [], KIND_DEST)
        save_app_settings(self.settings)
        return self._destinations_payload()

    def destinations_set_toolbar_folder(self, folder_id: str = "") -> dict:
        fid = str(folder_id or "").strip()
        tree = self._destinations_tree()
        if fid and not find_folder(tree, fid):
            fid = ""
        if fid:
            self.settings["web_dest_toolbar_folder_id"] = fid
        else:
            self.settings.pop("web_dest_toolbar_folder_id", None)
        save_app_settings(self.settings)
        return self._destinations_payload()

    def destinations_add(self, label: str, path: str, parent_id: str = "") -> dict:
        p = str(Path(path).expanduser().resolve())
        label = label.strip() or Path(p).name
        tree = self._destinations_tree()
        container = get_children_list(tree, str(parent_id or "").strip() or None)
        for x in container:
            if isinstance(x, dict) and x.get("kind") == KIND_DEST and str(x.get("path", "")) == p:
                return self._destinations_payload()
        container.append({"kind": KIND_DEST, "label": label, "path": p})
        self.settings["destinations"] = tree
        save_app_settings(self.settings)
        return self._destinations_payload()

    def destinations_remove(self, parent_id: str, idx: int) -> dict:
        tree = self._destinations_tree()
        container = get_children_list(tree, str(parent_id or "").strip() or None)
        if 0 <= int(idx) < len(container):
            container.pop(int(idx))
            self.settings["destinations"] = tree
            save_app_settings(self.settings)
        return self._destinations_payload()

    def destinations_edit(self, parent_id: str, idx: int, label: str, path: str) -> dict:
        tree = self._destinations_tree()
        container = get_children_list(tree, str(parent_id or "").strip() or None)
        i = int(idx)
        if 0 <= i < len(container):
            node = container[i]
            if isinstance(node, dict) and node.get("kind") == KIND_DEST:
                p = str(Path(path).expanduser().resolve())
                label = label.strip() or Path(p).name
                container[i] = {"kind": KIND_DEST, "label": label, "path": p}
                self.settings["destinations"] = tree
                save_app_settings(self.settings)
        return self._destinations_payload()

    def destinations_reorder(self, parent_id: str, from_idx: int, to_idx: int) -> dict:
        tree = self._destinations_tree()
        container = get_children_list(tree, str(parent_id or "").strip() or None)
        n = len(container)
        fi, ti = int(from_idx), int(to_idx)
        if n <= 1 or not (0 <= fi < n and 0 <= ti < n) or fi == ti:
            return self._destinations_payload()
        item = container.pop(fi)
        container.insert(ti, item)
        self.settings["destinations"] = tree
        save_app_settings(self.settings)
        return self._destinations_payload()

    def destinations_folder_add(self, label: str, parent_id: str = "") -> dict:
        label = (label or "").strip() or "Carpeta"
        tree = self._destinations_tree()
        container = get_children_list(tree, str(parent_id or "").strip() or None)
        folder = {"kind": KIND_FOLDER, "id": new_folder_id(), "label": label, "children": []}
        container.append(folder)
        self.settings["destinations"] = tree
        save_app_settings(self.settings)
        payload = self._destinations_payload()
        payload["folderId"] = folder["id"]
        return payload

    def destinations_folder_edit(self, folder_id: str, label: str) -> dict:
        tree = self._destinations_tree()
        folder = find_folder(tree, str(folder_id or "").strip())
        if folder:
            folder["label"] = (label or "").strip() or folder.get("label") or "Carpeta"
            self.settings["destinations"] = tree
            save_app_settings(self.settings)
        return self._destinations_payload()

    def destinations_folder_remove(self, folder_id: str) -> dict:
        tree = self._destinations_tree()
        fid = str(folder_id or "").strip()
        if fid and remove_folder(tree, fid):
            if self.settings.get("web_dest_toolbar_folder_id") == fid:
                self.settings.pop("web_dest_toolbar_folder_id", None)
            self.settings["destinations"] = tree
            save_app_settings(self.settings)
        return self._destinations_payload()
