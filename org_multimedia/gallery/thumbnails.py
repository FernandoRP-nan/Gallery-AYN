"""Carga de miniaturas por pagina y colocacion en la rejilla."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path

from ..gallery_images import make_thumbnail_photoimage
from ..pil_compat import HAS_PIL


class GalleryThumbnailsMixin:
    def _start_thumb_worker(self, *, scroll_top_after: bool = False) -> None:
        self._scroll_top_after_load = scroll_top_after
        self._thumb_gen += 1
        while True:
            try:
                self._thumb_queue.get_nowait()
            except queue.Empty:
                break
        # Al paginar, reemplaza la rejilla visible completa (no acumular miniaturas).
        for w in self.gallery_inner.winfo_children():
            w.destroy()
        self.path_to_frame.clear()
        self.path_to_checkvar.clear()
        self.path_to_checkwidget.clear()
        self._photos.clear()
        gen = self._thumb_gen

        total = len(self.ordered_paths)
        self._update_pager_ui()
        if total == 0:
            self.status_gallery.set("No hay imagenes en esta carpeta.")
            self._thumb_worker = None
            return

        self._clamp_gallery_page()
        self._update_pager_ui()
        start, end = self._gallery_page_slice()
        paths = self.ordered_paths[start:end]

        cw = self._effective_gallery_canvas_width(self.gallery_canvas.winfo_width())
        self._update_layout_metrics(cw)
        self._prepare_grid_columns()

        if not paths:
            self.status_gallery.set("Pagina vacia.")
            self._thumb_worker = None
            return

        def worker() -> None:
            for path in paths:
                if gen != self._thumb_gen:
                    return
                if not path.exists():
                    continue
                thumb_img = make_thumbnail_photoimage(path, self._thumb_size_tuple)
                self._thumb_queue.put(("thumb", gen, path, thumb_img))
            if gen != self._thumb_gen:
                return
            self._thumb_queue.put(("done", gen, len(paths), start, end, total))

        self._thumb_worker = threading.Thread(target=worker, daemon=True)
        self._thumb_worker.start()
        self._poll_thumb_queue()

    def _poll_thumb_queue(self) -> None:
        done_batch: tuple[int, int, int, int] | None = None
        try:
            while True:
                item = self._thumb_queue.get_nowait()
                if item[0] == "thumb":
                    _, gen, path, photo = item
                    if gen != self._thumb_gen:
                        continue
                    self._add_thumb_cell(path, photo)
                elif item[0] == "done":
                    _, gen, n_done, start, end, total = item
                    if gen != self._thumb_gen:
                        continue
                    done_batch = (n_done, start, end, total)
        except queue.Empty:
            pass
        if done_batch is not None:
            n_done, start, end, total = done_batch
            extra = "" if HAS_PIL else " Instala Pillow: pip install pillow."
            self.status_gallery.set(
                f"Pagina actual: miniaturas {start + 1}-{end} de {total} ({n_done} cargadas).{extra}"
            )
            if getattr(self, "_scroll_top_after_load", False):
                self._scroll_top_after_load = False
                self.gallery_canvas.yview_moveto(0)
        if self._thumb_worker and self._thumb_worker.is_alive():
            self.root.after(80, self._poll_thumb_queue)
        elif not self._thumb_queue.empty():
            self.root.after(80, self._poll_thumb_queue)
        else:
            self._thumb_worker = None

    def _add_thumb_cell(self, path: Path, photo: object | None) -> None:
        cols = max(2, self._layout_cols)
        row = len(self.path_to_frame) // cols
        col = len(self.path_to_frame) % cols
        gap = getattr(self, "_gallery_cell_gap", 6)
        gx = max(1, gap // 2)
        thumb = self._thumb_size_tuple[0]
        compact = bool(self.settings.get("gallery_compact_thumb_padding", False))
        py = 2 if compact else 4
        outer = tk.Frame(self.gallery_inner, bg="#24283b", padx=2, pady=py)
        outer.grid(row=row, column=col, padx=(gx, gx), pady=py, sticky="nsew")
        self.path_to_frame[path] = outer

        chk_var = tk.BooleanVar(value=path in self.selected)
        self.path_to_checkvar[path] = chk_var
        img_box = tk.Frame(outer, bg="#24283b", width=thumb, height=thumb, highlightthickness=0)
        img_box.pack(anchor=tk.CENTER, pady=(0, 2))
        img_box.pack_propagate(False)
        if photo is not None:
            key = str(path)
            self._photos[key] = photo
            lbl = tk.Label(img_box, image=photo, bg="#24283b")
            lbl.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        else:
            lbl = tk.Label(img_box, text="(sin vista previa)", bg="#24283b", fg="#565f89", font=("Sans", 8))
            lbl.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        chk = tk.Checkbutton(
            img_box,
            variable=chk_var,
            text="",
            width=2,
            bg="#24283b",
            fg="#a9b1d6",
            activebackground="#24283b",
            activeforeground="#c0caf5",
            selectcolor="#1a1b26",
            highlightthickness=0,
            command=lambda p=path: self._on_thumb_checkbox_toggle(p),
        )
        self.path_to_checkwidget[path] = chk
        self._update_thumb_check_visibility()

        cap: tk.Label | None = None
        if self._gallery_show_filename():
            name = path.name if len(path.name) < 28 else path.name[:12] + "..." + path.name[-10:]
            wrap = max(60, thumb - 4)
            cap = tk.Label(outer, text=name, bg="#24283b", fg="#a9b1d6", font=("Sans", 8), wraplength=wrap)
            cap.pack(fill=tk.X, pady=(2, 0))

        scroll_widgets: list[tk.Misc] = [outer, chk, img_box, lbl]
        click_widgets: list[tk.Misc] = [outer, img_box, lbl]
        if cap is not None:
            scroll_widgets.append(cap)
            click_widgets.append(cap)
        for wgt in scroll_widgets:
            self._bind_gallery_scroll_events(wgt)
        for wgt in click_widgets:
            wgt.bind("<Button-1>", lambda e, p=path: self._on_thumb_press(e, p))
            wgt.bind("<Shift-Button-1>", lambda e, p=path: self._on_thumb_press(e, p))
            wgt.bind("<Control-Button-1>", lambda e, p=path: self._on_thumb_press(e, p))
            wgt.bind("<B1-Motion>", self._on_thumb_motion)
        outer.bind("<ButtonRelease-1>", lambda e: self._on_thumb_release(e))
