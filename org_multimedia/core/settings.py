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
            "marker_tree": [],
            "gallery_last_folder": "",
            "gallery_recent_folders": [],
            "gallery_pinned_folders": [],
            "gallery_thumb_scale": 1.0,
            "gallery_show_thumb_filename": True,
            "gallery_thumbs_per_page": 48,
            "gallery_scroll_top_on_page_change": True,
            "gallery_compact_thumb_padding": False,
            "gallery_preview_sash_x": None,
            "dest_preview_thumb_scale": 1.0,
            "dest_preview_geometry": "",
            "web_preview_ratio": 0.4,
            "web_dest_panel_ratio": 0.26,
            "web_preview_visible": True,
            "web_pinned_folder_labels": {},
            "web_shortcuts": {
                "toggleMode": "Shift",
                "deleteAction": "R",
                "zoomPrev": "ArrowLeft,ArrowUp,A,W",
                "zoomNext": "ArrowRight,ArrowDown,D,S",
                "escape": "Escape",
            },
            "dest_preview_modal_w": 0.9,
            "dest_preview_modal_h": 0.8,
            "window_start_maximized": True,
            "gallery_include_subfolders": False,
            "gallery_sort_mode": "name,mtime,type",
            "gallery_group_by_folder": False,
            "gallery_timeline_view": False,
            "gallery_section_dominant_color": True,
            "web_prefer_qt_engine": True,
            "video_transcode_preset": "fast",
            "video_transcode_max_height": 1080,
            "video_transcode_max_width": 1920,
            "video_transcode_hw": "auto",
        }
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        if "destinations" not in data or not isinstance(data.get("destinations"), list):
            data["destinations"] = []
        if "marker_tree" not in data or not isinstance(data.get("marker_tree"), list):
            data["marker_tree"] = []
        if "gallery_last_folder" not in data:
            data["gallery_last_folder"] = ""
        if "gallery_recent_folders" not in data:
            data["gallery_recent_folders"] = []
        elif not isinstance(data["gallery_recent_folders"], list):
            data["gallery_recent_folders"] = []
        if "gallery_pinned_folders" not in data:
            data["gallery_pinned_folders"] = []
        elif not isinstance(data["gallery_pinned_folders"], list):
            data["gallery_pinned_folders"] = []
        # Primera migración: si no hay historial pero sí última carpeta, mostrar al menos esa
        if (
            isinstance(data.get("gallery_recent_folders"), list)
            and len(data["gallery_recent_folders"]) == 0
        ):
            gl = (data.get("gallery_last_folder") or "").strip()
            if gl:
                data["gallery_recent_folders"] = [gl]
        if "gallery_thumb_scale" not in data:
            data["gallery_thumb_scale"] = 1.0
        else:
            # Migrar valores viejos (0.5) a rango usable
            gs = float(data["gallery_thumb_scale"])
            data["gallery_thumb_scale"] = max(0.01, min(2.25, gs))
        if "gallery_show_thumb_filename" not in data:
            data["gallery_show_thumb_filename"] = True
        if "gallery_thumbs_per_page" not in data:
            data["gallery_thumbs_per_page"] = 48
        else:
            n = int(data["gallery_thumbs_per_page"])
            # 0 = sin límite; cualquier otro valor mínimo 12.
            data["gallery_thumbs_per_page"] = 0 if n <= 0 else max(12, n)
        if "gallery_scroll_top_on_page_change" not in data:
            data["gallery_scroll_top_on_page_change"] = True
        if "gallery_compact_thumb_padding" not in data:
            data["gallery_compact_thumb_padding"] = False
        if "gallery_preview_sash_x" not in data:
            data["gallery_preview_sash_x"] = None
        if "dest_preview_thumb_scale" not in data:
            data["dest_preview_thumb_scale"] = 1.0
        else:
            ds = float(data["dest_preview_thumb_scale"])
            data["dest_preview_thumb_scale"] = max(0.7, min(2.1, ds))
        if "dest_preview_geometry" not in data:
            data["dest_preview_geometry"] = ""
        if "web_preview_ratio" not in data:
            data["web_preview_ratio"] = 0.4
        else:
            vr = float(data["web_preview_ratio"])
            data["web_preview_ratio"] = max(0.14, min(0.68, vr))
        if "web_dest_panel_ratio" not in data:
            data["web_dest_panel_ratio"] = 0.26
        else:
            dr = float(data["web_dest_panel_ratio"])
            data["web_dest_panel_ratio"] = max(0.12, min(0.55, dr))
        if "web_preview_visible" not in data:
            data["web_preview_visible"] = True
        else:
            data["web_preview_visible"] = bool(data["web_preview_visible"])
        if "web_pinned_folder_labels" not in data or not isinstance(data.get("web_pinned_folder_labels"), dict):
            data["web_pinned_folder_labels"] = {}
        if "web_shortcuts" not in data or not isinstance(data.get("web_shortcuts"), dict):
            data["web_shortcuts"] = {
                "toggleMode": "Shift",
                "deleteAction": "R",
                "zoomPrev": "ArrowLeft,ArrowUp,A,W",
                "zoomNext": "ArrowRight,ArrowDown,D,S",
                "escape": "Escape",
            }
        if "dest_preview_modal_w" not in data:
            data["dest_preview_modal_w"] = 0.9
        if "dest_preview_modal_h" not in data:
            data["dest_preview_modal_h"] = 0.8
        if "window_start_maximized" not in data:
            data["window_start_maximized"] = True
        if "gallery_include_subfolders" not in data:
            data["gallery_include_subfolders"] = False
        else:
            data["gallery_include_subfolders"] = bool(data["gallery_include_subfolders"])
        if "gallery_sort_mode" not in data:
            data["gallery_sort_mode"] = "name,mtime,type"
        else:
            # Validar y limpiar la lista de ordenamiento compuesta
            sm = str(data["gallery_sort_mode"]).lower()
            parts = [p.strip() for p in sm.split(",") if p.strip() in ("name", "mtime", "type", "nombre", "fecha", "tipo")]
            if parts:
                data["gallery_sort_mode"] = ",".join(parts)
            else:
                data["gallery_sort_mode"] = "name,mtime,type"
        if "gallery_group_by_folder" not in data:
            data["gallery_group_by_folder"] = False
        else:
            data["gallery_group_by_folder"] = bool(data["gallery_group_by_folder"])
        if "gallery_timeline_view" not in data:
            data["gallery_timeline_view"] = False
        else:
            data["gallery_timeline_view"] = bool(data["gallery_timeline_view"])
        if "gallery_section_dominant_color" not in data:
            data["gallery_section_dominant_color"] = True
        else:
            data["gallery_section_dominant_color"] = bool(data["gallery_section_dominant_color"])
        if "web_prefer_qt_engine" not in data:
            data["web_prefer_qt_engine"] = True
        else:
            data["web_prefer_qt_engine"] = bool(data["web_prefer_qt_engine"])
        if "video_transcode_preset" not in data:
            data["video_transcode_preset"] = "fast"
        elif str(data["video_transcode_preset"]).lower() not in ("turbo", "fast", "quality"):
            data["video_transcode_preset"] = "fast"
        if "video_transcode_max_height" not in data:
            data["video_transcode_max_height"] = 1080
        else:
            try:
                h = int(data["video_transcode_max_height"])
                data["video_transcode_max_height"] = 0 if h <= 0 else max(480, min(2160, h))
            except (TypeError, ValueError):
                data["video_transcode_max_height"] = 1080
        if "video_transcode_max_width" not in data:
            data["video_transcode_max_width"] = 1920
        else:
            try:
                w = int(data["video_transcode_max_width"])
                data["video_transcode_max_width"] = 0 if w <= 0 else max(640, min(3840, w))
            except (TypeError, ValueError):
                data["video_transcode_max_width"] = 1920
        if "video_transcode_hw" not in data:
            data["video_transcode_hw"] = "auto"
        elif str(data["video_transcode_hw"]).lower() not in ("auto", "off"):
            data["video_transcode_hw"] = "auto"
        return data
    except (OSError, json.JSONDecodeError):
        return {
            "destinations": [],
            "marker_tree": [],
            "gallery_last_folder": "",
            "gallery_recent_folders": [],
            "gallery_pinned_folders": [],
            "gallery_thumb_scale": 1.0,
            "gallery_show_thumb_filename": True,
            "gallery_thumbs_per_page": 48,
            "gallery_scroll_top_on_page_change": True,
            "gallery_compact_thumb_padding": False,
            "gallery_preview_sash_x": None,
            "dest_preview_thumb_scale": 1.0,
            "dest_preview_geometry": "",
            "web_preview_ratio": 0.4,
            "web_dest_panel_ratio": 0.26,
            "web_preview_visible": True,
            "web_pinned_folder_labels": {},
            "web_shortcuts": {
                "toggleMode": "Shift",
                "deleteAction": "R",
                "zoomPrev": "ArrowLeft,ArrowUp,A,W",
                "zoomNext": "ArrowRight,ArrowDown,D,S",
                "escape": "Escape",
            },
            "dest_preview_modal_w": 0.9,
            "dest_preview_modal_h": 0.8,
            "window_start_maximized": True,
            "gallery_include_subfolders": False,
            "gallery_sort_mode": "name,mtime,type",
            "gallery_group_by_folder": False,
            "gallery_timeline_view": False,
            "gallery_section_dominant_color": True,
            "web_prefer_qt_engine": True,
            "video_transcode_preset": "fast",
            "video_transcode_max_height": 1080,
            "video_transcode_max_width": 1920,
            "video_transcode_hw": "auto",
        }


def save_app_settings(data: dict) -> None:
    _config_dir().mkdir(parents=True, exist_ok=True)
    with _settings_path().open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


