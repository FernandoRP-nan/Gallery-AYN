"""Modos de reproducción por vídeo (auto, directo, remux, presets)."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from .video_transcode_options import get_transcode_hw_mode, get_transcode_max_height, get_transcode_max_width, get_transcode_preset

PlaybackMode = Literal["auto", "direct", "remux", "turbo", "fast", "quality"]
_ENCODE_MODES = frozenset({"turbo", "fast", "quality"})


def normalize_playback_mode(raw: str | None) -> PlaybackMode:
    m = str(raw or "auto").lower().strip()
    if m in ("direct", "remux", "turbo", "fast", "quality"):
        return m  # type: ignore[return-value]
    return "auto"


def transcode_cache_suffix(playback_mode: PlaybackMode, source: Path | None = None) -> str:
    """Sufijo estable para la clave de caché (incluye ajustes globales)."""
    from .video_transcode import _ffprobe_streams, mp4_playback_mode

    hw = get_transcode_hw_mode()
    max_h = get_transcode_max_height()
    max_w = get_transcode_max_width()
    mode = normalize_playback_mode(playback_mode)

    if mode == "remux":
        return f"remux-{max_h}-{max_w}"

    if mode in _ENCODE_MODES:
        return f"h264-{mode}-{max_h}-{max_w}-{hw}"

    # auto: remux rápido si aplica; si no, preset global
    if source is not None:
        video, audio = _ffprobe_streams(source.resolve())
        plan = mp4_playback_mode(video, audio)
        if plan in ("copy_all", "copy_video_aac"):
            return f"remux-{max_h}-{max_w}"

    preset = get_transcode_preset()
    return f"h264-{preset}-{max_h}-{max_w}-{hw}"


def resolve_transcode_plan(source: Path, playback_mode: PlaybackMode) -> tuple[str, str | None]:
    """Devuelve (plan ffmpeg, preset_override) — plan: copy_all | copy_video_aac | encode."""
    from .video_transcode import _ffprobe_streams, mp4_playback_mode

    mode = normalize_playback_mode(playback_mode)
    video, audio = _ffprobe_streams(source.resolve())

    if mode == "remux":
        plan = mp4_playback_mode(video, audio)
        if plan in ("copy_all", "copy_video_aac"):
            return plan, None
        return "encode", "fast"

    if mode in _ENCODE_MODES:
        return "encode", mode

    plan = mp4_playback_mode(video, audio)
    if plan in ("copy_all", "copy_video_aac"):
        return plan, None
    return "encode", None


def list_video_playback_profiles(path: Path) -> list[dict[str, object]]:
    """Perfiles disponibles para un vídeo concreto."""
    from .video_transcode import _ffprobe_streams, mp4_playback_mode
    from .viewer_playback import needs_viewer_transcode, viewer_playback_strategy, viewer_prefers_webm

    resolved = path.resolve()
    strategy = viewer_playback_strategy(resolved)
    needs = needs_viewer_transcode(resolved)
    video, audio = _ffprobe_streams(resolved)
    can_remux = mp4_playback_mode(video, audio) in ("copy_all", "copy_video_aac")

    profiles: list[dict[str, object]] = [
        {
            "id": "auto",
            "available": True,
            "recommended": True,
            "strategy": strategy,
            "needsTranscode": needs,
        }
    ]

    if not viewer_prefers_webm():
        profiles.append(
            {
                "id": "direct",
                "available": not needs,
                "recommended": not needs,
                "strategy": "direct",
                "needsTranscode": False,
            }
        )
        profiles.append(
            {
                "id": "remux",
                "available": can_remux,
                "recommended": strategy == "remux",
                "strategy": "remux",
                "needsTranscode": True,
            }
        )

    for preset in ("turbo", "fast", "quality"):
        profiles.append(
            {
                "id": preset,
                "available": True,
                "recommended": False,
                "strategy": "encode",
                "needsTranscode": True,
            }
        )

    return profiles
