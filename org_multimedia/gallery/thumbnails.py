"""Carga por lotes de miniaturas y colocación en la rejilla."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path

from ..gallery_images import make_thumbnail_photoimage
from ..pil_compat import HAS_PIL


class GalleryThumbnailsMixin:
    def _load_more_thumbs(self) -> None:
        if not self.ordered_paths:
            return
        self._start_thumb_worker(reset_offset=False)

    def _start_thumb_worker(self, reset_offset: bool = False) -> None:
        if self._thumb_worker and self._thumb_worker.is_alive() and not reset_offset:
            return
        if reset_offset:
            self._thumb_gen += 1
            while True:
                try:
                    self._thumb_queue.get_nowait()
                except queue.Empty:
                    break
        gen = self._thumb_gen
        if reset_offset:
            self._thumb_offset = 0
        cw = self._effective_gallery_canvas_width(self.gallery_canvas.winfo_width())
        self._update_layout_metrics(cw)
        self._prepare_grid_columns()
        total = len(self.ordered_paths)
        if self._thumb_offset >= total:
            self.status_gallery.set("No hay mas miniaturas para cargar.")
            self.more_thumbs_btn.config(state=tk.DISABLED)
            return
        end = min(self._thumb_offset + self.BATCH_THUMBS, total)
        paths = self.ordered_paths[self._thumb_offset : end]
        self._thumb_offset = end

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
            self._thumb_queue.put(("done", gen, len(paths), end, total))

        self._thumb_worker = threading.Thread(target=worker, daemon=True)
        self._thumb_worker.start()
        self.more_thumbs_btn.config(state=tk.DISABLED)
        self._poll_thumb_queue()

    def _poll_thumb_queue(self) -> None:
        done_batch: tuple[int, int, int] | None = None
        try:
            while True:
                item = self._thumb_queue.get_nowait()
                if item[0] == "thumb":
                    _, gen, path, photo = item
                    if gen != self._thumb_gen:
                        continue
                    self._add_thumb_cell(path, photo)
                elif item[0] == "done":
                    _, gen, n, offset_end, total = item
                    if gen != self._thumb_gen:
                        continue
                    done_batch = (n, offset_end, total)
        except queue.Empty:
            pass
        if done_batch is not None:
            _n, offset_end, total = done_batch
            extra = "" if HAS_PIL else " Instala Pillow: pip install pillow."
            remaining = max(0, total - offset_end)
            self.status_gallery.set(
                f"Miniaturas mostradas hasta {offset_end} de {total}.{extra}"
                + (f" Quedan {remaining}; pulsa 'Mas miniaturas'." if remaining > 0 else "")
            )
            if remaining > 0:
                self.more_thumbs_btn.config(state=tk.NORMAL)
            else:
                self.more_thumbs_btn.config(state=tk.DISABLED)
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
        outer = tk.Frame(self.gallery_inner, bg="#24283b", padx=2, pady=4)
        outer.grid(row=row, column=col, padx=(gx, gx), pady=4, sticky="nsew")
        self.path_to_frame[path] = outer
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
        name = path.name if len(path.name) < 28 else path.name[:12] + "..." + path.name[-10:]
        wrap = max(60, thumb - 4)
        cap = tk.Label(outer, text=name, bg="#24283b", fg="#a9b1d6", font=("Sans", 8), wraplength=wrap)
        cap.pack(fill=tk.X, pady=(2, 0))
        for w in (outer, img_box, lbl, cap):
            w.bind("<Button-1>", lambda e, p=path: self._on_thumb_press(e, p))
            w.bind("<Shift-Button-1>", lambda e, p=path: self._on_thumb_press(e, p))
            w.bind("<Control-Button-1>", lambda e, p=path: self._on_thumb_press(e, p))
            w.bind("<B1-Motion>", self._on_thumb_motion)
        outer.bind("<ButtonRelease-1>", lambda e: self._on_thumb_release(e))
