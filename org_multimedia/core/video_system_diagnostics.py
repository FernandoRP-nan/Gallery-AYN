"""Diagnóstico global del motor de vídeo y transcodificación (sin archivo concreto)."""

from __future__ import annotations

import os
import sys


def video_system_diagnostics() -> dict:
    """Informe rápido: no ejecuta ffmpeg -encoders ni escaneos pesados de caché."""
    from .video_tools import ffmpeg_available, ffprobe_available, resolve_ffmpeg, resolve_ffprobe
    from .video_transcode import transcode_cache_dir, transcode_queue_stats
    from .video_transcode_options import (
        get_cached_hw_encoder_snapshot,
        get_transcode_hw_mode,
        get_transcode_max_jobs,
        get_transcode_preset,
    )
    from .viewer_playback import (
        viewer_engine_label,
        viewer_prefers_webm,
        qt_has_proprietary_codecs,
        freeworld_install_hint,
        freeworld_rpm_installed,
        openh264_rpm_installed,
        pyqt6_system_install,
        qt_chromium_proprietary_flag_enabled,
    )

    ffmpeg = resolve_ffmpeg()
    ffprobe = resolve_ffprobe()
    queue = transcode_queue_stats()
    hw = get_cached_hw_encoder_snapshot()
    cache_dir = transcode_cache_dir()
    cache_files = 0
    if cache_dir.is_dir():
        try:
            with os.scandir(cache_dir) as it:
                for entry in it:
                    if entry.is_file():
                        cache_files += 1
                        if cache_files >= 500:
                            break
        except OSError:
            cache_files = 0

    return {
        "engine": viewer_engine_label(),
        "prefersWebm": viewer_prefers_webm(),
        "qtFreeworld": qt_has_proprietary_codecs(),
        "qtFreeworldRpm": freeworld_rpm_installed(),
        "qtOpenh264": openh264_rpm_installed(),
        "qtPyqt6System": pyqt6_system_install(),
        "qtChromiumProprietaryFlag": qt_chromium_proprietary_flag_enabled(),
        "freeworldInstallHint": freeworld_install_hint(),
        "pywebviewGui": os.environ.get("PYWEBVIEW_GUI", "qt" if sys.platform.startswith("linux") else "other"),
        "ffmpegAvailable": ffmpeg_available(),
        "ffmpegPath": ffmpeg,
        "ffprobeAvailable": ffprobe_available(),
        "ffprobePath": ffprobe,
        "hwEncodersAvailable": hw.get("hwEncodersAvailable", []),
        "webmHwEncodersAvailable": hw.get("webmHwEncodersAvailable", []),
        "hwEncoderSelected": hw.get("hwEncoderSelected"),
        "hwProbed": hw.get("hwProbed", False),
        "transcodeHwMode": get_transcode_hw_mode(),
        "transcodePreset": get_transcode_preset(),
        "transcodeMaxJobs": get_transcode_max_jobs(),
        "transcodeCacheDir": str(cache_dir),
        "transcodeCacheFiles": cache_files,
        "transcodeCacheBytes": -1,
        "activeTranscodeJobs": queue.get("active", 0),
        "transcodeQueued": queue.get("queued", 0),
        "transcodeRunning": queue.get("running", 0),
        "transcodeWarmQueued": queue.get("warmQueued", 0),
        "transcodeWorkers": queue.get("workers", 0),
    }
