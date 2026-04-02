"""API bridge para PyWebView (frontend web -> backend Python)."""

from __future__ import annotations

import base64
import io
import os
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .fs_utils import ensure_unique_destination
from .gallery_images import make_thumbnail_photoimage
from .gallery_paths import list_subdirs, scan_images_flat
from .media_organizer import MediaOrganizer
from .settings import load_app_settings, save_app_settings

try:
    from PIL import Image, ImageOps
except Exception:  # pragma: no cover
    Image = None
    ImageOps = None


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


class WebApi:
    """Estado y operaciones principales para la UI web."""

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

    def _is_unlimited_mode(self) -> bool:
        return int(self.settings.get("gallery_thumbs_per_page", 48)) <= 0

    def _unlimited_batch_size(self) -> int:
        return 48

    def _clear_thumb_cache(self) -> None:
        self._thumb_cache.clear()

    def _thumb_data_url_cached(self, path: Path, thumb_px: int, profile: str = "hq") -> str | None:
        key = (str(path.resolve()), thumb_px, profile)
        try:
            mtime = path.stat().st_mtime
        except OSError:
            return None
        with self._thumb_cache_lock:
            hit = self._thumb_cache.get(key)
            if hit is not None and hit[0] == mtime:
                return hit[1]
        if profile == "lq":
            # Fase 1: miniatura rápida (menos calidad) para pintar la rejilla antes.
            data = _thumb_jpeg_data_url_square(path, max(48, int(thumb_px * 0.55)), quality=40)
        else:
            # Fase 2: miniatura nítida.
            data = _thumb_jpeg_data_url_square(path, int(round(thumb_px * 1.35)), quality=96)
        with self._thumb_cache_lock:
            self._thumb_cache[key] = (mtime, data)
        return data

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
        pins = self.settings.get("gallery_pinned_folders")
        if not isinstance(pins, list):
            pins = []
            self.settings["gallery_pinned_folders"] = pins
        return [str(x) for x in pins if str(x).strip()]

    def get_initial_state(self) -> dict:
        return {
            "settings": self.settings,
            "gallery": self._gallery_state(),
            "destinations": list(self._destinations_list()),
        }

    def gallery_pin_folder(self, raw_path: str) -> dict:
        p = str(Path(raw_path).expanduser().resolve())
        pins = self._pinned_folders()
        if p not in pins:
            pins.insert(0, p)
            self.settings["gallery_pinned_folders"] = pins[:40]
            save_app_settings(self.settings)
        return {"pinnedFolders": list(self.settings.get("gallery_pinned_folders", []))}

    def gallery_unpin_folder(self, raw_path: str) -> dict:
        p = str(Path(raw_path).expanduser().resolve())
        pins = [x for x in self._pinned_folders() if x != p]
        self.settings["gallery_pinned_folders"] = pins
        save_app_settings(self.settings)
        return {"pinnedFolders": pins}

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

    def _build_image_items(self, slice_paths: list[Path], thumb_px: int, selected_frozenset: frozenset[Path]) -> list[dict]:
        def _one_image_item(p: Path) -> dict:
            return {
                "kind": "image",
                "name": p.name,
                "path": str(p),
                "selected": p in selected_frozenset,
                "thumbDataUrl": self._thumb_data_url_cached(p, thumb_px, "lq"),
                "thumbQuality": "lq",
            }

        if not slice_paths:
            return []
        max_workers = min(8, max(1, len(slice_paths)))
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            return list(pool.map(_one_image_item, slice_paths))

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

    def _build_gallery_items(self) -> list[dict]:
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
            self.ordered_paths = scan_images_flat(folder)
            self._schedule_gallery_total_bytes_recompute()
            self.selected.clear()
            self.gallery_page = 0
            self.gallery_unlimited_loaded = (
                min(len(self.ordered_paths), self._unlimited_batch_size()) if self._is_unlimited_mode() else 0
            )
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
            self.ordered_paths = scan_images_flat(folder)
            self._schedule_gallery_total_bytes_recompute()
            self._clamp_page()
            if self._is_unlimited_mode():
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

    def gallery_preview(self, path: str, width: int, height: int) -> dict:
        p = Path(path)
        data_url = _img_to_data_url_contain(p, max(80, int(width)), max(80, int(height)))
        return {"path": str(p), "name": p.name, "dataUrl": data_url}

    def destination_move_selected(self, dest_path: str) -> dict:
        dest_dir = Path(dest_path).expanduser().resolve()
        dest_dir.mkdir(parents=True, exist_ok=True)
        moved = 0
        errors = 0
        with self.lock:
            for src in list(self.selected):
                try:
                    target = ensure_unique_destination(dest_dir / src.name)
                    if src.resolve() == target.resolve():
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(src), str(target))
                    moved += 1
                except Exception:
                    errors += 1
            self.selected.clear()
        data = self.gallery_reload()
        data["moveResult"] = {"moved": moved, "errors": errors}
        return data

    def gallery_delete_selected(self) -> dict:
        """Elimina del disco las imágenes seleccionadas en la galería."""
        deleted = 0
        errors = 0
        with self.lock:
            for src in list(self.selected):
                try:
                    if src.is_file():
                        src.unlink()
                        deleted += 1
                except Exception:
                    errors += 1
            self.selected.clear()
        data = self.gallery_reload()
        data["deleteResult"] = {"deleted": deleted, "errors": errors}
        return data

    def gallery_delete_paths(self, paths: list[str]) -> dict:
        """Elimina una lista explícita de rutas (p. ej. imagen actual en fullscreen)."""
        deleted = 0
        errors = 0
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
                    src = Path(raw).expanduser().resolve()
                    if src.is_file():
                        src.unlink()
                        deleted += 1
                except Exception:
                    errors += 1
            self.selected = {p for p in self.selected if p.exists()}
        data = self.gallery_reload()
        data["deleteResult"] = {"deleted": deleted, "errors": errors}
        return data

    def gallery_move_path(self, src_path: str, dest_path: str) -> dict:
        """Mueve una sola imagen a un destino desde fullscreen."""
        moved = 0
        errors = 0
        src = Path(src_path).expanduser().resolve()
        dest_dir = Path(dest_path).expanduser().resolve()
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
            if src.is_file():
                target = ensure_unique_destination(dest_dir / src.name)
                if src.resolve() != target.resolve():
                    shutil.move(str(src), str(target))
                    moved = 1
                    self._last_gallery_move = (target, src)
        except Exception:
            errors = 1
        data = self.gallery_reload()
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
        data = self.gallery_reload()
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

    def gallery_thumb_hq(self, path: str, scale: float) -> dict:
        p = Path(path).expanduser().resolve()
        thumb_px = _thumb_px_from_gallery_scale(float(scale))
        return {"path": str(p), "thumbDataUrl": self._thumb_data_url_cached(p, thumb_px, "hq"), "thumbQuality": "hq"}

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
        data = self.gallery_reload()
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

    def settings_patch(self, data: dict) -> dict:
        self.settings.update(data)
        save_app_settings(self.settings)
        return {"settings": self.settings}

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
                expanded = Path(os.path.expandvars(os.path.expanduser(raw))).resolve()
                if expanded.is_dir():
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
