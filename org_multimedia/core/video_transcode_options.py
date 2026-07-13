"""Opciones de transcodificación (ajustes de usuario + códec HW)."""

from __future__ import annotations

import subprocess

from .win_subprocess import run_hidden
import threading
from dataclasses import dataclass
from typing import Literal

_HW_ENCODER: str | None | False = False
_HW_ENCODERS_TEXT: str | False = False
_HW_LOCK = threading.Lock()

# Orden de preferencia al elegir códec HW (Linux: VAAPI entre QSV y AMF).
_HW_ENCODER_PRIORITY = ("h264_nvenc", "h264_qsv", "h264_vaapi", "h264_amf")
_WEBM_HW_ENCODER_PRIORITY = ("vp8_vaapi",)

PresetId = Literal["turbo", "fast", "quality"]
HwMode = Literal["auto", "off"]


@dataclass(frozen=True)
class TranscodeEncodeOptions:
    video_codec: str
    video_args: list[str]
    audio_args: list[str]
    max_width: int
    max_height: int


def _load_settings() -> dict:
    from .settings import load_app_settings

    return load_app_settings()


def get_transcode_preset() -> PresetId:
    raw = str(_load_settings().get("video_transcode_preset", "fast")).lower()
    if raw == "quality":
        return "quality"
    if raw == "turbo":
        return "turbo"
    return "fast"


def get_transcode_max_height() -> int:
    try:
        h = int(_load_settings().get("video_transcode_max_height", 1080))
    except (TypeError, ValueError):
        h = 1080
    if h <= 0:
        return 0
    return max(480, min(2160, h))


def get_transcode_max_width() -> int:
    try:
        w = int(_load_settings().get("video_transcode_max_width", 1920))
    except (TypeError, ValueError):
        w = 1920
    if w <= 0:
        return 0
    return max(640, min(3840, w))


def get_transcode_hw_mode() -> HwMode:
    raw = str(_load_settings().get("video_transcode_hw", "auto")).lower()
    return "off" if raw == "off" else "auto"


def get_transcode_max_jobs() -> int:
    try:
        n = int(_load_settings().get("video_transcode_max_jobs", 1))
    except (TypeError, ValueError):
        n = 1
    return max(1, min(3, n))


def reset_hw_encoder_cache() -> None:
    global _HW_ENCODER, _HW_ENCODERS_TEXT
    with _HW_LOCK:
        _HW_ENCODER = False
        _HW_ENCODERS_TEXT = False


def transcode_settings_fingerprint() -> str:
    """Huella de ajustes globales (para invalidación explícita)."""
    return (
        f"{get_transcode_preset()}:{get_transcode_max_height()}:{get_transcode_max_width()}:"
        f"{get_transcode_hw_mode()}:{get_transcode_max_jobs()}"
    )


def _effective_scale_limits(preset: PresetId, max_w: int, max_h: int) -> tuple[int, int]:
    """Turbo limita resolución para acelerar la primera reproducción."""
    if preset != "turbo":
        return max_w, max_h
    cap_w, cap_h = 1280, 720
    if max_w <= 0:
        eff_w = cap_w
    else:
        eff_w = min(max_w, cap_w)
    if max_h <= 0:
        eff_h = cap_h
    else:
        eff_h = min(max_h, cap_h)
    return eff_w, eff_h


def _ffmpeg_encoders_text(ffmpeg: str) -> str:
    global _HW_ENCODERS_TEXT
    with _HW_LOCK:
        if _HW_ENCODERS_TEXT is not False:
            return _HW_ENCODERS_TEXT
        text = ""
        try:
            out = run_hidden(
                [ffmpeg, "-hide_banner", "-encoders"],
                capture_output=True,
                text=True,
                timeout=12,
                check=False,
            )
            text = out.stdout or ""
        except Exception:
            text = ""
        _HW_ENCODERS_TEXT = text
        return text


def list_available_hw_encoders(ffmpeg: str) -> list[str]:
    """Códecs HW de H.264 detectados en ffmpeg -encoders."""
    text = _ffmpeg_encoders_text(ffmpeg)
    return [name for name in _HW_ENCODER_PRIORITY if name in text]


def list_available_webm_hw_encoders(ffmpeg: str) -> list[str]:
    text = _ffmpeg_encoders_text(ffmpeg)
    return [name for name in _WEBM_HW_ENCODER_PRIORITY if name in text]


def _detect_hw_encoder(ffmpeg: str) -> str | None:
    global _HW_ENCODER
    with _HW_LOCK:
        if _HW_ENCODER is not False:
            return _HW_ENCODER
        enc: str | None = None
        if get_transcode_hw_mode() != "off":
            for name in list_available_hw_encoders(ffmpeg):
                enc = name
                break
        _HW_ENCODER = enc
        return enc


def get_selected_hw_encoder(ffmpeg: str | None = None) -> str | None:
    if get_transcode_hw_mode() == "off":
        return None
    if not ffmpeg:
        from .video_tools import resolve_ffmpeg

        ffmpeg = resolve_ffmpeg()
    if not ffmpeg:
        return None
    return _detect_hw_encoder(ffmpeg)


def _vaapi_render_device() -> str:
    from pathlib import Path

    for cand in ("/dev/dri/renderD128", "/dev/dri/renderD129"):
        if Path(cand).exists():
            return cand
    return "/dev/dri/renderD128"


def build_vaapi_scale_filter(max_w: int, max_h: int) -> str:
    w = max_w if max_w > 0 else 99999
    h = max_h if max_h > 0 else 99999
    return f"scale_vaapi=w='min({w},iw)':h='min({h},ih)':force_original_aspect_ratio=decrease"


def build_vaapi_vf_chain(max_w: int, max_h: int) -> str:
    return f"format=nv12,hwupload,{build_vaapi_scale_filter(max_w, max_h)}"


def detect_webm_hw_encoder(ffmpeg: str) -> str | None:
    if get_transcode_hw_mode() == "off":
        return None
    for name in list_available_webm_hw_encoders(ffmpeg):
        return name
    return None


def build_scale_filter(max_w: int, max_h: int) -> str | None:
    if max_w <= 0 and max_h <= 0:
        return None
    w = max_w if max_w > 0 else 99999
    h = max_h if max_h > 0 else 99999
    return f"scale='min({w},iw)':'min({h},ih)':force_original_aspect_ratio=decrease"


def build_mp4_encode_options(ffmpeg: str, *, preset_override: PresetId | None = None) -> TranscodeEncodeOptions:
    preset: PresetId = preset_override if preset_override else get_transcode_preset()
    max_h = get_transcode_max_height()
    max_w = get_transcode_max_width()
    max_w, max_h = _effective_scale_limits(preset, max_w, max_h)
    hw = get_transcode_hw_mode()
    vf = build_scale_filter(max_w, max_h)

    if preset == "quality":
        x264_preset, crf = "veryfast", "23"
    elif preset == "turbo":
        x264_preset, crf = "ultrafast", "30"
    else:
        x264_preset, crf = "ultrafast", "28"

    vcodec = "libx264"
    video_args = ["-preset", x264_preset, "-crf", crf, "-pix_fmt", "yuv420p"]
    if hw == "auto":
        hw_enc = _detect_hw_encoder(ffmpeg)
        if hw_enc == "h264_nvenc":
            vcodec = "h264_nvenc"
            nv_preset = "p1" if preset in ("turbo", "fast") else "p4"
            video_args = ["-preset", nv_preset, "-cq", crf, "-pix_fmt", "yuv420p"]
        elif hw_enc == "h264_qsv":
            vcodec = "h264_qsv"
            video_args = ["-global_quality", crf, "-pix_fmt", "nv12"]
        elif hw_enc == "h264_amf":
            vcodec = "h264_amf"
            amf_quality = "speed" if preset in ("turbo", "fast") else "balanced"
            video_args = [
                "-quality",
                amf_quality,
                "-rc",
                "cqp",
                "-qp_i",
                crf,
                "-qp_p",
                crf,
            ]
        elif hw_enc == "h264_vaapi":
            device = _vaapi_render_device()
            vcodec = "h264_vaapi"
            vf_chain = build_vaapi_vf_chain(max_w, max_h)
            video_args = ["-vaapi_device", device, "-vf", vf_chain, "-qp", crf]
            vf = None

    if vf:
        video_args = ["-vf", vf, *video_args]

    audio_bitrate = "96k" if preset == "turbo" else "128k"
    return TranscodeEncodeOptions(
        video_codec=vcodec,
        video_args=video_args,
        audio_args=["-c:a", "aac", "-b:a", audio_bitrate],
        max_width=max_w,
        max_height=max_h,
    )


def build_webm_encode_options(ffmpeg: str) -> tuple[str, list[str]]:
    """Opciones de vídeo para transcodificación WebM (VP8 CPU o VAAPI)."""
    max_h = get_transcode_max_height()
    max_w = get_transcode_max_width()
    hw_enc = detect_webm_hw_encoder(ffmpeg)
    if hw_enc == "vp8_vaapi":
        device = _vaapi_render_device()
        vf_chain = build_vaapi_vf_chain(max_w, max_h)
        return "vp8_vaapi", ["-vaapi_device", device, "-vf", vf_chain, "-b:v", "1M"]
    vf = build_scale_filter(max_w, max_h)
    args: list[str] = []
    if vf:
        args.extend(["-vf", vf])
    args.extend(["-b:v", "1M", "-deadline", "realtime", "-cpu-used", "5"])
    return "libvpx", args
