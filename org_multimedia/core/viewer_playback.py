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


def _freeworld_rpm_installed() -> bool:
    """Paquetes RPM que habilitan H.264 en Qt WebEngine (Fedora/RHEL)."""
    for pkg in ("qt6-qtwebengine-freeworld", "qt5-qtwebengine-freeworld"):
        try:
            result = subprocess.run(
                ["rpm", "-q", pkg],
                capture_output=True,
                timeout=3,
                check=False,
            )
            if result.returncode == 0:
                return True
        except Exception:
            pass
    return False


def _qt_chromium_proprietary_codecs_enabled() -> bool:
    """True si Chromium arrancó con --proprietary-codecs (linux_gui_env)."""
    flags = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "")
    return "--proprietary-codecs" in flags.split()


def _openh264_rpm_installed() -> bool:
    try:
        result = subprocess.run(
            ["rpm", "-q", "openh264"],
            capture_output=True,
            timeout=3,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


def _pyqt6_system_install() -> bool:
    """PyQt6 del sistema (dnf), no el wheel aislado de pip en ~/.local."""
    try:
        import PyQt6  # type: ignore

        p = str(Path(PyQt6.__file__).resolve())
        if "/.local/" in p or "site-packages/PyQt6" in p and p.startswith("/home/"):
            return False
        return p.startswith("/usr/")
    except Exception:
        return False


def _qt_has_proprietary_codecs() -> bool:
    """True si H.264 en Qt está confirmado para reproducción directa."""
    if _QT_H264_PROBE_OK is False:
        return False
    if os.environ.get("ORGANIZADOR_QT_PROPRIETARY_CODECS", "").lower() in ("1", "true", "yes"):
        return True
    if _freeworld_rpm_installed():
        return True
    if _pyqt6_system_install() and _openh264_rpm_installed():
        return True
    try:
        import PyQt6  # type: ignore

        plugins = Path(PyQt6.__file__).resolve().parent / "Qt6" / "plugins" / "webview"
        for lib in plugins.glob("libffmpeg*.so*"):
            if lib.stat().st_size > 1_500_000:
                return True
    except Exception:
        pass
    return False


def openh264_rpm_installed() -> bool:
    return _openh264_rpm_installed()


def pyqt6_system_install() -> bool:
    return _pyqt6_system_install()


def freeworld_rpm_installed() -> bool:
    return _freeworld_rpm_installed()


def qt_chromium_proprietary_flag_enabled() -> bool:
    return _qt_chromium_proprietary_codecs_enabled()


def freeworld_install_hint() -> str | None:
    """Comandos sugeridos para reproducción directa en Fedora (sin transcodificar)."""
    if not sys.platform.startswith("linux"):
        return None
    if _qt_has_proprietary_codecs():
        return None
    gui = os.environ.get("PYWEBVIEW_GUI", "qt").lower()
    if gui != "qt":
        return None
    if not _openh264_rpm_installed():
        return "sudo dnf install openh264 mozilla-openh264"
    if not _pyqt6_system_install():
        return "pip uninstall PyQt6 PyQt6-WebEngine && sudo dnf install python3-pyqt6 python3-pyqt6-webengine"
    return "sudo dnf install openh264 mozilla-openh264 python3-pyqt6 python3-pyqt6-webengine"


_DIRECT_H264_REJECTED: set[str] = set()
_QT_H264_PROBE_OK: bool | None = None


def viewer_needs_webm_fallback(path: Path, *, playback_mode: str = "auto") -> bool:
    """True si hace falta exponer /om-webm/ como URL de respaldo."""
    if viewer_prefers_webm():
        return True
    if _QT_H264_PROBE_OK is False:
        return True
    mode = normalize_playback_mode(playback_mode)
    if mode == "auto" and viewer_can_try_direct_h264(path):
        return True
    return False


def viewer_playback_url_kind() -> str:
    """webm | mp4 según motor activo."""
    return "webm" if viewer_prefers_webm() else "mp4"


def mark_direct_h264_rejected(path: Path) -> None:
    """El visor no pudo reproducir H.264 directo; no reintentar /media en esta sesión."""
    global _QT_H264_PROBE_OK
    resolved = str(path.resolve())
    _DIRECT_H264_REJECTED.add(resolved)
    _QT_H264_PROBE_OK = False


def viewer_can_try_direct_h264(path: Path) -> bool:
    """MP4/M4V H.264: probar /media directo si H.264 en Qt está confirmado."""
    if _QT_H264_PROBE_OK is False:
        return False
    if str(path.resolve()) in _DIRECT_H264_REJECTED:
        return False
    if not _qt_has_proprietary_codecs():
        return False
    if not viewer_prefers_webm():
        return False
    from .video_tools import ffprobe_available

    if not ffprobe_available():
        return False
    return is_browser_playable(path)


def viewer_prefers_webm() -> bool:
    """WebM (VP8) evita H.264 cuando Qt WebEngine no trae códecs propietarios."""
    if _QT_H264_PROBE_OK is False:
        return True
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


def explain_viewer_transcode(path: Path, *, playback_mode: str = "auto") -> dict[str, str]:
    """Motivo legible de por qué un vídeo va directo o pasa por conversión."""
    mode = normalize_playback_mode(playback_mode)
    if mode == "direct":
        return {"needsTranscode": "no", "reason": "modo_original", "strategy": "direct"}
    if not needs_viewer_transcode(path, playback_mode=mode):
        return {"needsTranscode": "no", "reason": "compatible", "strategy": viewer_playback_strategy(path, playback_mode=mode)}

    if viewer_prefers_webm():
        if path.suffix.lower() == ".webm":
            return {"needsTranscode": "yes", "reason": "webm_no_compatible", "strategy": "encode"}
        return {"needsTranscode": "yes", "reason": "motor_webm", "strategy": "encode"}

    from .video_transcode import explain_browser_playable, mp4_playback_mode, _ffprobe_streams

    ok, detail = explain_browser_playable(path)
    if not ok:
        video, audio = _ffprobe_streams(path)
        plan = mp4_playback_mode(video, audio)
        strategy = "remux" if plan in ("copy_all", "copy_video_aac") else "encode"
        return {"needsTranscode": "yes", "reason": detail, "strategy": strategy}
    return {"needsTranscode": "no", "reason": "compatible", "strategy": "direct"}


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
        if mode == "auto" and viewer_can_try_direct_h264(path):
            return False
        return True
    if not ffprobe_available():
        ext = path.suffix.lower()
        return ext not in (".mp4", ".m4v", ".mov", ".3gp", ".3g2")
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
        if mode == "auto" and viewer_can_try_direct_h264(path):
            return "direct"
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
    from .video_transcode import _mp4_cache_valid, _webm_cache_valid, transcode_output_path, transcode_webm_output_path

    mode = normalize_playback_mode(playback_mode)
    if viewer_prefers_webm():
        cached = transcode_webm_output_path(path)
        mime = "video/webm"
        fmt = "webm"
        ok = _webm_cache_valid(cached)
    else:
        cached = transcode_output_path(path, playback_mode=mode)
        mime = "video/mp4"
        fmt = "mp4"
        ok = _mp4_cache_valid(cached)
    return {
        "playbackFormat": fmt,
        "playbackMime": mime,
        "transcodeCached": ok,
        "transcodeCacheBytes": cached.stat().st_size if ok else 0,
        "transcodeCachePath": str(cached) if ok else None,
    }


def video_playback_profiles(path: Path) -> list[dict[str, object]]:
    return list_video_playback_profiles(path)
