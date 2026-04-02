"""API bridge para PyWebView (frontend web -> backend Python)."""

from __future__ import annotations

import base64
import io
import os
import shutil
import threading
import time
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
    """Escala lineal 0.75–2.25 → ~80–340 px (muchos pasos visibles, sin saltos por columnas)."""
    lo, hi = 0.75, 2.25
    px_min, px_max = 80, 340
    s = max(lo, min(hi, float(scale)))
    return int(round(px_min + (s - lo) / (hi - lo) * (px_max - px_min)))


def _thumb_px_from_dest_scale(scale: float) -> int:
    """Vista previa de carpeta destino (rango de escala distinto en la UI)."""
    lo, hi = 0.7, 2.1
    px_min, px_max = 72, 320
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


class WebApi:
    """Estado y operaciones principales para la UI web."""

    def __init__(self) -> None:
        self.settings = load_app_settings()
        self.gallery_folder: Path | None = None
        self.ordered_paths: list[Path] = []
        self.subfolders: list[Path] = []
        self.selected: set[Path] = set()
        self.gallery_page = 0
        self.lock = threading.RLock()
        self._organizer_job: dict | None = None
        # Caché (ruta resuelta, tamaño px) -> (mtime, data_url) para no re-encodear PNG en cada clic
        self._thumb_cache: dict[tuple[str, int], tuple[float, str | None]] = {}

    def _clear_thumb_cache(self) -> None:
        self._thumb_cache.clear()

    def _thumb_data_url_cached(self, path: Path, thumb_px: int) -> str | None:
        key = (str(path.resolve()), thumb_px)
        try:
            mtime = path.stat().st_mtime
        except OSError:
            return None
        hit = self._thumb_cache.get(key)
        if hit is not None and hit[0] == mtime:
            return hit[1]
        data = _img_to_data_url(path, (thumb_px, thumb_px))
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

    def get_initial_state(self) -> dict:
        return {
            "settings": self.settings,
            "gallery": self._gallery_state(),
            "destinations": self.settings.get("destinations", []),
        }

    def _thumbs_per_page(self) -> int:
        n = int(self.settings.get("gallery_thumbs_per_page", 120))
        return max(30, min(300, n))

    def _total_pages(self) -> int:
        total = len(self.ordered_paths)
        if total == 0:
            return 1
        ps = self._thumbs_per_page()
        return max(1, (total + ps - 1) // ps)

    def _clamp_page(self) -> None:
        tp = self._total_pages()
        self.gallery_page = max(0, min(self.gallery_page, tp - 1))

    def _slice(self) -> tuple[int, int]:
        ps = self._thumbs_per_page()
        s = self.gallery_page * ps
        e = min(len(self.ordered_paths), s + ps)
        return s, e

    def _gallery_state(self) -> dict:
        total = len(self.ordered_paths)
        tp = self._total_pages()
        self._clamp_page()
        s, e = self._slice()
        return {
            "folder": str(self.gallery_folder) if self.gallery_folder else "",
            "total": total,
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
            parent = self.gallery_folder.parent
            if parent != self.gallery_folder and parent.is_dir():
                items.append(
                    {"kind": "folder_up", "name": ".. Carpeta superior", "path": str(parent), "thumbDataUrl": None}
                )
            for sub in self.subfolders:
                items.append({"kind": "folder", "name": sub.name, "path": str(sub), "thumbDataUrl": None})
        thumb_px = _thumb_px_from_gallery_scale(float(self.settings.get("gallery_thumb_scale", 1.0)))
        for p in self.ordered_paths[s:e]:
            items.append(
                {
                    "kind": "image",
                    "name": p.name,
                    "path": str(p),
                    "selected": p in self.selected,
                    "thumbDataUrl": self._thumb_data_url_cached(p, thumb_px),
                }
            )
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
            self.selected.clear()
            self.gallery_page = 0
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
            self._clamp_page()
            return {"state": self._gallery_state(), "items": self._build_gallery_items()}

    def gallery_refresh_items(self) -> dict:
        """Solo reconstruye estado e ítems (sin reescaneo): útil tras toggle de selección."""
        with self.lock:
            if not self.gallery_folder:
                return {"state": self._gallery_state(), "items": []}
            return {"state": self._gallery_state(), "items": self._build_gallery_items()}

    def gallery_go_page(self, page_1: int) -> dict:
        with self.lock:
            self.gallery_page = max(0, int(page_1) - 1)
            self._clamp_page()
            return {"state": self._gallery_state(), "items": self._build_gallery_items()}

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
        data_url = _img_to_data_url(p, (max(80, int(width)), max(80, int(height))))
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

    def destination_preview(self, dest_path: str, scale: float, width: int) -> dict:
        folder = Path(dest_path).expanduser().resolve()
        paths = scan_images_flat(folder) if folder.is_dir() else []
        thumb = _thumb_px_from_dest_scale(float(scale))
        cols = max(2, min(10, int(max(400, width) // (thumb + 34))))
        items = []
        for p in paths:
            items.append(
                {"name": p.name, "path": str(p), "thumbDataUrl": _img_to_data_url(p, (thumb, thumb))}
            )
        return {"items": items, "cols": cols}

    def destinations_get(self) -> dict:
        return {"destinations": self.settings.get("destinations", [])}

    def destinations_add(self, label: str, path: str) -> dict:
        p = str(Path(path).expanduser().resolve())
        label = label.strip() or Path(p).name
        self.settings.setdefault("destinations", []).append({"label": label, "path": p})
        save_app_settings(self.settings)
        return self.destinations_get()

    def destinations_remove(self, idx: int) -> dict:
        dests = self.settings.get("destinations", [])
        if 0 <= idx < len(dests):
            dests.pop(idx)
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
