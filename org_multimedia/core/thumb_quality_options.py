"""Presets de calidad/resolución para miniaturas LQ y HQ."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ThumbQualityPreset = Literal["balanced", "sharp", "hidpi", "performance"]


@dataclass(frozen=True)
class ThumbEncodeParams:
    size_px: int
    jpeg_quality: int


@dataclass(frozen=True)
class _PresetSpec:
    lq_scale: float
    lq_quality: int
    hq_scale: float
    hq_quality: int


_PRESETS: dict[ThumbQualityPreset, _PresetSpec] = {
    "balanced": _PresetSpec(lq_scale=0.55, lq_quality=40, hq_scale=1.35, hq_quality=96),
    "sharp": _PresetSpec(lq_scale=0.78, lq_quality=58, hq_scale=1.45, hq_quality=94),
    "hidpi": _PresetSpec(lq_scale=1.0, lq_quality=72, hq_scale=1.65, hq_quality=92),
    "performance": _PresetSpec(lq_scale=0.45, lq_quality=32, hq_scale=1.2, hq_quality=88),
}


def _load_settings() -> dict:
    from .settings import load_app_settings

    return load_app_settings()


def get_thumb_quality_preset() -> ThumbQualityPreset:
    raw = str(_load_settings().get("gallery_thumb_quality_preset", "balanced")).lower()
    if raw in _PRESETS:
        return raw  # type: ignore[return-value]
    return "balanced"


def thumb_encode_params(thumb_px: int, profile: str) -> ThumbEncodeParams:
    """Parámetros JPEG según preset y perfil lq/hq."""
    spec = _PRESETS[get_thumb_quality_preset()]
    px = max(48, int(thumb_px))
    if str(profile).lower() == "lq":
        size = max(48, int(round(px * spec.lq_scale)))
        return ThumbEncodeParams(size_px=size, jpeg_quality=spec.lq_quality)
    size = max(48, int(round(px * spec.hq_scale)))
    return ThumbEncodeParams(size_px=size, jpeg_quality=spec.hq_quality)
