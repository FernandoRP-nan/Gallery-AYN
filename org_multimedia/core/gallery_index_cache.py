"""Índice persistente de carpetas (sobrevive reinicios de la app)."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
from pathlib import Path

_CACHE_VERSION = 1


def _index_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return Path(base) / "organizador_multimedia" / "gallery_index"


def _cache_id(folder: Path, settings_key: tuple) -> str:
    payload = json.dumps([str(folder.resolve()), list(settings_key)], sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def _meta_path(cache_id: str) -> Path:
    return _index_dir() / f"{cache_id}.meta.json"


def _paths_path(cache_id: str) -> Path:
    return _index_dir() / f"{cache_id}.paths.gz"


def _folder_mtime_ns(folder: Path) -> int:
    try:
        return folder.stat().st_mtime_ns
    except OSError:
        return 0


def _serialize_spans(spans: list[tuple]) -> list[list]:
    return [list(row) for row in spans]


def _parse_path_line(raw: str) -> Path | None:
    """Paths ya persistidos resueltos; evitar resolve() masivo (I/O en /mnt)."""
    s = raw.strip()
    if not s:
        return None
    return Path(s)


def _paths_file_valid(paths: list[Path], sample: int = 5) -> bool:
    if not paths:
        return False
    checks = {0, len(paths) // 2, len(paths) - 1}
    for i in list(checks)[:sample]:
        try:
            if not paths[i].is_file():
                return False
        except (OSError, IndexError):
            return False
    return True


def _deserialize_spans(raw: list | None) -> list[tuple]:
    if not raw:
        return []
    return [tuple(row) for row in raw]


def try_load_gallery_index(
    folder: Path,
    settings_key: tuple,
) -> dict | None:
    """Devuelve paths y metadatos si el índice en disco sigue siendo válido."""
    cid = _cache_id(folder, settings_key)
    meta_file = _meta_path(cid)
    paths_file = _paths_path(cid)
    if not meta_file.is_file() or not paths_file.is_file():
        return None
    try:
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        if int(meta.get("version", 0)) != _CACHE_VERSION:
            return None
        if meta.get("folder") != str(folder.resolve()):
            return None
        if meta.get("settings_key") != list(settings_key):
            return None
        if int(meta.get("folder_mtime_ns", -1)) != _folder_mtime_ns(folder):
            return None
        with gzip.open(paths_file, "rt", encoding="utf-8") as fh:
            paths: list[Path] = []
            for line in fh:
                p = _parse_path_line(line)
                if p is not None:
                    paths.append(p)
        if int(meta.get("path_count", -1)) != len(paths):
            return None
        if not _paths_file_valid(paths):
            _meta_path(cid).unlink(missing_ok=True)
            _paths_path(cid).unlink(missing_ok=True)
            return None
        return {
            "paths": paths,
            "section_spans": _deserialize_spans(meta.get("section_spans")),
            "timeline_spans": _deserialize_spans(meta.get("timeline_spans")),
            "alpha_spans": _deserialize_spans(meta.get("alpha_spans")),
        }
    except (OSError, json.JSONDecodeError, ValueError):
        return None


def save_gallery_index(
    folder: Path,
    settings_key: tuple,
    paths: list[Path],
    *,
    section_spans: list[tuple] | None = None,
    timeline_spans: list[tuple] | None = None,
    alpha_spans: list[tuple] | None = None,
) -> None:
    """Persiste el listado ordenado (escritura en segundo plano segura)."""
    if not paths:
        return
    cid = _cache_id(folder, settings_key)
    root = _index_dir()
    root.mkdir(parents=True, exist_ok=True)
    meta = {
        "version": _CACHE_VERSION,
        "folder": str(folder.resolve()),
        "settings_key": list(settings_key),
        "folder_mtime_ns": _folder_mtime_ns(folder),
        "path_count": len(paths),
        "section_spans": _serialize_spans(section_spans or []),
        "timeline_spans": _serialize_spans(timeline_spans or []),
        "alpha_spans": _serialize_spans(alpha_spans or []),
    }
    paths_file = _paths_path(cid)
    meta_file = _meta_path(cid)
    tmp_paths = paths_file.with_name(paths_file.name + ".tmp")
    tmp_meta = meta_file.with_name(meta_file.name + ".tmp")
    try:
        with gzip.open(tmp_paths, "wt", encoding="utf-8") as fh:
            for p in paths:
                fh.write(str(p.resolve()))
                fh.write("\n")
        tmp_meta.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        tmp_paths.replace(paths_file)
        tmp_meta.replace(meta_file)
    except OSError:
        tmp_paths.unlink(missing_ok=True)
        tmp_meta.unlink(missing_ok=True)


def invalidate_gallery_index(folder: Path | None = None) -> None:
    """Borra índices (uno o todos)."""
    root = _index_dir()
    if not root.is_dir():
        return
    if folder is None:
        for p in root.glob("*"):
            p.unlink(missing_ok=True)
        return
    for meta in root.glob("*.meta.json"):
        try:
            data = json.loads(meta.read_text(encoding="utf-8"))
            if data.get("folder") == str(folder.resolve()):
                cid = meta.name[: -len(".meta.json")]
                _meta_path(cid).unlink(missing_ok=True)
                _paths_path(cid).unlink(missing_ok=True)
                return
        except (OSError, json.JSONDecodeError):
            continue
