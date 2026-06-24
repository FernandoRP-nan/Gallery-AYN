"""Formato de reproducción del visor integrado (MP4/H.264 vs WebM según motor)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from .video_transcode import (
    ensure_transcoded_mp4,
    ensure_transcoded_webm,
    is_browser_playable,
    is_webm_playable,
    transcode_output_path,
    transcode_webm_output_path,
    warm_transcode_async,
    warm_webm_transcode_async,
)


def _qt_has_proprietary_codecs() -> bool:
    """True si hay Qt WebEngine compilado con H.264 (p. ej. freeworld en Fedora)."""
    if os.environ.get("ORGANIZADOR_QT_PROPRIETARY_CODECS", "").lower() in ("1", "true", "yes"):
        return True
    try:
        result = subprocess.run(
            ["rpm", "-q", "qt6-qtwebengine-freeworld"],
            capture_output=True,
            timeout=3,
            check=False,
        )
        if result.returncode == 0:
            return True
    except Exception:
        pass
    try:
        import PyQt6  # type: ignore

        plugins = Path(PyQt6.__file__).resolve().parent / "Qt6" / "plugins" / "webview"
        for lib in plugins.glob("libffmpeg*.so*"):
            if lib.stat().st_size > 1_500_000:
                return True
    except Exception:
        pass
    return False


def viewer_prefers_webm() -> bool:
    """WebM (VP8) evita H.264 cuando Qt WebEngine no trae códecs propietarios."""
    forced = os.environ.get("ORGANIZADOR_WEBM_PLAYBACK", "").lower()
    if forced in ("1", "true", "yes"):
        return True
    if forced in ("0", "false", "no"):
        return False
    if os.environ.get("ORGANIZADOR_MP4_PLAYBACK", "").lower() in ("1", "true", "yes"):
        return False
    if not sys.platform.startswith("linux"):
        return False
    gui = os.environ.get("PYWEBVIEW_GUI", "qt").lower()
    if gui != "qt":
        return False
    return not _qt_has_proprietary_codecs()


def viewer_engine_label() -> str:
    gui = os.environ.get("PYWEBVIEW_GUI", "qt" if sys.platform.startswith("linux") else "other")
    if viewer_prefers_webm():
        return f"{gui} · WebM (sin H.264 en Qt)"
    return f"{gui} · MP4/H.264"


def needs_viewer_transcode(path: Path) -> bool:
    if viewer_prefers_webm():
        if path.suffix.lower() == ".webm":
            return not is_webm_playable(path)
        return True
    return not is_browser_playable(path)


def ensure_viewer_playback(path: Path) -> tuple[Path, str]:
    """Devuelve (archivo, mime) listo para el visor integrado."""
    if viewer_prefers_webm():
        out = ensure_transcoded_webm(path)
        return out, "video/webm"
    out = ensure_transcoded_mp4(path)
    return out, "video/mp4"


def warm_viewer_playback_async(path: Path) -> None:
    if viewer_prefers_webm():
        warm_webm_transcode_async(path)
    else:
        warm_transcode_async(path)


def viewer_playback_cache_status(path: Path) -> dict:
    if viewer_prefers_webm():
        cached = transcode_webm_output_path(path)
        mime = "video/webm"
        fmt = "webm"
    else:
        cached = transcode_output_path(path)
        mime = "video/mp4"
        fmt = "mp4"
    ok = cached.is_file() and cached.stat().st_size > 512
    return {
        "playbackFormat": fmt,
        "playbackMime": mime,
        "transcodeCached": ok,
        "transcodeCacheBytes": cached.stat().st_size if ok else 0,
        "transcodeCachePath": str(cached) if ok else None,
    }
