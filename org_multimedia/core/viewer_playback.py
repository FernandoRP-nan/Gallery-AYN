"""Formato de reproducción del visor integrado (MP4/H.264 vs WebM según motor)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from .video_playback_mode import list_video_playback_profiles, normalize_playback_mode
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


def qt_has_proprietary_codecs() -> bool:
    """True si Qt WebEngine puede reproducir H.264 (p. ej. freeworld en Fedora)."""
    return _qt_has_proprietary_codecs()


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


def needs_viewer_transcode(path: Path, *, playback_mode: str = "auto") -> bool:
    mode = normalize_playback_mode(playback_mode)
    if mode == "direct":
        return False
    if mode in ("remux", "turbo", "fast", "quality"):
        return True

    from .video_tools import ffprobe_available

    if viewer_prefers_webm():
        if path.suffix.lower() == ".webm":
            if not ffprobe_available():
                return True
            return not is_webm_playable(path)
        return True
    if not ffprobe_available():
        return path.suffix.lower() not in (".mp4", ".m4v")
    return not is_browser_playable(path)


def viewer_playback_strategy(path: Path, *, playback_mode: str = "auto") -> str:
    """direct = sin conversión; remux = copiar a MP4; encode = re-codificar (lento)."""
    mode = normalize_playback_mode(playback_mode)
    if mode == "direct":
        return "direct"
    if mode == "remux":
        return "remux"
    if mode in ("turbo", "fast", "quality"):
        return "encode"

    if not needs_viewer_transcode(path, playback_mode="auto"):
        return "direct"
    if viewer_prefers_webm():
        return "encode"
    from .video_transcode import _ffprobe_streams, mp4_playback_mode

    video, audio = _ffprobe_streams(path)
    plan = mp4_playback_mode(video, audio)
    if plan in ("copy_all", "copy_video_aac"):
        return "remux"
    return "encode"


def ensure_viewer_playback(path: Path, *, playback_mode: str = "auto") -> tuple[Path, str]:
    """Devuelve (archivo, mime) listo para el visor integrado."""
    mode = normalize_playback_mode(playback_mode)
    if viewer_prefers_webm():
        out = ensure_transcoded_webm(path)
        return out, "video/webm"
    out = ensure_transcoded_mp4(path, playback_mode=mode)
    return out, "video/mp4"


def warm_viewer_playback_async(
    path: Path,
    *,
    playback_mode: str = "auto",
    priority: int | None = None,
) -> None:
    from .video_transcode import TRANSCODE_PRIORITY_USER, TRANSCODE_PRIORITY_WARM, prioritize_transcode_for_path

    mode = normalize_playback_mode(playback_mode)
    prio = priority if priority is not None else TRANSCODE_PRIORITY_WARM
    if viewer_prefers_webm():
        warm_webm_transcode_async(path)
        if prio >= TRANSCODE_PRIORITY_USER:
            prioritize_transcode_for_path(path, playback_mode=mode)
    else:
        warm_transcode_async(path, playback_mode=mode, priority=prio)
        if prio >= TRANSCODE_PRIORITY_USER:
            prioritize_transcode_for_path(path, playback_mode=mode)


def viewer_playback_cache_status(path: Path, *, playback_mode: str = "auto") -> dict:
    mode = normalize_playback_mode(playback_mode)
    if viewer_prefers_webm():
        cached = transcode_webm_output_path(path)
        mime = "video/webm"
        fmt = "webm"
    else:
        cached = transcode_output_path(path, playback_mode=mode)
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


def video_playback_profiles(path: Path) -> list[dict[str, object]]:
    return list_video_playback_profiles(path)
