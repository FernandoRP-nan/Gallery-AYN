"""Diagnóstico de vídeo para el visor integrado (ffprobe, caché, transcodificación)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .video_transcode import (
    ensure_transcoded_mp4,
    ensure_transcoded_webm,
    is_browser_playable,
    transcode_output_path,
    transcode_webm_output_path,
    _ffprobe_streams,
)
from .viewer_playback import (
    ensure_viewer_playback,
    needs_viewer_transcode,
    viewer_engine_label,
    viewer_playback_cache_status,
    viewer_prefers_webm,
)


def _tool_path(name: str) -> tuple[bool, str]:
    path = shutil.which(name) or ""
    return bool(path), path


def _ffprobe_error(path: Path) -> str | None:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(path)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode == 0:
            return None
        err = (result.stderr or result.stdout or "").strip()
        return err or f"ffprobe salió con código {result.returncode}"
    except FileNotFoundError:
        return "ffprobe no está instalado o no está en el PATH"
    except Exception as exc:
        return str(exc)


def probe_video_file(path: Path) -> dict:
    """Metadatos de códec y compatibilidad con WebView."""
    video, audio = _ffprobe_streams(path)
    cached = transcode_webm_output_path(path) if viewer_prefers_webm() else transcode_output_path(path)
    cached_ok = cached.is_file() and cached.stat().st_size > 512
    return {
        "videoCodec": (video or {}).get("codec_name"),
        "audioCodec": (audio or {}).get("codec_name"),
        "pixFmt": (video or {}).get("pix_fmt"),
        "width": (video or {}).get("width"),
        "height": (video or {}).get("height"),
        "durationSec": (video or {}).get("duration") or (audio or {}).get("duration"),
        "isBrowserPlayable": is_browser_playable(path),
        "needsViewerTranscode": needs_viewer_transcode(path),
        "viewerEngine": viewer_engine_label(),
        "viewerPrefersWebm": viewer_prefers_webm(),
        "ffprobeError": _ffprobe_error(path) if not video else None,
        "transcodeCached": cached_ok,
        "transcodeCachePath": str(cached) if cached_ok else None,
        "transcodeCacheBytes": cached.stat().st_size if cached_ok else 0,
        **viewer_playback_cache_status(path),
    }


def video_diagnostics(path: Path, *, test_transcode: bool = False) -> dict:
    """Informe completo para mostrar en la UI cuando falla la reproducción."""
    ffmpeg_ok, ffmpeg_path = _tool_path("ffmpeg")
    ffprobe_ok, ffprobe_path = _tool_path("ffprobe")
    out: dict = {
        "path": str(path),
        "exists": path.is_file(),
        "sizeBytes": path.stat().st_size if path.is_file() else 0,
        "extension": path.suffix.lower(),
        "ffmpegAvailable": ffmpeg_ok,
        "ffmpegPath": ffmpeg_path or None,
        "ffprobeAvailable": ffprobe_ok,
        "ffprobePath": ffprobe_path or None,
    }
    if not path.is_file():
        out["error"] = "El archivo no existe o no se pudo resolver la ruta."
        return out

    out.update(probe_video_file(path))
    out["needsTranscode"] = needs_viewer_transcode(path)

    if test_transcode and ffmpeg_ok:
        try:
            transcoded, mime = ensure_viewer_playback(path)
            out["transcodeTestOk"] = True
            out["transcodeTestBytes"] = transcoded.stat().st_size
            out["transcodeTestPath"] = str(transcoded)
            out["transcodeTestMime"] = mime
            out["transcodeError"] = None
        except Exception as exc:
            out["transcodeTestOk"] = False
            out["transcodeError"] = str(exc).strip() or "Error desconocido en ffmpeg"
    else:
        out["transcodeTestOk"] = None
        out["transcodeError"] = None

    return out
