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

# Ventana de carga para scroll virtual (salto a fecha/letra lejana).
_GALLERY_WINDOW_OVERSCAN_BEFORE = 96
_GALLERY_WINDOW_OVERSCAN_AFTER = 160
# Núcleo visible en salto (fase 1 rápida); fase 2 expande al overscan completo.
_GALLERY_JUMP_CORE_OVERSCAN_BEFORE = 32
_GALLERY_JUMP_CORE_OVERSCAN_AFTER = 48
# Scroll leve por encima de la ventana: ampliar hacia atrás; más lejos: recentrar ventana.
_GALLERY_WINDOW_JUMP_MARGIN = 128
_GALLERY_LOAD_MAX_BATCHES = 2
_GALLERY_SCAN_CACHE_TTL_S = 300.0
_GALLERY_SCAN_CACHE_MAX = 8
_GALLERY_EXTEND_MAX_BATCHES = 16
# Carpetas pequeñas: tandas LQ más cortas para builds rápidos.
_GALLERY_SMALL_FOLDER_MAX = 2000
_GALLERY_SMALL_FOLDER_BATCH_CAP = 32
MASONRY_THUMB_HEIGHT_FACTOR = 2.4

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
    from ..core.thumbs import thumb_jpeg_data_url_square

    return thumb_jpeg_data_url_square(path, size, quality=quality)

def _thumb_jpeg_data_url_masonry(path: Path, max_w: int, max_h: int, quality: int = 90) -> str | None:
    from ..core.thumbs import thumb_jpeg_data_url_masonry

    return thumb_jpeg_data_url_masonry(path, max_w, max_h, quality=quality)

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
    from ..core.thumb_quality_options import thumb_encode_params
    from .bridge_editor import _video_thumb_jpeg_data_url_square

    if Image is None:
        return []
    enc = thumb_encode_params(max(32, thumb_px // 2), "lq")
    thumb_cell = enc.size_px
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
            url = _video_thumb_jpeg_data_url_square(p, thumb_cell, quality=enc.jpeg_quality)
        else:
            url = _thumb_jpeg_data_url_square(p, thumb_cell, quality=enc.jpeg_quality)
        urls.append(url)
    return urls


class GalleryBridgeMixin:
    def _is_grouped_mode(self) -> bool:
        return bool(self.settings.get("gallery_group_by_folder", False))

    def _is_timeline_mode(self) -> bool:
        return bool(self.settings.get("gallery_timeline_view", False))

    def _is_unlimited_mode(self) -> bool:
        return int(self.settings.get("gallery_thumbs_per_page", 48)) <= 0

    def _unlimited_batch_size(self, total: int | None = None, *, for_scroll: bool = False) -> int:
        n = int(self.settings.get("gallery_unlimited_batch_size", 48))
        base = max(24, min(256, n))
        if total is None:
            total = len(self.ordered_paths)
        # Solo acortar tandas en scroll/append; la apertura inicial usa el batch completo.
        if for_scroll and total > 0 and total <= _GALLERY_SMALL_FOLDER_MAX:
            return max(24, min(base, _GALLERY_SMALL_FOLDER_BATCH_CAP))
        return base

    def _is_small_gallery_folder(self) -> bool:
        total = len(self.ordered_paths)
        return total > 0 and total <= _GALLERY_SMALL_FOLDER_MAX

    def _gallery_window_overscan_before(self) -> int:
        n = int(self.settings.get("gallery_window_overscan_before", _GALLERY_WINDOW_OVERSCAN_BEFORE))
        return max(32, min(512, n))

    def _gallery_window_overscan_after(self) -> int:
        n = int(self.settings.get("gallery_window_overscan_after", _GALLERY_WINDOW_OVERSCAN_AFTER))
        return max(32, min(512, n))

    def _gallery_jump_core_overscan_before(self) -> int:
        n = int(
            self.settings.get(
                "gallery_jump_core_overscan_before",
                _GALLERY_JUMP_CORE_OVERSCAN_BEFORE,
            )
        )
        return max(24, min(128, n))

    def _gallery_jump_core_overscan_after(self) -> int:
        n = int(
            self.settings.get(
                "gallery_jump_core_overscan_after",
                _GALLERY_JUMP_CORE_OVERSCAN_AFTER,
            )
        )
        return max(32, min(160, n))

    def _gallery_thumb_build_workers(self, *, boost: bool = False) -> int:
        n = int(self.settings.get("gallery_thumb_build_workers", 8))
        if boost:
            n = min(16, max(n, 12))
        return max(2, min(16, n))

    def _gallery_sliding_window_enabled(self) -> bool:
        return bool(self.settings.get("gallery_sliding_window_enabled", False))

    def _gallery_sliding_window_max_items(self) -> int:
        n = int(self.settings.get("gallery_sliding_window_max_items", 896))
        return max(320, min(4096, n))

    def _maybe_trim_sliding_window(self) -> int:
        """Recorta el inicio de la ventana deslizante si supera el máximo configurado."""
        if not self._gallery_sliding_window_enabled():
            return 0
        ws = int(getattr(self, "gallery_unlimited_window_start", 0) or 0)
        loaded = int(self.gallery_unlimited_loaded or 0)
        if loaded <= ws:
            return 0
        max_items = self._gallery_sliding_window_max_items()
        span = loaded - ws
        if span <= max_items:
            return 0
        trim = span - max_items
        self.gallery_unlimited_window_start = ws + trim
        return trim

    def _maybe_trim_sliding_window_from_end(self) -> int:
        """Recorta el final de la ventana al prepend hacia atrás."""
        if not self._gallery_sliding_window_enabled():
            return 0
        ws = int(getattr(self, "gallery_unlimited_window_start", 0) or 0)
        loaded = int(self.gallery_unlimited_loaded or 0)
        if loaded <= ws:
            return 0
        max_items = self._gallery_sliding_window_max_items()
        span = loaded - ws
        if span <= max_items:
            return 0
        trim = span - max_items
        self.gallery_unlimited_loaded = loaded - trim
        return trim

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
            label = f"{_MONTH_NAMES_ES[m].capitalize()} {y}"
            spans.append((i, j, key, label))
            i = j
        return spans

    @staticmethod
    def _alpha_bucket(name: str) -> str:
        raw = str(name or "").strip()
        if not raw:
            return "#"
        ch = raw[0].upper()
        return ch if ch.isalpha() else "#"

    def _compute_alpha_spans(self, ordered: list[Path]) -> list[tuple[int, int, str, str]]:
        """Rangos por letra inicial del nombre (A, B, …, #)."""
        if not ordered:
            return []
        spans: list[tuple[int, int, str, str]] = []
        i = 0
        while i < len(ordered):
            letter = self._alpha_bucket(ordered[i].name)
            j = i + 1
            while j < len(ordered) and self._alpha_bucket(ordered[j].name) == letter:
                j += 1
            spans.append((i, j, letter, letter))
            i = j
        return spans

    def _is_date_primary_sort(self) -> bool:
        """True si el criterio primario de orden es una fecha (mtime, ctime, etc.)."""
        mode = str(self.settings.get("gallery_sort_mode", "name"))
        primary = mode.split(",")[0].strip().split(":")[0].lower()
        return primary in (
            "mtime",
            "date",
            "fecha",
            "ctime",
            "creacion",
            "creation",
            "created",
        )

    def _layout_mode(self) -> str:
        if self._is_grouped_mode():
            return "grouped"
        if self._is_timeline_mode():
            return "timeline"
        mode = str(self.settings.get("gallery_sort_mode", "name"))
        primary = mode.split(",")[0].strip().split(":")[0].lower()
        if primary in ("name", "nombre"):
            return "alpha"
        return "flat"

    def _layout_spans_payload(self) -> list[dict]:
        mode = self._layout_mode()
        if mode == "timeline":
            src = self._gallery_timeline_spans
            kind = "timeline"
        elif mode == "grouped":
            src = self._gallery_section_spans
            kind = "folder"
        elif mode == "alpha":
            src = self._gallery_alpha_spans
            kind = "alpha"
        elif self._is_date_primary_sort() and self._gallery_timeline_spans:
            src = self._gallery_timeline_spans
            kind = "timeline"
        else:
            return []
        return [
            {"start": int(s), "end": int(e), "label": str(label), "kind": kind, "key": str(key)}
            for s, e, key, label in src
        ]

    def _is_masonry_view(self) -> bool:
        return bool(self.settings.get("gallery_masonry_view", False))

    def _masonry_display_size(self, path: Path, thumb_px: int) -> tuple[int, int]:
        """Tamaño de miniatura en UI (misma lógica que thumbs.masonry_thumb_target_size)."""
        from ..core.thumbs import _load_rgb_for_thumb, masonry_thumb_target_size

        max_h = max(48, int(round(thumb_px * MASONRY_THUMB_HEIGHT_FACTOR)))
        try:
            im = _load_rgb_for_thumb(path)
            w, h = im.size
            return masonry_thumb_target_size(w, h, thumb_px, max_h)
        except Exception:
            side = max(48, int(thumb_px))
            return side, min(max_h, max(1, int(round(side * 1.25))))

    def _gallery_item_path(self, p: Path) -> str:
        try:
            return str(p.resolve())
        except OSError:
            return str(p)

    def _build_image_items(
        self,
        slice_paths: list[Path],
        thumb_px: int,
        selected_frozenset: frozenset[Path],
        *,
        base_index: int = 0,
        timeline_meta: bool = False,
        timeline_date_field: str = "mtime",
        jump_fast: bool = False,
        build_boost: bool = False,
    ) -> list[dict]:
        def _one_image_item(entry: tuple[int, Path]) -> dict:
            i, p = entry
            item_path = self._gallery_item_path(p)
            cache_key = (item_path, int(thumb_px))
            cached = self._gallery_path_item_cache.get(cache_key)
            if cached is not None:
                d = dict(cached)
                d["selected"] = p in selected_frozenset
                d["mediaIndex"] = base_index + i
                return d
            ext = p.suffix.lower()
            is_video = ext in MediaOrganizer.VIDEO_EXTENSIONS
            d: dict = {
                "kind": "video" if is_video else "image",
                "name": p.name,
                "path": item_path,
                "selected": p in selected_frozenset,
                "thumbDataUrl": self._thumb_data_url_cached(p, thumb_px, "lq"),
                "thumbQuality": "lq",
                "mediaIndex": base_index + i,
            }
            if timeline_meta:
                d["mtimeIso"] = self._path_date_iso(p, timeline_date_field)
            if (
                self._is_masonry_view()
                and not jump_fast
                and p.suffix.lower() not in (".svg",)
            ):
                tw, th = self._masonry_display_size(p, thumb_px)
                d["thumbW"] = int(tw)
                d["thumbH"] = int(th)
            template = {k: v for k, v in d.items() if k not in ("selected", "mediaIndex")}
            if template.get("thumbDataUrl"):
                self._gallery_path_item_cache[cache_key] = template
            return d

        if not slice_paths:
            return []
        max_workers = min(
            self._gallery_thumb_build_workers(boost=jump_fast or build_boost),
            max(1, len(slice_paths)),
        )
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            return list(pool.map(_one_image_item, enumerate(slice_paths)))

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

    def _scan_cache_key(self, folder: Path) -> tuple:
        return (
            str(folder.resolve()),
            bool(self.settings.get("gallery_include_subfolders", False)),
            bool(self.settings.get("gallery_group_by_folder", False)),
            bool(self.settings.get("gallery_timeline_view", False)),
            str(self.settings.get("gallery_sort_mode", "name")),
            self._layout_mode(),
        )

    def _invalidate_gallery_scan_cache(self) -> None:
        self._gallery_scan_cache = {}

    def _store_scan_cache(self, key: tuple, ordered: list[Path]) -> None:
        cache: dict = getattr(self, "_gallery_scan_cache", {})
        cache[key] = {
            "paths": ordered,
            "section_spans": list(self._gallery_section_spans),
            "timeline_spans": list(self._gallery_timeline_spans),
            "alpha_spans": list(self._gallery_alpha_spans),
            "ts": time.monotonic(),
        }
        if len(cache) > _GALLERY_SCAN_CACHE_MAX:
            oldest_key = min(cache, key=lambda k: float(cache[k].get("ts", 0)))
            del cache[oldest_key]
        self._gallery_scan_cache = cache

    def _apply_scan_spans(
        self,
        section_spans: list[tuple],
        timeline_spans: list[tuple],
        alpha_spans: list[tuple],
    ) -> None:
        self._gallery_section_spans = list(section_spans)
        self._gallery_timeline_spans = list(timeline_spans)
        self._gallery_alpha_spans = list(alpha_spans)

    def _scan_ordered_paths(self, folder: Path) -> list[Path]:
        """Lista de imágenes según ajustes de recursión, agrupación u orden."""
        from ..core.gallery_index_cache import save_gallery_index, try_load_gallery_index

        key = self._scan_cache_key(folder)
        self._last_scan_source = "fresh"
        cache: dict = getattr(self, "_gallery_scan_cache", {})
        hit = cache.get(key)
        now = time.monotonic()
        if hit and (now - float(hit.get("ts", 0))) < _GALLERY_SCAN_CACHE_TTL_S:
            self._apply_scan_spans(
                hit.get("section_spans") or [],
                hit.get("timeline_spans") or [],
                hit.get("alpha_spans") or [],
            )
            self._last_scan_source = "memory"
            return list(hit.get("paths") or [])

        disk = try_load_gallery_index(folder, key)
        if disk is not None:
            self._apply_scan_spans(
                disk.get("section_spans") or [],
                disk.get("timeline_spans") or [],
                disk.get("alpha_spans") or [],
            )
            ordered = list(disk.get("paths") or [])
            self._store_scan_cache(key, ordered)
            self._last_scan_source = "disk"
            return ordered

        ordered = self._scan_ordered_paths_fresh(folder)
        self._store_scan_cache(key, ordered)
        try:
            save_gallery_index(
                folder,
                key,
                ordered,
                section_spans=self._gallery_section_spans,
                timeline_spans=self._gallery_timeline_spans,
                alpha_spans=self._gallery_alpha_spans,
            )
        except Exception:
            pass
        return ordered

    def _scan_ordered_paths_fresh(self, folder: Path) -> list[Path]:
        """Escaneo en disco sin caché."""
        self._gallery_section_spans = []
        self._gallery_timeline_spans = []
        self._gallery_alpha_spans = []
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
        stat_workers = self._gallery_thumb_build_workers()
        ordered = sort_image_paths(raw, sort_mode, stat_workers=stat_workers)
        if self._is_date_primary_sort() and not self._is_timeline_mode():
            self._gallery_timeline_spans = self._compute_timeline_spans(ordered)
        if self._layout_mode() == "alpha":
            self._gallery_alpha_spans = self._compute_alpha_spans(ordered)
        return ordered

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
            "layoutMode": self._layout_mode(),
            "layoutSpans": self._layout_spans_payload(),
            "windowStart": int(getattr(self, "gallery_unlimited_window_start", 0) or 0),
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
            items.extend(
                self._build_image_items(slice_paths, thumb_px, selected_frozenset, base_index=start)
            )
        return items

    def _build_timeline_items_for_range(
        self,
        range_start: int,
        range_end: int,
        *,
        build_boost: bool = False,
    ) -> list[dict]:
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
                    base_index=clip_start,
                    timeline_meta=True,
                    timeline_date_field=self._timeline_date_field(),
                    build_boost=build_boost,
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
        build_boost = self._is_unlimited_mode() and self.gallery_page == 0 and s == 0
        items.extend(self._build_timeline_items_for_range(s, e, build_boost=build_boost))
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
        build_boost = self._is_unlimited_mode() and self.gallery_page == 0 and s == 0
        items.extend(
            self._build_image_items(
                slice_paths,
                thumb_px,
                selected_frozenset,
                base_index=s,
                build_boost=build_boost,
            )
        )
        return items

    def _gallery_items_for_range(
        self,
        start: int,
        end: int,
        *,
        jump_fast: bool = False,
    ) -> list[dict]:
        """Ítems de galería para un rango [start, end) de ordered_paths."""
        start = max(0, int(start))
        end = max(start, int(end))
        if start >= end:
            return []
        if self._is_timeline_mode():
            return self._build_timeline_items_for_range(start, end)
        thumb_px = _thumb_px_from_gallery_scale(float(self.settings.get("gallery_thumb_scale", 1.0)))
        selected_frozenset = frozenset(self.selected)
        return self._build_image_items(
            self.ordered_paths[start:end],
            thumb_px,
            selected_frozenset,
            base_index=start,
            jump_fast=jump_fast,
        )

    def _gallery_load_window(self, center_index: int, *, jump_core: bool = False) -> dict:
        """Carga solo una ventana alrededor del índice (salto o scroll fuera de rango)."""
        total = len(self.ordered_paths)
        if total <= 0:
            return {
                "state": self._gallery_state(),
                "items": [],
                "hasMore": False,
                "replaceWindow": True,
                "windowStart": 0,
                "windowEnd": 0,
            }
        center = max(0, min(total - 1, int(center_index)))
        if jump_core:
            before = self._gallery_jump_core_overscan_before()
            after = self._gallery_jump_core_overscan_after()
        else:
            before = self._gallery_window_overscan_before()
            after = self._gallery_window_overscan_after()
        start = max(0, center - before)
        end = min(total, center + after)
        old_start = int(getattr(self, "gallery_unlimited_window_start", 0) or 0)
        old_end = int(self.gallery_unlimited_loaded or 0)
        # Ya cubierto: evita reconstruir la ventana al soltar el scroll en la misma zona.
        if (
            not jump_core
            and old_end > old_start
            and old_start <= center < old_end
            and start >= old_start
            and end <= old_end
        ):
            return {
                "state": self._gallery_state(),
                "items": [],
                "hasMore": old_end < total,
                "replaceWindow": False,
            }
        t_build = time.perf_counter()
        batch_items = self._gallery_items_for_range(start, end, jump_fast=jump_core)
        build_ms = int((time.perf_counter() - t_build) * 1000)
        self.gallery_unlimited_window_start = start
        self.gallery_unlimited_loaded = end
        if jump_core:
            self._jump_expand_center = center
        payload: dict = {
            "state": self._gallery_state(),
            "items": batch_items,
            "hasMore": end < total,
            "replaceWindow": True,
            "windowStart": start,
            "windowEnd": end,
            "windowPhase": "core" if jump_core else "full",
            "timing": {"buildMs": build_ms, "itemCount": len(batch_items)},
        }
        if jump_core:
            full_before = self._gallery_window_overscan_before()
            full_after = self._gallery_window_overscan_after()
            full_start = max(0, center - full_before)
            full_end = min(total, center + full_after)
            if full_start < start or full_end > end:
                payload["windowExpandPending"] = True
                payload["windowExpandCenter"] = center
        return payload

    def _gallery_expand_jump_window(self, center_index: int) -> dict:
        """Fase 2 del salto: ampliar márgenes sin reconstruir el núcleo ya visible."""
        total = len(self.ordered_paths)
        if total <= 0:
            return {
                "state": self._gallery_state(),
                "items": [],
                "hasMore": False,
                "replaceWindow": False,
                "windowPhase": "expand",
            }
        center = max(0, min(total - 1, int(center_index)))
        before = self._gallery_window_overscan_before()
        after = self._gallery_window_overscan_after()
        start = max(0, center - before)
        end = min(total, center + after)
        cur_start = int(getattr(self, "gallery_unlimited_window_start", 0) or 0)
        cur_end = int(self.gallery_unlimited_loaded or 0)
        if cur_start <= start and cur_end >= end:
            return {
                "state": self._gallery_state(),
                "items": [],
                "hasMore": end < total,
                "replaceWindow": False,
                "windowPhase": "expand",
                "windowExpandPending": False,
            }

        prepend_items: list[dict] = []
        append_items: list[dict] = []
        need_prepend = cur_start > start
        need_append = cur_end < end
        can_incremental = cur_end > cur_start and (need_prepend or need_append)

        t_build = time.perf_counter()
        if can_incremental:
            if need_prepend:
                prepend_items = self._gallery_items_for_range(
                    start, cur_start, jump_fast=False
                )
            if need_append:
                append_items = self._gallery_items_for_range(
                    cur_end, end, jump_fast=False
                )
            batch_items = prepend_items + append_items
        else:
            batch_items = self._gallery_items_for_range(start, end, jump_fast=False)

        build_ms = int((time.perf_counter() - t_build) * 1000)
        self.gallery_unlimited_window_start = start
        self.gallery_unlimited_loaded = end
        self._jump_expand_center = 0
        trimmed = self._maybe_trim_sliding_window()

        if can_incremental and batch_items:
            return {
                "state": self._gallery_state(),
                "items": [],
                "prependItems": prepend_items,
                "appendItems": append_items,
                "hasMore": end < total,
                "replaceWindow": False,
                "windowExpandIncremental": True,
                "windowStart": start,
                "windowEnd": end,
                "windowPhase": "expand",
                "windowExpandPending": False,
                "windowTrimmed": trimmed,
                "timing": {
                    "buildMs": build_ms,
                    "itemCount": len(batch_items),
                    "prependCount": len(prepend_items),
                    "appendCount": len(append_items),
                },
            }

        return {
            "state": self._gallery_state(),
            "items": batch_items,
            "hasMore": end < total,
            "replaceWindow": True,
            "windowStart": start,
            "windowEnd": end,
            "windowPhase": "expand",
            "windowExpandPending": False,
            "timing": {"buildMs": build_ms, "itemCount": len(batch_items)},
        }

    def gallery_load_folder(self, raw_path: str) -> dict:
        folder = resolve_dir_path(raw_path)
        with self.lock:
            t0 = time.perf_counter()
            folder_changed = self.gallery_folder != folder
            if folder_changed:
                self._clear_thumb_cache()
            # Siempre regenerar plantillas LQ (p. ej. tras índice en disco o cambio de calidad).
            self._gallery_path_item_cache.clear()
            self.gallery_folder = folder
            self.settings["gallery_last_folder"] = str(folder)
            self._merge_recent_folder(str(folder))
            save_app_settings(self.settings)
            self.subfolders = list_subdirs(folder)
            t_scan = time.perf_counter()
            self.ordered_paths = self._scan_ordered_paths(folder)
            scan_ms = int((time.perf_counter() - t_scan) * 1000)
            self._schedule_gallery_total_bytes_recompute()
            self.selected.clear()
            self.gallery_page = 0
            self.gallery_unlimited_loaded = (
                min(len(self.ordered_paths), self._unlimited_batch_size()) if self._is_unlimited_mode() else 0
            )
            self.gallery_unlimited_window_start = 0
            if self._is_grouped_mode() and self._is_unlimited_mode():
                self.gallery_unlimited_loaded = len(self.ordered_paths)
            t_build = time.perf_counter()
            items = self._build_gallery_items()
            build_ms = int((time.perf_counter() - t_build) * 1000)
            total_ms = int((time.perf_counter() - t0) * 1000)
            return {
                "state": self._gallery_state(),
                "items": items,
                "recentFolders": list(self.settings.get("gallery_recent_folders", [])),
                "timing": {
                    "scanMs": scan_ms,
                    "buildMs": build_ms,
                    "totalMs": total_ms,
                    "fromCache": getattr(self, "_last_scan_source", "fresh") != "fresh",
                    "scanSource": getattr(self, "_last_scan_source", "fresh"),
                },
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
        self._invalidate_gallery_scan_cache()
        if self.gallery_folder:
            from ..core.gallery_index_cache import invalidate_gallery_index

            invalidate_gallery_index(self.gallery_folder)
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
                batch = self._unlimited_batch_size(total)
                keep = prev_unlimited_loaded if prev_unlimited_loaded > 0 else batch
                self.gallery_unlimited_loaded = min(total, max(batch, keep))
                self.gallery_unlimited_window_start = 0

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

    def _extend_batch_count(self, gap: int, batch: int) -> int:
        """Tandas por petición al extender (más si el hueco hasta el target es grande)."""
        if self._is_small_gallery_folder():
            if gap <= batch:
                return 1
            if gap <= batch * 3:
                return _GALLERY_LOAD_MAX_BATCHES
            return min(4, _GALLERY_LOAD_MAX_BATCHES + 2)
        if gap <= batch * 2:
            return _GALLERY_LOAD_MAX_BATCHES
        return min(
            _GALLERY_EXTEND_MAX_BATCHES,
            max(_GALLERY_LOAD_MAX_BATCHES, (gap // batch) + 2),
        )

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
            end = min(total, start + self._unlimited_batch_size(total, for_scroll=True))
            if start >= end:
                return {"state": self._gallery_state(), "items": [], "hasMore": False}

            window_start = int(getattr(self, "gallery_unlimited_window_start", 0) or 0)
            if window_start > 0:
                batch_items = self._gallery_items_for_range(start, end)
                self.gallery_unlimited_loaded = end
                trimmed = self._maybe_trim_sliding_window()
                has_more = end < total
                return {
                    "state": self._gallery_state(),
                    "items": batch_items,
                    "hasMore": has_more,
                    "replaceWindow": False,
                    "windowStart": window_start,
                    "windowEnd": end,
                    "windowTrimmed": trimmed,
                }

            if self._is_timeline_mode():
                batch_items = self._build_timeline_items_for_range(start, end)
            else:
                batch_items = self._gallery_items_for_range(start, end)

            self.gallery_unlimited_loaded = end
            has_more = end < total
            return {"state": self._gallery_state(), "items": batch_items, "hasMore": has_more}

    def gallery_load_until_index(
        self,
        target_index: int,
        jump: bool = False,
        expand: bool = False,
    ) -> dict:
        """Carga progresiva o ventana directa (salto a índice lejano)."""
        with self.lock:
            if not self.gallery_folder:
                return {"state": self._gallery_state(), "items": [], "hasMore": False}
            if self._is_grouped_mode() or not self._is_unlimited_mode():
                return {"state": self._gallery_state(), "items": [], "hasMore": False}
            total = len(self.ordered_paths)
            if total <= 0:
                return {"state": self._gallery_state(), "items": [], "hasMore": False}

            target = max(0, min(total, int(target_index)))
            if expand:
                center = int(getattr(self, "_jump_expand_center", 0) or target)
                if center <= 0 or abs(center - target) > self._gallery_window_overscan_before() + 128:
                    center = target
                return self._gallery_expand_jump_window(center)

            window_start = int(getattr(self, "gallery_unlimited_window_start", 0) or 0)
            loaded = int(self.gallery_unlimited_loaded or 0)
            batch = self._unlimited_batch_size(total, for_scroll=True)

            # Salto explícito (rail o scroll muy lejos): núcleo rápido + expansión en segundo plano.
            if jump:
                return self._gallery_load_window(target, jump_core=True)

            # Scroll por encima del inicio cargado: prepend incremental (sin reemplazar ventana).
            if target < window_start:
                margin = _GALLERY_WINDOW_JUMP_MARGIN
                if target >= window_start - margin:
                    new_start = max(0, target - self._gallery_window_overscan_before())
                    new_end = loaded
                    if new_start >= window_start:
                        return {
                            "state": self._gallery_state(),
                            "items": [],
                            "hasMore": loaded < total,
                            "replaceWindow": False,
                        }
                    t_build = time.perf_counter()
                    prepend_items = self._gallery_items_for_range(new_start, window_start)
                    build_ms = int((time.perf_counter() - t_build) * 1000)
                    self.gallery_unlimited_window_start = new_start
                    trimmed_end = self._maybe_trim_sliding_window_from_end()
                    new_end = int(self.gallery_unlimited_loaded or new_end)
                    if prepend_items:
                        return {
                            "state": self._gallery_state(),
                            "items": [],
                            "prependItems": prepend_items,
                            "appendItems": [],
                            "hasMore": new_end < total,
                            "replaceWindow": False,
                            "windowExpandIncremental": True,
                            "windowStart": new_start,
                            "windowEnd": new_end,
                            "windowPhase": "scroll_prepend",
                            "windowTrimmedEnd": trimmed_end,
                            "timing": {
                                "buildMs": build_ms,
                                "prependCount": len(prepend_items),
                                "itemCount": len(prepend_items),
                            },
                        }
                    return {
                        "state": self._gallery_state(),
                        "items": [],
                        "hasMore": new_end < total,
                        "replaceWindow": False,
                    }
                return self._gallery_load_window(target)

            if loaded >= target:
                return {
                    "state": self._gallery_state(),
                    "items": [],
                    "hasMore": loaded < total,
                    "replaceWindow": False,
                }

            # Tras un salto: extender solo el tramo nuevo hacia adelante (append).
            if window_start > 0 and loaded >= window_start:
                gap = max(0, target - loaded)
                extend_batches = self._extend_batch_count(gap, batch)
                new_end = min(total, loaded + batch * extend_batches)
                new_end = min(new_end, target + batch)
                if new_end <= loaded:
                    return {
                        "state": self._gallery_state(),
                        "items": [],
                        "hasMore": loaded < total,
                        "replaceWindow": False,
                    }
                t_build = time.perf_counter()
                batch_items = self._gallery_items_for_range(loaded, new_end)
                build_ms = int((time.perf_counter() - t_build) * 1000)
                self.gallery_unlimited_loaded = new_end
                trimmed = self._maybe_trim_sliding_window()
                return {
                    "state": self._gallery_state(),
                    "items": batch_items,
                    "hasMore": new_end < total,
                    "replaceWindow": False,
                    "windowStart": window_start,
                    "windowEnd": new_end,
                    "windowPhase": "scroll_append",
                    "windowTrimmed": trimmed,
                    "timing": {"buildMs": build_ms, "itemCount": len(batch_items)},
                }

            # Modo append desde el inicio: extender sin reemplazar ítems ya cargados.
            start = loaded
            gap = max(0, target - start)
            extend_batches = self._extend_batch_count(gap, batch)
            end = min(total, start + batch * extend_batches)
            end = min(end, target + batch)
            batch_items = self._gallery_items_for_range(start, end)
            self.gallery_unlimited_loaded = end
            return {
                "state": self._gallery_state(),
                "items": batch_items,
                "hasMore": end < total,
                "replaceWindow": False,
                "windowStart": 0,
                "windowEnd": end,
            }

    def gallery_open_folder_tile(self, path: str) -> dict:
        return self.gallery_load_folder(path)

    def gallery_thumb_hq(self, path: str, scale: float) -> dict:
        from ..core.fs_path import resolve_file_path

        p = resolve_file_path(path)
        thumb_px = _thumb_px_from_gallery_scale(float(scale))
        item_path = self._gallery_item_path(p)
        return {
            "path": item_path,
            "thumbDataUrl": self._thumb_data_url_cached(p, thumb_px, "hq"),
            "thumbQuality": "hq",
        }

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
