"""Persistencia de ajustes en ~/.config/organizador_multimedia/settings.json."""

from __future__ import annotations

import json
import os
from pathlib import Path


def _config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return Path(base) / "organizador_multimedia"


def _settings_path() -> Path:
    return _config_dir() / "settings.json"


def load_app_settings() -> dict:
    path = _settings_path()
    if not path.exists():
        return {
            "destinations": [],
            "gallery_last_folder": "",
            "gallery_thumb_scale": 1.0,
            "gallery_show_thumb_filename": True,
            "gallery_thumbs_per_page": 120,
            "gallery_scroll_top_on_page_change": True,
            "gallery_compact_thumb_padding": False,
        }
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        if "destinations" not in data:
            data["destinations"] = []
        if "gallery_last_folder" not in data:
            data["gallery_last_folder"] = ""
        if "gallery_thumb_scale" not in data:
            data["gallery_thumb_scale"] = 1.0
        else:
            # Migrar valores viejos (0.5) a rango usable
            gs = float(data["gallery_thumb_scale"])
            data["gallery_thumb_scale"] = max(0.75, min(2.25, gs))
        if "gallery_show_thumb_filename" not in data:
            data["gallery_show_thumb_filename"] = True
        if "gallery_thumbs_per_page" not in data:
            data["gallery_thumbs_per_page"] = 120
        else:
            data["gallery_thumbs_per_page"] = int(data["gallery_thumbs_per_page"])
        if "gallery_scroll_top_on_page_change" not in data:
            data["gallery_scroll_top_on_page_change"] = True
        if "gallery_compact_thumb_padding" not in data:
            data["gallery_compact_thumb_padding"] = False
        return data
    except (OSError, json.JSONDecodeError):
        return {
            "destinations": [],
            "gallery_last_folder": "",
            "gallery_thumb_scale": 1.0,
            "gallery_show_thumb_filename": True,
            "gallery_thumbs_per_page": 120,
            "gallery_scroll_top_on_page_change": True,
            "gallery_compact_thumb_padding": False,
        }


def save_app_settings(data: dict) -> None:
    _config_dir().mkdir(parents=True, exist_ok=True)
    with _settings_path().open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


