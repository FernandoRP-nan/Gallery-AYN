from __future__ import annotations

"""Precalentamiento de índices de galería (marcadores, destinos, hijos)."""

import time
from pathlib import Path

from ..core.fs_path import resolve_dir_path
from ..core.gallery_index_cache import (
    _cache_id,
    _meta_path,
    save_gallery_index,
    try_load_gallery_index,
)
from ..core.gallery_index_warm import GalleryIndexWarmService
from ..core.gallery_paths import scan_all_files_flat, scan_images_flat
from ..core.item_tree import collect_warm_paths


class GalleryIndexWarmBridgeMixin:
    """API y lógica de warm de índices en disco."""

    def _index_warm_service(self) -> GalleryIndexWarmService:
        svc = getattr(self, "_gallery_index_warm_service", None)
        if svc is None:
            svc = GalleryIndexWarmService()
            self._gallery_index_warm_service = svc
        return svc

    def _dest_preview_scan_cache_key(self, folder: Path) -> tuple:
        """Clave de índice plano para vista previa de destino."""
        return (
            str(folder.resolve()),
            False,
            bool(self.settings.get("gallery_show_other_files", False)),
            False,
            False,
            False,
            False,
            "name",
            "flat",
        )

    def _warm_single_folder(self, folder_path: str) -> dict:
        """Escanea y persiste índice de galería sin cambiar la carpeta activa."""
        try:
            folder = resolve_dir_path(folder_path)
        except (OSError, ValueError) as exc:
            return {"ok": False, "path": folder_path, "error": str(exc)}
        with self.lock:
            sec_b = list(self._gallery_section_spans)
            tl_b = list(self._gallery_timeline_spans)
            al_b = list(self._gallery_alpha_spans)
            try:
                ordered = self._scan_ordered_paths(folder)
                source = str(getattr(self, "_last_scan_source", "fresh"))
                return {
                    "ok": True,
                    "path": str(folder),
                    "source": source,
                    "count": len(ordered),
                }
            except Exception as exc:
                return {"ok": False, "path": str(folder), "error": str(exc)}
            finally:
                self._gallery_section_spans = sec_b
                self._gallery_timeline_spans = tl_b
                self._gallery_alpha_spans = al_b

    def _warm_dest_preview_index(self, folder_path: str) -> dict:
        """Índice ligero para modal «Ver carpeta» de destinos."""
        try:
            folder = resolve_dir_path(folder_path)
        except (OSError, ValueError) as exc:
            return {"ok": False, "path": folder_path, "error": str(exc)}
        key = self._dest_preview_scan_cache_key(folder)
        if try_load_gallery_index(folder, key) is not None:
            return {"ok": True, "path": str(folder), "source": "disk", "preview": True}
        show_other = bool(self.settings.get("gallery_show_other_files", False))
        paths = scan_all_files_flat(folder) if show_other else scan_images_flat(folder)
        if paths:
            try:
                save_gallery_index(folder, key, paths)
            except Exception as exc:
                return {"ok": False, "path": str(folder), "error": str(exc)}
        return {
            "ok": True,
            "path": str(folder),
            "source": "fresh",
            "preview": True,
            "count": len(paths),
        }

    def _collect_warm_path_list(self, include_children: bool | None = None) -> list[str]:
        markers = self._markers_tree() if hasattr(self, "_markers_tree") else []
        destinations = self._destinations_tree() if hasattr(self, "_destinations_tree") else []
        recent = self.settings.get("gallery_recent_folders")
        if not isinstance(recent, list):
            recent = []
        if include_children is None:
            include_children = bool(self.settings.get("gallery_warm_include_children", True))
        max_depth = int(self.settings.get("gallery_warm_max_depth", 2) or 2)
        return collect_warm_paths(
            markers,
            destinations,
            recent=[str(x) for x in recent if str(x).strip()],
            include_children=bool(include_children),
            max_depth=max_depth,
        )

    def gallery_index_warm_start(
        self, paths: list[str] | None = None, include_children: bool = True
    ) -> dict:
        """Encola precalentamiento de índices (None = marcadores + destinos + recientes)."""
        resolved = self._collect_warm_path_list(include_children) if not paths else list(paths)
        return self._index_warm_service().start(self, resolved)

    def gallery_index_warm_status(self) -> dict:
        return self._index_warm_service().status()

    def gallery_index_warm_cancel(self) -> dict:
        return self._index_warm_service().cancel()

    def gallery_index_status(self, raw_path: str) -> dict:
        """Estado del índice en disco/memoria para una carpeta."""
        try:
            folder = resolve_dir_path(raw_path)
        except (OSError, ValueError) as exc:
            return {"ok": False, "cached": False, "error": str(exc)}
        key = self._scan_cache_key(folder)
        preview_key = self._dest_preview_scan_cache_key(folder)
        source = "miss"
        path_count = 0
        age_sec: float | None = None

        disk = try_load_gallery_index(folder, key)
        if disk is not None:
            source = "disk"
            path_count = len(disk.get("paths") or [])
            cid = _cache_id(folder, key)
            meta_file = _meta_path(cid)
            if meta_file.is_file():
                age_sec = max(0.0, time.time() - meta_file.stat().st_mtime)
        else:
            cache: dict = getattr(self, "_gallery_scan_cache", {})
            hit = cache.get(key)
            if hit:
                source = "memory"
                path_count = len(hit.get("paths") or [])

        preview_cached = try_load_gallery_index(folder, preview_key) is not None
        return {
            "ok": True,
            "path": str(folder),
            "cached": source != "miss",
            "source": source,
            "pathCount": path_count,
            "ageSec": age_sec,
            "previewCached": preview_cached,
        }

    def gallery_index_warm_maybe_startup(self) -> None:
        """Arranque en segundo plano si el ajuste está activo."""
        if not bool(self.settings.get("gallery_warm_index_on_startup", False)):
            return
        paths = self._collect_warm_path_list()
        if paths:
            self._index_warm_service().start(self, paths)

    def _dest_preview_paths(self, folder: Path) -> list[Path]:
        """Lista de archivos para vista previa (índice en disco o scan fresco)."""
        key = self._dest_preview_scan_cache_key(folder)
        disk = try_load_gallery_index(folder, key)
        if disk is not None:
            return list(disk.get("paths") or [])
        show_other = bool(self.settings.get("gallery_show_other_files", False))
        paths = scan_all_files_flat(folder) if show_other else scan_images_flat(folder)
        if paths:
            try:
                save_gallery_index(folder, key, paths)
            except Exception:
                pass
        return paths
