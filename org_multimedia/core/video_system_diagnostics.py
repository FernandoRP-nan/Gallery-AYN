"""Diagnóstico global del motor de vídeo y transcodificación (sin archivo concreto)."""

from __future__ import annotations

import os
import sys


def video_system_diagnostics() -> dict:
    from .video_tools import ffmpeg_available, ffprobe_available, resolve_ffmpeg, resolve_ffprobe
    from .video_transcode import list_active_transcode_jobs, transcode_cache_dir, transcode_queue_stats
    from .video_transcode_options import (
        get_transcode_hw_mode,
        get_transcode_max_jobs,
        get_transcode_preset,
    )
    from .viewer_playback import qt_has_proprietary_codecs, viewer_engine_label, viewer_prefers_webm

    ffmpeg = resolve_ffmpeg()
    ffprobe = resolve_ffprobe()
    queue = transcode_queue_stats()
    cache_dir = transcode_cache_dir()
    cache_bytes = 0
    cache_files = 0
    if cache_dir.is_dir():
        for entry in cache_dir.iterdir():
            if not entry.is_file():
                continue
            cache_files += 1
            if cache_files <= 256:
                try:
                    cache_bytes += entry.stat().st_size
                except OSError:
                    pass

    hw_available: list[str] = []
    webm_hw_available: list[str] = []
    hw_selected: str | None = None
    if ffmpeg and queue.get("running", 0) <= 1 and queue.get("queued", 0) < 8:
        from .video_transcode_options import (
            get_selected_hw_encoder,
            list_available_hw_encoders,
            list_available_webm_hw_encoders,
        )

        hw_available = list_available_hw_encoders(ffmpeg)
        webm_hw_available = list_available_webm_hw_encoders(ffmpeg)
        hw_selected = get_selected_hw_encoder(ffmpeg)

    return {
        "engine": viewer_engine_label(),
        "prefersWebm": viewer_prefers_webm(),
        "qtFreeworld": qt_has_proprietary_codecs(),
        "pywebviewGui": os.environ.get("PYWEBVIEW_GUI", "qt" if sys.platform.startswith("linux") else "other"),
        "ffmpegAvailable": ffmpeg_available(),
        "ffmpegPath": ffmpeg,
        "ffprobeAvailable": ffprobe_available(),
        "ffprobePath": ffprobe,
        "hwEncodersAvailable": hw_available,
        "webmHwEncodersAvailable": webm_hw_available,
        "hwEncoderSelected": hw_selected,
        "transcodeHwMode": get_transcode_hw_mode(),
        "transcodePreset": get_transcode_preset(),
        "transcodeMaxJobs": get_transcode_max_jobs(),
        "transcodeCacheDir": str(cache_dir),
        "transcodeCacheFiles": cache_files,
        "transcodeCacheBytes": cache_bytes,
        "activeTranscodeJobs": len(list_active_transcode_jobs()),
        "transcodeQueued": queue.get("queued", 0),
        "transcodeRunning": queue.get("running", 0),
        "transcodeWarmQueued": queue.get("warmQueued", 0),
    }
