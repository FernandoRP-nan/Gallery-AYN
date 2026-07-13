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
            "gallery_thumb_quality_preset": "balanced",
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
            "gallery_show_other_files": False,
            "gallery_warm_index_on_startup": False,
            "gallery_warm_include_children": True,
            "gallery_warm_max_depth": 2,
            "gallery_sort_mode": "name,mtime,type",
            "gallery_group_by_folder": False,
            "gallery_group_by_alpha": False,
            "gallery_timeline_view": False,
            "gallery_dynamic_name_regex": False,
            "gallery_masonry_view": False,
            "gallery_masonry_tight_spacing": False,
            "gallery_section_dominant_color": True,
            "web_prefer_qt_engine": True,
            "video_transcode_preset": "fast",
            "video_transcode_max_height": 1080,
            "video_transcode_max_width": 1920,
            "video_transcode_hw": "auto",
            "preview_video_autoplay": True,
            "preview_video_autoplay_edit": False,
            "mess_folder_path": "",
            "mess_similarity_min": 0.82,
            "mess_pinterest_masonry": False,
            "mess_pinterest_more_like": False,
            "mess_pinterest_drag_groups": False,
            "mess_suggestions_enabled": False,
            "mess_scan_max_files": 400,
            "gallery_unlimited_batch_size": 48,
            "gallery_window_overscan_before": 96,
            "gallery_window_overscan_after": 160,
            "gallery_jump_core_overscan_before": 32,
            "gallery_jump_core_overscan_after": 48,
            "gallery_sliding_window_enabled": True,
            "gallery_sliding_window_max_items": 896,
            "gallery_thumb_build_workers": 8,
            "gallery_thumb_hq_workers": 4,
            "gallery_thumb_hq_visible_sequential": 16,
            "gallery_compact_indices_after_move": True,
            "web_debug_log_enabled": False,
            "web_debug_log_filters": {
                "scroll": True,
                "scroll_drag": True,
                "rail_jump": True,
                "prefetch": True,
                "load_lq": True,
                "load_hq": True,
                "user": True,
                "window": True,
                "selection": True,
                "selection_reset": True,
                "sort": True,
            },
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
        if "gallery_thumb_quality_preset" not in data:
            data["gallery_thumb_quality_preset"] = "balanced"
        elif str(data["gallery_thumb_quality_preset"]).lower() not in (
            "balanced",
            "sharp",
            "hidpi",
            "performance",
        ):
            data["gallery_thumb_quality_preset"] = "balanced"
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
        if "gallery_show_other_files" not in data:
            data["gallery_show_other_files"] = False
        else:
            data["gallery_show_other_files"] = bool(data["gallery_show_other_files"])
        if "gallery_warm_index_on_startup" not in data:
            data["gallery_warm_index_on_startup"] = False
        else:
            data["gallery_warm_index_on_startup"] = bool(data["gallery_warm_index_on_startup"])
        if "gallery_warm_include_children" not in data:
            data["gallery_warm_include_children"] = True
        else:
            data["gallery_warm_include_children"] = bool(data["gallery_warm_include_children"])
        if "gallery_warm_max_depth" not in data:
            data["gallery_warm_max_depth"] = 2
        else:
            try:
                data["gallery_warm_max_depth"] = max(0, min(6, int(data["gallery_warm_max_depth"])))
            except (TypeError, ValueError):
                data["gallery_warm_max_depth"] = 2
        if "gallery_sort_mode" not in data:
            data["gallery_sort_mode"] = "name,mtime,type"
        else:
            # Validar y limpiar la lista de ordenamiento compuesta (key:dir)
            _sort_aliases = {
                "name": "name",
                "nombre": "name",
                "name_lex": "name_lex",
                "normal": "name_lex",
                "lexicografico": "name_lex",
                "lexicographical": "name_lex",
                "random": "random",
                "aleatorio": "random",
                "azar": "random",
                "name_base": "name_base",
                "base": "name_base",
                "num_base": "name_base",
                "principal": "name_base",
                "name_suffix": "name_suffix",
                "suffix": "name_suffix",
                "num_suffix": "name_suffix",
                "secundario": "name_suffix",
                "parentesis": "name_suffix",
                "mtime": "mtime",
                "date": "mtime",
                "fecha": "mtime",
                "ctime": "ctime",
                "creacion": "ctime",
                "creation": "ctime",
                "created": "ctime",
                "exif": "exif",
                "exifdate": "exif",
                "photo": "exif",
                "foto": "exif",
                "captura": "exif",
                "exif_month": "exif_month",
                "month_exif": "exif_month",
                "mes_exif": "exif_month",
                "mes": "exif_month",
                "type": "type",
                "tipo": "type",
            }
            sm = str(data["gallery_sort_mode"]).lower()
            normalized: list[str] = []
            for raw in sm.split(","):
                part = raw.strip()
                if not part:
                    continue
                key_raw, _, dir_raw = part.partition(":")
                canon = _sort_aliases.get(key_raw)
                if not canon:
                    continue
                direction = dir_raw if dir_raw in ("asc", "desc") else (
                    "desc" if canon in ("mtime", "ctime", "exif", "exif_month") else "asc"
                )
                normalized.append(f"{canon}:{direction}")
            if normalized:
                data["gallery_sort_mode"] = ",".join(normalized)
            else:
                data["gallery_sort_mode"] = "name:asc,mtime:desc,type:asc"
        if "gallery_group_by_folder" not in data:
            data["gallery_group_by_folder"] = False
        else:
            data["gallery_group_by_folder"] = bool(data["gallery_group_by_folder"])
        if "gallery_group_by_alpha" not in data:
            data["gallery_group_by_alpha"] = False
        else:
            data["gallery_group_by_alpha"] = bool(data["gallery_group_by_alpha"])
        if "gallery_timeline_view" not in data:
            data["gallery_timeline_view"] = False
        else:
            data["gallery_timeline_view"] = bool(data["gallery_timeline_view"])
        if "gallery_dynamic_name_regex" not in data:
            data["gallery_dynamic_name_regex"] = False
        else:
            data["gallery_dynamic_name_regex"] = bool(data["gallery_dynamic_name_regex"])
        if "gallery_masonry_view" not in data:
            data["gallery_masonry_view"] = False
        else:
            data["gallery_masonry_view"] = bool(data["gallery_masonry_view"])
        if "gallery_masonry_tight_spacing" not in data:
            data["gallery_masonry_tight_spacing"] = False
        else:
            data["gallery_masonry_tight_spacing"] = bool(data["gallery_masonry_tight_spacing"])
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
        if "preview_video_autoplay" not in data:
            data["preview_video_autoplay"] = True
        else:
            data["preview_video_autoplay"] = bool(data["preview_video_autoplay"])
        if "preview_video_autoplay_edit" not in data:
            data["preview_video_autoplay_edit"] = False
        else:
            data["preview_video_autoplay_edit"] = bool(data["preview_video_autoplay_edit"])
        if "mess_folder_path" not in data:
            data["mess_folder_path"] = ""
        else:
            data["mess_folder_path"] = str(data.get("mess_folder_path") or "").strip()
        if "mess_similarity_min" not in data:
            data["mess_similarity_min"] = 0.82
        else:
            try:
                sim = float(data["mess_similarity_min"])
                data["mess_similarity_min"] = max(0.5, min(0.98, sim))
            except (TypeError, ValueError):
                data["mess_similarity_min"] = 0.82
        if "mess_pinterest_masonry" not in data:
            data["mess_pinterest_masonry"] = False
        else:
            data["mess_pinterest_masonry"] = bool(data["mess_pinterest_masonry"])
        if "mess_pinterest_more_like" not in data:
            data["mess_pinterest_more_like"] = False
        else:
            data["mess_pinterest_more_like"] = bool(data["mess_pinterest_more_like"])
        if "mess_pinterest_drag_groups" not in data:
            data["mess_pinterest_drag_groups"] = False
        else:
            data["mess_pinterest_drag_groups"] = bool(data["mess_pinterest_drag_groups"])
        if "mess_scan_max_files" not in data:
            data["mess_scan_max_files"] = 400
        else:
            try:
                mf = int(data["mess_scan_max_files"])
                data["mess_scan_max_files"] = max(50, min(2000, mf))
            except (TypeError, ValueError):
                data["mess_scan_max_files"] = 400
        if "mess_suggestions_enabled" not in data:
            data["mess_suggestions_enabled"] = False
        else:
            data["mess_suggestions_enabled"] = bool(data["mess_suggestions_enabled"])
        if "gallery_unlimited_batch_size" not in data:
            data["gallery_unlimited_batch_size"] = 48
        else:
            try:
                data["gallery_unlimited_batch_size"] = max(
                    24, min(256, int(data["gallery_unlimited_batch_size"]))
                )
            except (TypeError, ValueError):
                data["gallery_unlimited_batch_size"] = 48
        for key, default, lo, hi in (
            ("gallery_window_overscan_before", 96, 32, 512),
            ("gallery_window_overscan_after", 160, 32, 512),
            ("gallery_jump_core_overscan_before", 32, 16, 128),
            ("gallery_jump_core_overscan_after", 48, 24, 160),
            ("gallery_sliding_window_max_items", 896, 320, 4096),
            ("gallery_thumb_build_workers", 8, 2, 16),
            ("gallery_thumb_hq_workers", 4, 1, 16),
            ("gallery_thumb_hq_visible_sequential", 16, 4, 32),
        ):
            if key not in data:
                data[key] = default
            else:
                try:
                    data[key] = max(lo, min(hi, int(data[key])))
                except (TypeError, ValueError):
                    data[key] = default
        # Migrar núcleo de salto antiguo (48+72) al preset agresivo (32+48).
        if (
            int(data.get("gallery_jump_core_overscan_before", 32)) == 48
            and int(data.get("gallery_jump_core_overscan_after", 48)) == 72
        ):
            data["gallery_jump_core_overscan_before"] = 32
            data["gallery_jump_core_overscan_after"] = 48
        if "gallery_sliding_window_enabled" not in data:
            data["gallery_sliding_window_enabled"] = True
        else:
            data["gallery_sliding_window_enabled"] = bool(data["gallery_sliding_window_enabled"])
        if "gallery_sliding_window_max_items" not in data:
            data["gallery_sliding_window_max_items"] = 896
        else:
            try:
                data["gallery_sliding_window_max_items"] = max(
                    320, min(4096, int(data["gallery_sliding_window_max_items"]))
                )
            except (TypeError, ValueError):
                data["gallery_sliding_window_max_items"] = 896
        if "web_debug_log_enabled" not in data:
            data["web_debug_log_enabled"] = False
        else:
            data["web_debug_log_enabled"] = bool(data["web_debug_log_enabled"])
        if "gallery_compact_indices_after_move" not in data:
            data["gallery_compact_indices_after_move"] = True
        else:
            data["gallery_compact_indices_after_move"] = bool(data["gallery_compact_indices_after_move"])
        _default_debug_filters = {
            "scroll": True,
            "scroll_drag": True,
            "rail_jump": True,
            "prefetch": True,
            "load_lq": True,
            "load_hq": True,
            "user": True,
            "window": True,
            "selection": True,
            "selection_reset": True,
            "sort": True,
        }
        raw_filters = data.get("web_debug_log_filters")
        if not isinstance(raw_filters, dict):
            data["web_debug_log_filters"] = dict(_default_debug_filters)
        else:
            merged = dict(_default_debug_filters)
            for key in _default_debug_filters:
                if key in raw_filters:
                    merged[key] = bool(raw_filters[key])
            data["web_debug_log_filters"] = merged
        return data
    except (OSError, json.JSONDecodeError):
        return {
            "destinations": [],
            "marker_tree": [],
            "gallery_last_folder": "",
            "gallery_recent_folders": [],
            "gallery_pinned_folders": [],
            "gallery_thumb_scale": 1.0,
            "gallery_thumb_quality_preset": "balanced",
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
            "gallery_show_other_files": False,
            "gallery_warm_index_on_startup": False,
            "gallery_warm_include_children": True,
            "gallery_warm_max_depth": 2,
            "gallery_sort_mode": "name,mtime,type",
            "gallery_group_by_folder": False,
            "gallery_group_by_alpha": False,
            "gallery_timeline_view": False,
            "gallery_dynamic_name_regex": False,
            "gallery_masonry_view": False,
            "gallery_masonry_tight_spacing": False,
            "gallery_section_dominant_color": True,
            "web_prefer_qt_engine": True,
            "video_transcode_preset": "fast",
            "video_transcode_max_height": 1080,
            "video_transcode_max_width": 1920,
            "video_transcode_hw": "auto",
            "preview_video_autoplay": True,
            "preview_video_autoplay_edit": False,
            "mess_folder_path": "",
            "mess_similarity_min": 0.82,
            "mess_pinterest_masonry": False,
            "mess_pinterest_more_like": False,
            "mess_pinterest_drag_groups": False,
            "mess_suggestions_enabled": False,
            "mess_scan_max_files": 400,
            "gallery_unlimited_batch_size": 48,
            "gallery_window_overscan_before": 96,
            "gallery_window_overscan_after": 160,
            "gallery_jump_core_overscan_before": 32,
            "gallery_jump_core_overscan_after": 48,
            "gallery_sliding_window_enabled": True,
            "gallery_sliding_window_max_items": 896,
            "gallery_thumb_build_workers": 8,
            "gallery_thumb_hq_workers": 4,
            "gallery_thumb_hq_visible_sequential": 16,
            "gallery_compact_indices_after_move": True,
            "web_debug_log_enabled": False,
            "web_debug_log_filters": {
                "scroll": True,
                "scroll_drag": True,
                "rail_jump": True,
                "prefetch": True,
                "load_lq": True,
                "load_hq": True,
                "user": True,
                "window": True,
                "selection": True,
                "selection_reset": True,
                "sort": True,
            },
        }


def save_app_settings(data: dict) -> None:
    _config_dir().mkdir(parents=True, exist_ok=True)
    with _settings_path().open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


