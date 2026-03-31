"""Canvas de rejilla: scroll, zoom, reflow y métricas de columnas."""

from __future__ import annotations

import queue
import tkinter as tk

from ..gallery_grid_layout import GalleryGridLayout
from ..settings import save_app_settings


class GalleryCanvasLayoutMixin:
    def _on_gallery_scroll_up(self, _event: tk.Event | None = None) -> None:
        self.gallery_canvas.yview_scroll(-3, "units")

    def _on_gallery_scroll_down(self, _event: tk.Event | None = None) -> None:
        self.gallery_canvas.yview_scroll(3, "units")

    def _on_mousewheel(self, event: tk.Event) -> None:
        # Windows / macOS: delta multiplo de 120. Linux X11: suele ser Button-4/5 en los hijos.
        d = int(getattr(event, "delta", 0) or 0)
        if d != 0:
            self.gallery_canvas.yview_scroll(int(-1 * (d / 120)), "units")
            return
        num = int(getattr(event, "num", 0) or 0)
        if num == 4:
            self._on_gallery_scroll_up()
        elif num == 5:
            self._on_gallery_scroll_down()

    def _bind_gallery_scroll_events(self, widget: tk.Misc) -> None:
        """La rueda actua sobre el widget bajo el cursor; el canvas solo la recibe en zonas vacias."""
        widget.bind("<MouseWheel>", self._on_mousewheel)
        widget.bind("<Button-4>", self._on_gallery_scroll_up)
        widget.bind("<Button-5>", self._on_gallery_scroll_down)

    def _effective_gallery_canvas_width(self, w: int | float) -> int:
        return GalleryGridLayout.effective_canvas_width(w, int(self._last_canvas_width or 0))

    def _debounced_gallery_canvas_reflow(self) -> None:
        self._resize_after_id = None
        w = self._effective_gallery_canvas_width(self.gallery_canvas.winfo_width())
        self._apply_gallery_reflow(w, force=False)

    def _on_gallery_canvas_configure(self, event: tk.Event) -> None:
        w = int(event.width)
        eff = self._effective_gallery_canvas_width(w)
        if self._gallery_window_id is not None and eff > 2:
            self.gallery_canvas.itemconfigure(self._gallery_window_id, width=max(1, eff - 3))
        if eff < 80:
            return
        if self._resize_after_id is not None:
            try:
                self.root.after_cancel(self._resize_after_id)
            except tk.TclError:
                pass
            self._resize_after_id = None
        self._resize_after_id = self.root.after(180, self._debounced_gallery_canvas_reflow)

    def _compute_layout_metrics(self, canvas_width: int) -> None:
        m = GalleryGridLayout.compute_metrics(canvas_width, float(self.thumb_scale_var.get()))
        self._layout_cols = m.layout_cols
        self._cell_outer_w = m.cell_outer_w
        self._thumb_size_tuple = m.thumb_size_tuple
        self._gallery_cell_gap = m.gallery_cell_gap

    def _update_layout_metrics(self, canvas_width: int | None = None) -> None:
        if canvas_width is None or canvas_width < 80:
            canvas_width = self.gallery_canvas.winfo_width()
        canvas_width = self._effective_gallery_canvas_width(canvas_width)
        if canvas_width < 80:
            canvas_width = max(400, self._last_canvas_width or 720)
        self._compute_layout_metrics(canvas_width)

    def _prepare_grid_columns(self) -> None:
        n = max(2, self._layout_cols)
        for i in range(24):
            self.gallery_inner.columnconfigure(i, weight=0, minsize=0)
        # minsize = ancho de celda calculado para que el grid reclame todo el ancho del canvas (no colapsar).
        cw = max(48, int(self._cell_outer_w))
        for i in range(n):
            self.gallery_inner.columnconfigure(i, weight=1, uniform="gal_col", minsize=cw)

    def _on_thumb_scale_slider(self, value: str | float) -> None:
        try:
            v = float(value)
        except (TypeError, ValueError):
            try:
                v = float(self.thumb_scale_var.get())
            except (TypeError, ValueError, tk.TclError):
                return
        v = max(0.75, min(2.25, v))
        self.thumb_scale_var.set(v)
        self.thumb_scale_label.configure(text=f"{int(round(v * 100))}%")
        self.settings["gallery_thumb_scale"] = v
        save_app_settings(self.settings)
        if self._scale_sched is not None:
            try:
                self.root.after_cancel(self._scale_sched)
            except tk.TclError:
                pass
        self._scale_sched = self.root.after(160, self._reflow_after_scale_change)

    def _reflow_after_scale_change(self) -> None:
        self._scale_sched = None
        w = self._effective_gallery_canvas_width(self.gallery_canvas.winfo_width())
        self._apply_gallery_reflow(w, force=True)

    def _apply_gallery_reflow(self, canvas_width: int, force: bool = False) -> None:
        self._resize_after_id = None
        canvas_width = self._effective_gallery_canvas_width(canvas_width)
        if canvas_width < 80:
            return
        if self._gallery_window_id is not None:
            self.gallery_canvas.itemconfigure(self._gallery_window_id, width=max(1, canvas_width - 3))
        self._compute_layout_metrics(canvas_width)
        self._last_canvas_width = canvas_width
        snap = (
            self._layout_cols,
            self._cell_outer_w,
            round(float(self.thumb_scale_var.get()), 2),
        )
        if (
            not force
            and snap == getattr(self, "_layout_snap", None)
            and abs(canvas_width - getattr(self, "_layout_snap_w", -999)) < 16
        ):
            return
        self._layout_snap = snap
        self._layout_snap_w = canvas_width
        if not self.path_to_frame:
            return
        if not self.ordered_paths:
            return
        while True:
            try:
                self._thumb_queue.get_nowait()
            except queue.Empty:
                break
        for w in self.gallery_inner.winfo_children():
            w.destroy()
        self.path_to_frame.clear()
        if hasattr(self, "path_to_checkvar"):
            self.path_to_checkvar.clear()
        if hasattr(self, "path_to_checkwidget"):
            self.path_to_checkwidget.clear()
        self._photos.clear()
        self.selected.clear()
        self.anchor_index = None
        self._clamp_gallery_page()
        self._update_selection_label()
        self._start_thumb_worker(scroll_top_after=False)
