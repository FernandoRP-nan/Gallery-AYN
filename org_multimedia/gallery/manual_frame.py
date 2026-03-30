"""Widget principal de la galería: estado inicial y composición por mixins."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from ..settings import load_app_settings

from .canvas_layout import GalleryCanvasLayoutMixin
from .destinations import GalleryDestinationsMixin
from .navigation import GalleryNavigationMixin
from .pager_config import GalleryPagerAndSettingsMixin
from .preview_grid import GalleryPreviewGridMixin
from .selection_bar import GallerySelectionBarMixin
from .thumb_interaction import GalleryThumbInteractionMixin
from .thumbnails import GalleryThumbnailsMixin
from .ui_build import GalleryUIBuildMixin


class GalleryManualFrame(
    GalleryUIBuildMixin,
    GalleryCanvasLayoutMixin,
    GalleryNavigationMixin,
    GalleryDestinationsMixin,
    GalleryPreviewGridMixin,
    GalleryPagerAndSettingsMixin,
    GalleryThumbnailsMixin,
    GalleryThumbInteractionMixin,
    GallerySelectionBarMixin,
    ttk.Frame,
):
    """Galeria con miniaturas, seleccion multiple y destinos por arrastre."""

    PREVIEW_MAX = (440, 480)

    def __init__(self, parent: ttk.Frame, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        self.root = parent.winfo_toplevel()
        self._thumb_size_tuple: tuple[int, int] = (160, 160)
        self._layout_cols = 5
        self._thumb_gen = 0
        self._resize_after_id: str | None = None
        self._last_canvas_width = 0
        self._gallery_window_id: int | None = None
        self._preview_gen = 0
        self._preview_photo_large: object | None = None
        self.toggle_click_var = tk.BooleanVar(value=True)
        self.selection_count_var = tk.StringVar(value="0 imagenes seleccionadas")
        self.settings = load_app_settings()
        _ts = float(self.settings.get("gallery_thumb_scale", 1.0))
        self.thumb_scale_var = tk.DoubleVar(value=max(0.75, min(2.25, _ts)))
        self._scale_sched: str | None = None
        self.gallery_folder: Path | None = None
        self.ordered_paths: list[Path] = []
        self.selected: set[Path] = set()
        self.anchor_index: int | None = None
        self.thumb_refs: list[object] = []
        self.path_to_frame: dict[Path, tk.Widget] = {}
        self._thumb_queue: queue.Queue = queue.Queue()
        self._thumb_worker: threading.Thread | None = None
        self._drag_start: tuple[int, int] | None = None
        self._drag_active = False
        self._photos: dict[str, object] = {}
        self._gallery_page = 0
        self._scroll_top_after_load = False
        self.folder_var = tk.StringVar(value=self.settings.get("gallery_last_folder", ""))
        self.path_display_var = tk.StringVar(value="")
        self._subfolder_paths: list[Path] = []
        self.status_gallery = tk.StringVar(
            value="Elige una carpeta y pulsa Cargar: solo se listan imagenes de esa carpeta (no subcarpetas)."
        )
        self.dest_widgets: list[tk.Widget] = []
        self._gallery_cell_gap = 6
        self._cell_outer_w = 160
        self._build_ui()
        self.pack(fill=tk.BOTH, expand=True)
        self.root.bind("<ButtonRelease-1>", self._on_global_release, add="+")
