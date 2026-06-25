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

from ..core.fs_path import resolve_dir_path
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

# Número de miniaturas del contenido de carpeta que se envían al frontend.
_FOLDER_PREVIEW_COUNT = 4


def _folder_preview_thumbs(
    folder: Path,
    count: int,
    thumb_px: int,
) -> list[str | None]:
    """Devuelve hasta `count` data-URLs LQ del primer nivel (imágenes y vídeos)."""
    from .bridge_editor import _video_thumb_jpeg_data_url_square

    if Image is None:
        return []
    thumb_cell = max(32, thumb_px // 2)
    candidates: list[Path] = []
    try:
        for p in folder.iterdir():
            if not p.is_file():
                continue
            ext = p.suffix.lower()
            if ext in MediaOrganizer.IMAGE_EXTENSIONS and ext != ".svg":
                candidates.append(p)
            elif ext in MediaOrganizer.VIDEO_EXTENSIONS:
                candidates.append(p)
    except OSError:
        return []
    candidates.sort(key=lambda x: str(x).lower())
    urls: list[str | None] = []
    for p in candidates[:count]:
        ext = p.suffix.lower()
        if ext in MediaOrganizer.VIDEO_EXTENSIONS:
            url = _video_thumb_jpeg_data_url_square(p, thumb_cell, quality=40)
        else:
            url = _thumb_jpeg_data_url_square(p, thumb_cell, quality=40)
        urls.append(url)
    return urls


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
        if self._is_grouped_mode():
            total = len(self.ordered_paths)
            return 0, total
        if self._is_timeline_mode():
            total = len(self.ordered_paths)
            if not self._is_unlimited_mode():
                return 0, total
            if total <= 0:
                return 0, 0
            loaded = self.gallery_unlimited_loaded
            if loaded <= 0:
                loaded = min(total, self._unlimited_batch_size())
            loaded = max(0, min(total, loaded))
            self.gallery_unlimited_loaded = loaded
            return 0, loaded
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
    def _path_date_ts(p: Path, field: str = "mtime") -> float:
        try:
            st = p.stat()
            return float(st.st_ctime if field == "ctime" else st.st_mtime)
        except OSError:
            return 0.0

    @staticmethod
    def _path_date_iso(p: Path, field: str = "mtime") -> str:
        try:
            ts = GalleryBridgeMixin._path_date_ts(p, field)
            return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
        except OSError:
            return ""

    @staticmethod
    def _path_year_month(p: Path, field: str = "mtime") -> tuple[int, int]:
        try:
            ts = GalleryBridgeMixin._path_date_ts(p, field)
            dt = datetime.datetime.fromtimestamp(ts)
            return (dt.year, dt.month)
        except OSError:
            return (1970, 1)

    def _timeline_date_field(self) -> str:
        """Campo de fecha para línea de tiempo según el criterio primario de orden."""
        mode = str(self.settings.get("gallery_sort_mode", "mtime:desc"))
        primary = mode.split(",")[0].strip().split(":")[0].lower()
        if primary in ("ctime", "creacion", "creation", "created"):
            return "ctime"
        return "mtime"

    def _timeline_sort_mode(self) -> str:
        """Modo de orden para timeline; fuerza mtime/ctime si el primario no es fecha."""
        mode = str(self.settings.get("gallery_sort_mode", "mtime:desc"))
        primary = mode.split(",")[0].strip().split(":")[0].lower()
        if primary in ("mtime", "date", "fecha", "ctime", "creacion", "creation", "created"):
            return mode
        return "mtime:desc,name:asc"

    def _compute_timeline_spans(self, ordered: list[Path]) -> list[tuple[int, int, str, str]]:
        """Rangos por (año, mes) sobre una lista ya ordenada por fecha."""
        if not ordered:
            return []
        date_field = self._timeline_date_field()
        spans: list[tuple[int, int, str, str]] = []
        i = 0
        while i < len(ordered):
            y, m = self._path_year_month(ordered[i], date_field)
            j = i + 1
            while j < len(ordered) and self._path_year_month(ordered[j], date_field) == (y, m):
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
        timeline_date_field: str = "mtime",
    ) -> list[dict]:
        def _one_image_item(p: Path) -> dict:
            ext = p.suffix.lower()
            is_video = ext in MediaOrganizer.VIDEO_EXTENSIONS
            d: dict = {
                "kind": "video" if is_video else "image",
                "name": p.name,
                "path": str(p),
                "selected": p in selected_frozenset,
                "thumbDataUrl": self._thumb_data_url_cached(p, thumb_px, "lq"),
                "thumbQuality": "hq" if is_video else "lq",
            }
            if timeline_meta:
                d["mtimeIso"] = self._path_date_iso(p, timeline_date_field)
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
            ordered = sort_image_paths(raw, self._timeline_sort_mode())
            self._gallery_timeline_spans = self._compute_timeline_spans(ordered)
            return ordered
        include = bool(self.settings.get("gallery_include_subfolders", False))
        if include:
            raw = scan_media_recursive(folder)
        else:
            raw = scan_media_flat(folder)
        sort_mode = str(self.settings.get("gallery_sort_mode", "name"))
        return sort_image_paths(raw, sort_mode)

    def _gallery_media_counts(self) -> tuple[int, int]:
        """Devuelve (imágenes, vídeos) en ordered_paths."""
        videos = 0
        for p in self.ordered_paths:
            if p.suffix.lower() in MediaOrganizer.VIDEO_EXTENSIONS:
                videos += 1
        return len(self.ordered_paths) - videos, videos

    def _gallery_state(self) -> dict:
        total = len(self.ordered_paths)
        total_images, total_videos = self._gallery_media_counts()
        tp = self._total_pages()
        self._clamp_page()
        s, e = self._slice()
        return {
            "folder": str(self.gallery_folder) if self.gallery_folder else "",
            "total": total,
            "totalImages": total_images,
            "totalVideos": total_videos,
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

    def _build_timeline_items_for_range(self, range_start: int, range_end: int) -> list[dict]:
        """Ítems de línea de tiempo para un rango de índices en ordered_paths (carga progresiva)."""
        items: list[dict] = []
        if range_start >= range_end:
            return items
        thumb_px = _thumb_px_from_gallery_scale(float(self.settings.get("gallery_thumb_scale", 1.0)))
        selected_frozenset = frozenset(self.selected)
        for span_start, span_end, key, label in self._gallery_timeline_spans:
            if span_end <= range_start:
                continue
            if span_start >= range_end:
                break
            clip_start = max(span_start, range_start)
            clip_end = min(span_end, range_end)
            if clip_start >= clip_end:
                continue
            if clip_start == span_start:
                items.append(
                    {
                        "kind": "section",
                        "name": label,
                        "path": f"section:timeline:{key}",
                        "sectionFolder": "",
                        "thumbDataUrl": None,
                    }
                )
            slice_paths = self.ordered_paths[clip_start:clip_end]
            items.extend(
                self._build_image_items(
                    slice_paths,
                    thumb_px,
                    selected_frozenset,
                    timeline_meta=True,
                    timeline_date_field=self._timeline_date_field(),
                )
            )
        return items

    def _build_folder_items(self, thumb_px: int) -> list[dict]:
        """Tiles de subcarpetas inmediatas (navegación)."""
        if not self.subfolders:
            return []

        def _folder_item(sub: Path) -> dict:
            preview_urls = _folder_preview_thumbs(sub, _FOLDER_PREVIEW_COUNT, thumb_px)
            return {
                "kind": "folder",
                "name": sub.name,
                "path": str(sub),
                "thumbDataUrl": None,
                "folderPreviewUrls": preview_urls,
            }

        max_w = min(8, max(1, len(self.subfolders)))
        with ThreadPoolExecutor(max_workers=max_w) as pool:
            return list(pool.map(_folder_item, self.subfolders))

    def _build_gallery_items_timeline(self) -> list[dict]:
        s, e = self._slice()
        thumb_px = _thumb_px_from_gallery_scale(float(self.settings.get("gallery_thumb_scale", 1.0)))
        items: list[dict] = []
        if s == 0 and self.gallery_folder is not None:
            items.extend(self._build_folder_items(thumb_px))
        items.extend(self._build_timeline_items_for_range(s, e))
        return items

    def _build_gallery_items(self) -> list[dict]:
        if self._is_grouped_mode():
            return self._build_gallery_items_grouped()
        if self._is_timeline_mode():
            return self._build_gallery_items_timeline()
        s, e = self._slice()
        items: list[dict] = []
        if self.gallery_page == 0 and self.gallery_folder is not None:
            thumb_px = _thumb_px_from_gallery_scale(
                float(self.settings.get("gallery_thumb_scale", 1.0))
            )
            items.extend(self._build_folder_items(thumb_px))
        thumb_px = _thumb_px_from_gallery_scale(float(self.settings.get("gallery_thumb_scale", 1.0)))
        slice_paths = self.ordered_paths[s:e]
        selected_frozenset = frozenset(self.selected)
        items.extend(self._build_image_items(slice_paths, thumb_px, selected_frozenset))
        return items

    def gallery_load_folder(self, raw_path: str) -> dict:
        folder = resolve_dir_path(raw_path)
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
            if self._is_grouped_mode() and self._is_unlimited_mode():
                self.gallery_unlimited_loaded = len(self.ordered_paths)
            return {
                "state": self._gallery_state(),
                "items": self._build_gallery_items(),
                "recentFolders": list(self.settings.get("gallery_recent_folders", [])),
            }

    def gallery_reload(self, *, clear_thumb_cache: bool = True) -> dict:
        """Reindexa archivos en la carpeta actual sin perder página ni selección (p. ej. tras mover archivos)."""
        if not self.gallery_folder:
            return {"state": self._gallery_state(), "items": []}
        with self.lock:
            self._gallery_reindex_core(clear_thumb_cache=clear_thumb_cache)
            return {"state": self._gallery_state(), "items": self._build_gallery_items()}

    def _gallery_reindex_core(self, *, clear_thumb_cache: bool) -> None:
        prev_unlimited_loaded = int(self.gallery_unlimited_loaded or 0)
        if clear_thumb_cache:
            self._clear_thumb_cache()
        folder = self.gallery_folder
        self.subfolders = list_subdirs(folder)
        self.ordered_paths = self._scan_ordered_paths(folder)
        self._schedule_gallery_total_bytes_recompute()
        self._clamp_page()
        if self._is_unlimited_mode():
            total = len(self.ordered_paths)
            if self._is_grouped_mode():
                self.gallery_unlimited_loaded = total
            else:
                batch = self._unlimited_batch_size()
                keep = prev_unlimited_loaded if prev_unlimited_loaded > 0 else batch
                self.gallery_unlimited_loaded = min(total, max(batch, keep))

    def gallery_reindex_delta(self, removed_paths: list[str] | None = None) -> dict:
        """Reindexa metadatos tras quitar archivos; evita serializar toda la rejilla si no hace falta."""
        if not self.gallery_folder:
            return {"state": self._gallery_state(), "removedPaths": [], "delta": True}
        with self.lock:
            self._gallery_reindex_core(clear_thumb_cache=False)
            normalized: list[str] = []
            for raw in removed_paths or []:
                s = str(raw).strip()
                if not s:
                    continue
                try:
                    normalized.append(str(Path(s).expanduser().resolve()))
                except OSError:
                    normalized.append(s)
            out: dict = {
                "state": self._gallery_state(),
                "removedPaths": normalized,
                "delta": True,
            }
            # Agrupado / línea de tiempo: la estructura de secciones puede cambiar → items completos.
            if self._is_grouped_mode() or self._is_timeline_mode():
                out["items"] = self._build_gallery_items()
                out["delta"] = False
            return out

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
            if self._is_grouped_mode():
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

            if self._is_timeline_mode():
                batch_items = self._build_timeline_items_for_range(start, end)
            else:
                thumb_px = _thumb_px_from_gallery_scale(float(self.settings.get("gallery_thumb_scale", 1.0)))
                selected_frozenset = frozenset(self.selected)
                batch_items = self._build_image_items(self.ordered_paths[start:end], thumb_px, selected_frozenset)

            self.gallery_unlimited_loaded = end
            has_more = end < total
            return {"state": self._gallery_state(), "items": batch_items, "hasMore": has_more}

    def gallery_open_folder_tile(self, path: str) -> dict:
        return self.gallery_load_folder(path)

    def gallery_thumb_hq(self, path: str, scale: float) -> dict:
        p = Path(path).expanduser().resolve()
        thumb_px = _thumb_px_from_gallery_scale(float(scale))
        return {"path": str(p), "thumbDataUrl": self._thumb_data_url_cached(p, thumb_px, "hq"), "thumbQuality": "hq"}

    def gallery_file_stat(self, path: str) -> dict:
        """Metadatos básicos para propiedades del menú contextual."""
        import mimetypes

        from ..core.fs_path import resolve_file_path

        try:
            p = resolve_file_path(path)
        except ValueError as exc:
            raise ValueError("Archivo no encontrado.") from exc
        try:
            st = p.stat()
        except OSError as exc:
            raise ValueError(f"No se pudo leer el archivo: {exc}") from exc
        ext = p.suffix.lower()
        if ext in MediaOrganizer.VIDEO_EXTENSIONS:
            media_type = "video"
        elif ext in MediaOrganizer.IMAGE_EXTENSIONS:
            media_type = "image"
        else:
            media_type = "other"
        mime, _ = mimetypes.guess_type(p.name)
        mtime = datetime.datetime.fromtimestamp(st.st_mtime)
        return {
            "path": str(p),
            "name": p.name,
            "sizeBytes": int(st.st_size),
            "mtimeIso": mtime.strftime("%Y-%m-%d %H:%M:%S"),
            "extension": ext.lstrip(".") or p.suffix,
            "mediaType": media_type,
            "mimeType": mime or "",
        }
