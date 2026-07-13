"""Precalentamiento de índices de galería en segundo plano."""

from __future__ import annotations

import threading
import time
from typing import Any, Protocol


class IndexWarmApi(Protocol):
    """Superficie mínima del bridge para indexar carpetas."""

    def _warm_single_folder(self, folder_path: str) -> dict: ...

    def _warm_dest_preview_index(self, folder_path: str) -> dict: ...

    def _warm_videos_for_folder(self, folder_path: str) -> dict: ...


class GalleryIndexWarmService:
    """Cola de carpetas a indexar (un hilo, cancelable)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cancel = False
        self._thread: threading.Thread | None = None
        self._status: dict[str, Any] = self._idle_status()

    @staticmethod
    def _idle_status() -> dict[str, Any]:
        return {
            "running": False,
            "done": 0,
            "total": 0,
            "currentPath": "",
            "errors": [],
            "cancelled": False,
        }

    def status(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._status)

    def cancel(self) -> dict[str, Any]:
        with self._lock:
            self._cancel = True
            return dict(self._status)

    def start(self, api: IndexWarmApi, paths: list[str]) -> dict[str, Any]:
        unique = self._unique_valid_paths(paths)
        with self._lock:
            if self._thread and self._thread.is_alive():
                return dict(self._status)
            self._cancel = False
            self._status = {
                "running": True,
                "done": 0,
                "total": len(unique),
                "currentPath": "",
                "errors": [],
                "cancelled": False,
            }
            self._thread = threading.Thread(
                target=self._run,
                args=(api, unique),
                daemon=True,
                name="om-gallery-index-warm",
            )
            self._thread.start()
            return dict(self._status)

    @staticmethod
    def _unique_valid_paths(paths: list[str]) -> list[str]:
        from pathlib import Path

        out: list[str] = []
        seen: set[str] = set()
        for raw in paths or []:
            text = str(raw or "").strip()
            if not text or text in seen:
                continue
            try:
                p = Path(text).expanduser().resolve()
            except OSError:
                continue
            if not p.is_dir():
                continue
            key = str(p)
            seen.add(key)
            out.append(key)
        return out

    def _run(self, api: IndexWarmApi, paths: list[str]) -> None:
        errors: list[dict[str, str]] = []
        for idx, folder_path in enumerate(paths):
            with self._lock:
                if self._cancel:
                    self._status["cancelled"] = True
                    self._status["running"] = False
                    return
                self._status["currentPath"] = folder_path
            try:
                out = api._warm_single_folder(folder_path)
                if not out.get("ok"):
                    errors.append(
                        {"path": folder_path, "error": str(out.get("error") or "error")}
                    )
                prev = api._warm_dest_preview_index(folder_path)
                if not prev.get("ok"):
                    errors.append(
                        {"path": folder_path, "error": str(prev.get("error") or "preview")}
                    )
                api._warm_videos_for_folder(folder_path)
            except Exception as exc:
                errors.append({"path": folder_path, "error": str(exc)})
            with self._lock:
                self._status["done"] = idx + 1
                self._status["errors"] = list(errors)
            time.sleep(0.02)
        with self._lock:
            self._status["running"] = False
            self._status["currentPath"] = ""
