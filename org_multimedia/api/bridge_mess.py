from __future__ import annotations

"""API: carpeta desorden y agrupación por similitud."""

import os
import shutil
import threading
from pathlib import Path

from ..core.fs_utils import ensure_unique_destination
from ..core.settings import load_app_settings, save_app_settings
from ..core.thumbs import thumb_jpeg_data_url_square
from ..ia.mess_clusters import cluster_image_paths
from ..ia.mess_list import list_mess_image_paths
from ..ia.mess_similar import find_similar_paths

_THUMB_PX = 120
_THUMBS_PER_CLUSTER = 10


class MessBridgeMixin:
    def _mess_cluster_meta(self, clusters: list[dict]) -> list[dict]:
        """Metadatos sin data-URLs (el JSON del escaneo puede ser enorme)."""
        out = []
        for c in clusters:
            paths = list(c.get("paths") or [])
            out.append(
                {
                    "id": c.get("id"),
                    "count": len(paths),
                    "paths": paths,
                    "items": [{"path": p, "name": Path(p).name, "thumbDataUrl": None} for p in paths[:_THUMBS_PER_CLUSTER]],
                    "moreCount": max(0, len(paths) - min(len(paths), _THUMBS_PER_CLUSTER)),
                }
            )
        return out

    def mess_thumbs(self, paths: list[str], size: int = _THUMB_PX) -> dict:
        """Miniaturas LQ para el panel desorden (lotes pequeños desde el cliente)."""
        px = max(48, min(240, int(size)))
        items = []
        seen: set[str] = set()
        for raw in paths or []:
            s = str(raw).strip()
            if not s or s in seen:
                continue
            seen.add(s)
            p = Path(s)
            if not p.is_file():
                continue
            items.append(
                {
                    "path": s,
                    "name": p.name,
                    "thumbDataUrl": thumb_jpeg_data_url_square(p, px, quality=82),
                }
            )
        return {"items": items}

    def mess_list_images(self, folder_path: str | None = None, limit: int | None = None) -> dict:
        """Lista imágenes de la carpeta desorden para la franja de sugerencias."""
        raw = (folder_path or self.settings.get("mess_folder_path") or "").strip()
        if not raw:
            return {"ok": False, "error": "Indica la carpeta desorden.", "paths": [], "folder": ""}
        folder = Path(os.path.expandvars(os.path.expanduser(raw))).resolve()
        if not folder.is_dir():
            return {"ok": False, "error": "Carpeta desorden inválida.", "paths": [], "folder": str(folder)}
        max_files = int(limit if limit is not None else self.settings.get("mess_scan_max_files", 400))
        max_files = max(20, min(2000, max_files))
        out = list_mess_image_paths(folder, max_files)
        return {"ok": True, "folder": str(folder), **out}

    def mess_scan_start(self, folder_path: str, min_similarity: float | None = None) -> dict:
        job = getattr(self, "_mess_scan_job", None)
        if job and job.get("running"):
            return {"ok": False, "error": "Ya hay un análisis en curso."}
        raw = (folder_path or self.settings.get("mess_folder_path") or "").strip()
        if not raw:
            return {"ok": False, "error": "Indica la carpeta desorden."}
        folder = Path(os.path.expandvars(os.path.expanduser(raw))).resolve()
        if not folder.is_dir():
            return {"ok": False, "error": "Carpeta inválida."}

        sim = float(min_similarity if min_similarity is not None else self.settings.get("mess_similarity_min", 0.82))
        sim = max(0.5, min(0.98, sim))
        max_files = int(self.settings.get("mess_scan_max_files", 400))
        max_files = max(50, min(2000, max_files))
        cancel_event = threading.Event()
        scan_job: dict = {
            "running": True,
            "progress": {"current": 0, "total": 0, "detail": "Iniciando…"},
            "result": None,
            "error": None,
            "cancelEvent": cancel_event,
        }
        self._mess_scan_job = scan_job

        def worker() -> None:
            try:
                def on_progress(cur: int, total: int, detail: str) -> None:
                    scan_job["progress"] = {"current": cur, "total": total, "detail": detail}

                raw_result = cluster_image_paths(
                    folder,
                    sim,
                    progress=on_progress,
                    cancel_event=cancel_event,
                    max_files=max_files,
                )
                if raw_result.get("cancelled"):
                    scan_job["result"] = None
                    scan_job["error"] = "cancelled"
                else:
                    clusters = self._mess_cluster_meta(raw_result.get("clusters") or [])
                    scan_job["result"] = {
                        **raw_result,
                        "clusters": clusters,
                        "folder": str(folder),
                        "minSimilarity": sim,
                    }
            except Exception as exc:
                scan_job["error"] = str(exc)
            finally:
                scan_job["running"] = False

        threading.Thread(target=worker, daemon=True).start()
        return {"ok": True}

    def mess_scan_cancel(self) -> dict:
        job = getattr(self, "_mess_scan_job", None)
        if job and job.get("cancelEvent") is not None:
            job["cancelEvent"].set()
        return {"ok": True}

    def mess_scan_status(self) -> dict:
        job = getattr(self, "_mess_scan_job", None)
        if not job:
            return {
                "running": False,
                "progress": {"current": 0, "total": 0, "detail": "Sin análisis"},
                "result": None,
                "error": None,
            }
        out = {
            "running": bool(job.get("running")),
            "progress": dict(job.get("progress") or {}),
            "result": job.get("result"),
            "error": job.get("error"),
        }
        return out

    def mess_similar_paths(
        self,
        anchor_path: str,
        candidate_paths: list[str],
        min_similarity: float | None = None,
        limit: int = 32,
    ) -> dict:
        """«Más como esta»: similitud respecto a una foto del análisis actual."""
        anchor = str(anchor_path or "").strip()
        if not anchor:
            return {"ok": False, "error": "Ruta ancla vacía.", "items": []}
        sim = float(min_similarity if min_similarity is not None else self.settings.get("mess_similarity_min", 0.82))
        sim = max(0.5, min(0.98, sim))
        items = find_similar_paths(anchor, candidate_paths or [], sim, limit=limit)
        return {"ok": True, "anchor": anchor, "items": items}

    def mess_move_cluster(self, src_paths: list[str], dest_path: str) -> dict:
        """Mueve un grupo de imágenes a la carpeta destino (p. ej. carpeta actual de la galería)."""
        dest_dir = Path(dest_path).expanduser().resolve()
        if not dest_dir.is_dir():
            try:
                dest_dir.mkdir(parents=True, exist_ok=True)
            except OSError:
                return {"ok": False, "error": "Destino inválido.", "moved": 0, "errors": len(src_paths or [])}

        moved = 0
        errors = 0
        moved_paths: list[str] = []
        seen: set[str] = set()
        with self.lock:
            for raw in src_paths or []:
                s = str(raw).strip()
                if not s or s in seen:
                    continue
                seen.add(s)
                try:
                    src = Path(s).expanduser().resolve()
                    if not src.is_file():
                        errors += 1
                        continue
                    target = ensure_unique_destination(dest_dir / src.name)
                    if src.resolve() == target.resolve():
                        continue
                    shutil.move(str(src), str(target))
                    moved += 1
                    moved_paths.append(str(src))
                except OSError:
                    errors += 1
            if moved_paths:
                moved_src = {Path(x).expanduser().resolve() for x in moved_paths}
                self.selected = {p for p in self.selected if p not in moved_src and p.exists()}

        gallery_data = None
        if hasattr(self, "gallery_reindex_delta") and moved_paths:
            gallery_data = self.gallery_reindex_delta(moved_paths)
        elif hasattr(self, "gallery_reload") and errors > 0:
            gallery_data = self.gallery_reload(clear_thumb_cache=False)

        return {
            "ok": errors == 0,
            "moved": moved,
            "errors": errors,
            "gallery": gallery_data,
        }

    def mess_save_settings(self, folder_path: str, min_similarity: float | None = None) -> dict:
        self.settings["mess_folder_path"] = str(folder_path or "").strip()
        if min_similarity is not None:
            sim = max(0.5, min(0.98, float(min_similarity)))
            self.settings["mess_similarity_min"] = sim
        save_app_settings(self.settings)
        return {"settings": self.settings}
