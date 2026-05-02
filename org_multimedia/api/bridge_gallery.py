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

class GalleryBridgeMixin:
    def _is_grouped_mode(self) -> bool:
        return bool(self.settings.get("gallery_group_by_folder", False))

    def _is_timeline_mode(self) -> bool:
        return bool(self.settings.get("gallery_timeline_view", False))

    def _is_unlimited_mode(self) -> bool:
        return int(self.settings.get("gallery_thumbs_per_page", 48)) <= 0

    def _unlimited_batch_size(self) -> int:
        return 48

    def _thumbs_per_page(self) -> int:
        n = int(self.settings.get("gallery_thumbs_per_page", 48))
        if n <= 0:
            # En modo sin límite, se usa carga progresiva por tandas.
            return self._unlimited_batch_size()
        return max(12, n)

    def _schedule_gallery_total_bytes_recompute(self) -> None:
        with self.lock:
            self._gallery_bytes_gen += 1
            gen = self._gallery_bytes_gen
            snapshot = list(self.ordered_paths)
            self.gallery_total_bytes = -1  # frontend: "calculando…"

        def worker() -> None:
            total = 0
            for p in snapshot:
                try:
                    total += int(p.stat().st_size)
                except OSError:
                    continue
            with self.lock:
                if gen != self._gallery_bytes_gen:
                    return
                self.gallery_total_bytes = max(0, total)

        threading.Thread(target=worker, daemon=True).start()

    def _total_pages(self) -> int:
        if self._is_grouped_mode() or self._is_timeline_mode():
            return 1
        total = len(self.ordered_paths)
        if total == 0:
            return 1
        if self._is_unlimited_mode():
            return 1
        ps = self._thumbs_per_page()
        return max(1, (total + ps - 1) // ps)

    def _clamp_page(self) -> None:
        tp = self._total_pages()
        self.gallery_page = max(0, min(self.gallery_page, tp - 1))

    def _slice(self) -> tuple[int, int]:
        if self._is_grouped_mode() or self._is_timeline_mode():
            total = len(self.ordered_paths)
            return 0, total
        if self._is_unlimited_mode():
            total = len(self.ordered_paths)
            if total <= 0:
                return 0, 0
            loaded = self.gallery_unlimited_loaded
            if loaded <= 0:
                loaded = min(total, self._unlimited_batch_size())
            loaded = max(0, min(total, loaded))
            self.gallery_unlimited_loaded = loaded
            return 0, loaded
        ps = self._thumbs_per_page()
        s = self.gallery_page * ps
        e = min(len(self.ordered_paths), s + ps)
        return s, e

    @staticmethod
    def _path_mtime_iso(p: Path) -> str:
        try:
            ts = p.stat().st_mtime
            return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
        except OSError:
            return ""

    @staticmethod
    def _path_year_month(p: Path) -> tuple[int, int]:
        try:
            ts = p.stat().st_mtime
            dt = datetime.datetime.fromtimestamp(ts)
            return (dt.year, dt.month)
        except OSError:
            return (1970, 1)

    def _compute_timeline_spans(self, ordered: list[Path]) -> list[tuple[int, int, str, str]]:
        """Rangos por (año, mes) sobre una lista ya ordenada por fecha de modificación."""
        if not ordered:
            return []
        spans: list[tuple[int, int, str, str]] = []
        i = 0
        while i < len(ordered):
            y, m = self._path_year_month(ordered[i])
            j = i + 1
            while j < len(ordered) and self._path_year_month(ordered[j]) == (y, m):
                j += 1
            key = f"{y}-{m:02d}"
            label = f"{_MONTH_NAMES_ES[m]} {y}"
            spans.append((i, j, key, label))
            i = j
        return spans

    def _build_image_items(
        self,
        slice_paths: list[Path],
        thumb_px: int,
        selected_frozenset: frozenset[Path],
        *,
        timeline_meta: bool = False,
    ) -> list[dict]:
        def _one_image_item(p: Path) -> dict:
            ext = p.suffix.lower()
            is_video = ext in MediaOrganizer.VIDEO_EXTENSIONS
            d: dict = {
                "kind": "video" if is_video else "image",
                "name": p.name,
                "path": str(p),
                "selected": p in selected_frozenset,
                "thumbDataUrl": None if is_video else self._thumb_data_url_cached(p, thumb_px, "lq"),
                "thumbQuality": "lq",
            }
            if timeline_meta:
                d["mtimeIso"] = self._path_mtime_iso(p)
            return d

        if not slice_paths:
            return []
        max_workers = min(8, max(1, len(slice_paths)))
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            return list(pool.map(_one_image_item, slice_paths))

    def _compute_grouped_paths(self, root: Path) -> tuple[list[Path], list[tuple[int, int, str, str]]]:
        """Una sección por la carpeta actual (archivos directos) y por cada subcarpeta inmediata."""
        mode = str(self.settings.get("gallery_sort_mode", "name"))
        ordered: list[Path] = []
        spans: list[tuple[int, int, str, str]] = []
        idx = 0
        root_files = sort_image_paths(scan_media_flat(root), mode)
        spans.append((idx, idx + len(root_files), str(root), "(esta carpeta)"))
        ordered.extend(root_files)
        idx += len(root_files)
        for sub in list_subdirs(root):
            files = sort_image_paths(scan_media_flat(sub), mode)
            spans.append((idx, idx + len(files), str(sub), sub.name))
            ordered.extend(files)
            idx += len(files)
        return ordered, spans

    def _scan_ordered_paths(self, folder: Path) -> list[Path]:
        """Lista de imágenes según ajustes de recursión, agrupación u orden."""
        self._gallery_section_spans = []
        self._gallery_timeline_spans = []
        if self._is_grouped_mode():
            ordered, spans = self._compute_grouped_paths(folder)
            self._gallery_section_spans = spans
            return ordered
        if self._is_timeline_mode():
            include = bool(self.settings.get("gallery_include_subfolders", False))
            raw = scan_media_recursive(folder) if include else scan_media_flat(folder)
            ordered = sort_image_paths(raw, "mtime")
            self._gallery_timeline_spans = self._compute_timeline_spans(ordered)
            return ordered
        include = bool(self.settings.get("gallery_include_subfolders", False))
        if include:
            raw = scan_media_recursive(folder)
        else:
            raw = scan_media_flat(folder)
        sort_mode = str(self.settings.get("gallery_sort_mode", "name"))
        return sort_image_paths(raw, sort_mode)

    def _gallery_state(self) -> dict:
        total = len(self.ordered_paths)
        tp = self._total_pages()
        self._clamp_page()
        s, e = self._slice()
        return {
            "folder": str(self.gallery_folder) if self.gallery_folder else "",
            "total": total,
            "totalElements": total + len(self.subfolders),
            "totalBytes": int(self.gallery_total_bytes),
            "page": self.gallery_page + 1,
            "totalPages": tp,
            "startIndex": s,
            "endIndex": e,
            "selectedCount": len(self.selected),
            "subfoldersCount": len(self.subfolders),
        }

    def _build_gallery_items_grouped(self) -> list[dict]:
        items: list[dict] = []
        thumb_px = _thumb_px_from_gallery_scale(float(self.settings.get("gallery_thumb_scale", 1.0)))
        selected_frozenset = frozenset(self.selected)
        use_tint = bool(self.settings.get("gallery_section_dominant_color", True))
        for start, end, folder_path, label in self._gallery_section_spans:
            slice_paths = self.ordered_paths[start:end]
            sec: dict = {
                "kind": "section",
                "name": label,
                "path": f"section:{folder_path}",
                "sectionFolder": folder_path,
                "thumbDataUrl": None,
            }
            if use_tint and slice_paths:
                img_only = [
                    p
                    for p in slice_paths
                    if p.suffix.lower() in MediaOrganizer.IMAGE_EXTENSIONS and p.suffix.lower() != ".svg"
                ]
                th = accent_hex_from_paths(img_only, max_samples=3) if img_only else None
                if th:
                    sec["sectionTintHex"] = th
            items.append(sec)
            items.extend(self._build_image_items(slice_paths, thumb_px, selected_frozenset))
        return items

    def _build_gallery_items_timeline(self) -> list[dict]:
        items: list[dict] = []
        thumb_px = _thumb_px_from_gallery_scale(float(self.settings.get("gallery_thumb_scale", 1.0)))
        selected_frozenset = frozenset(self.selected)
        for start, end, key, label in self._gallery_timeline_spans:
            items.append(
                {
                    "kind": "section",
                    "name": label,
                    "path": f"section:timeline:{key}",
                    "sectionFolder": "",
                    "thumbDataUrl": None,
                }
            )
            slice_paths = self.ordered_paths[start:end]
            items.extend(
                self._build_image_items(slice_paths, thumb_px, selected_frozenset, timeline_meta=True)
            )
        return items

    def _build_gallery_items(self) -> list[dict]:
        if self._is_grouped_mode():
            return self._build_gallery_items_grouped()
        if self._is_timeline_mode():
            return self._build_gallery_items_timeline()
        s, e = self._slice()
        items: list[dict] = []
        if self.gallery_page == 0 and self.gallery_folder is not None:
            for sub in self.subfolders:
                items.append({"kind": "folder", "name": sub.name, "path": str(sub), "thumbDataUrl": None})
        thumb_px = _thumb_px_from_gallery_scale(float(self.settings.get("gallery_thumb_scale", 1.0)))
        slice_paths = self.ordered_paths[s:e]
        selected_frozenset = frozenset(self.selected)
        items.extend(self._build_image_items(slice_paths, thumb_px, selected_frozenset))
        return items

    def gallery_load_folder(self, raw_path: str) -> dict:
        folder = Path(os.path.expandvars(os.path.expanduser(raw_path.strip()))).resolve()
        if not folder.is_dir():
            raise ValueError(f"No existe o no es carpeta: {folder}")
        with self.lock:
            self._clear_thumb_cache()
            self.gallery_folder = folder
            self.settings["gallery_last_folder"] = str(folder)
            self._merge_recent_folder(str(folder))
            save_app_settings(self.settings)
            self.subfolders = list_subdirs(folder)
            self.ordered_paths = self._scan_ordered_paths(folder)
            self._schedule_gallery_total_bytes_recompute()
            self.selected.clear()
            self.gallery_page = 0
            self.gallery_unlimited_loaded = (
                min(len(self.ordered_paths), self._unlimited_batch_size()) if self._is_unlimited_mode() else 0
            )
            if (self._is_grouped_mode() or self._is_timeline_mode()) and self._is_unlimited_mode():
                self.gallery_unlimited_loaded = len(self.ordered_paths)
            return {
                "state": self._gallery_state(),
                "items": self._build_gallery_items(),
                "recentFolders": list(self.settings.get("gallery_recent_folders", [])),
            }

    def gallery_reload(self) -> dict:
        """Reindexa archivos en la carpeta actual sin perder página ni selección (p. ej. tras mover archivos)."""
        if not self.gallery_folder:
            return {"state": self._gallery_state(), "items": []}
        with self.lock:
            self._clear_thumb_cache()
            folder = self.gallery_folder
            self.subfolders = list_subdirs(folder)
            self.ordered_paths = self._scan_ordered_paths(folder)
            self._schedule_gallery_total_bytes_recompute()
            self._clamp_page()
            if self._is_unlimited_mode():
                if self._is_grouped_mode() or self._is_timeline_mode():
                    self.gallery_unlimited_loaded = len(self.ordered_paths)
                else:
                    self.gallery_unlimited_loaded = min(len(self.ordered_paths), self._unlimited_batch_size())
            return {"state": self._gallery_state(), "items": self._build_gallery_items()}

    def gallery_refresh_items(self) -> dict:
        """Solo reconstruye estado e ítems (sin reescaneo): útil tras toggle de selección."""
        with self.lock:
            if not self.gallery_folder:
                return {"state": self._gallery_state(), "items": []}
            return {"state": self._gallery_state(), "items": self._build_gallery_items()}

    def gallery_go_page(self, page_1: int) -> dict:
        with self.lock:
            if self._is_unlimited_mode():
                # En modo sin límite no hay páginas; la carga es por tandas.
                return {"state": self._gallery_state(), "items": self._build_gallery_items()}
            self.gallery_page = max(0, int(page_1) - 1)
            self._clamp_page()
            return {"state": self._gallery_state(), "items": self._build_gallery_items()}

    def gallery_load_more(self) -> dict:
        with self.lock:
            if not self.gallery_folder:
                return {"state": self._gallery_state(), "items": [], "hasMore": False}
            if self._is_grouped_mode() or self._is_timeline_mode():
                return {"state": self._gallery_state(), "items": [], "hasMore": False}
            if not self._is_unlimited_mode():
                return {"state": self._gallery_state(), "items": [], "hasMore": False}
            total = len(self.ordered_paths)
            if total <= 0:
                return {"state": self._gallery_state(), "items": [], "hasMore": False}

            start = max(0, min(total, self.gallery_unlimited_loaded))
            end = min(total, start + self._unlimited_batch_size())
            if start >= end:
                return {"state": self._gallery_state(), "items": [], "hasMore": False}

            thumb_px = _thumb_px_from_gallery_scale(float(self.settings.get("gallery_thumb_scale", 1.0)))
            selected_frozenset = frozenset(self.selected)
            image_items = self._build_image_items(self.ordered_paths[start:end], thumb_px, selected_frozenset)

            self.gallery_unlimited_loaded = end
            has_more = end < total
            return {"state": self._gallery_state(), "items": image_items, "hasMore": has_more}

    def gallery_open_folder_tile(self, path: str) -> dict:
        return self.gallery_load_folder(path)

    def gallery_thumb_hq(self, path: str, scale: float) -> dict:
        p = Path(path).expanduser().resolve()
        thumb_px = _thumb_px_from_gallery_scale(float(scale))
        return {"path": str(p), "thumbDataUrl": self._thumb_data_url_cached(p, thumb_px, "hq"), "thumbQuality": "hq"}

    def gallery_file_stat(self, path: str) -> dict:
        """Metadatos básicos para el menú contextual (tamaño, fecha de modificación local)."""
        p = Path(path).expanduser().resolve()
        if not p.is_file():
            raise ValueError("Archivo no encontrado.")
        try:
            st = p.stat()
        except OSError as exc:
            raise ValueError(f"No se pudo leer el archivo: {exc}") from exc
        mtime = datetime.datetime.fromtimestamp(st.st_mtime)
        return {
            "path": str(p),
            "name": p.name,
            "sizeBytes": int(st.st_size),
            "mtimeIso": mtime.strftime("%Y-%m-%d %H:%M:%S"),
        }
