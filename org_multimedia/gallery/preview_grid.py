"""Vaciado de rejilla y vista previa grande."""

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path

from ..core.gallery_images import load_preview_photoimage_fill_box
from ..core.pil_compat import HAS_PIL


class GalleryPreviewGridMixin:
    def _clear_grid(self) -> None:
        for w in self.gallery_inner.winfo_children():
            w.destroy()
        self.path_to_frame.clear()
        if hasattr(self, "path_to_checkvar"):
            self.path_to_checkvar.clear()
        if hasattr(self, "path_to_checkwidget"):
            self.path_to_checkwidget.clear()
        self.thumb_refs.clear()
        self._photos.clear()
        self._clear_preview()

    def _clear_preview(self) -> None:
        self._preview_gen += 1
        self._preview_current_path = None
        self._preview_photo_large = None
        self.preview_image_label.configure(image="", text="Clic en una miniatura", fg="#565f89")
        self.preview_meta_label.configure(text="")

    def _current_preview_target_size(self) -> tuple[int, int]:
        w = int(self.preview_image_label.winfo_width())
        h = int(self.preview_image_label.winfo_height())
        fw = int(getattr(self, "preview_box", self.preview_image_label).winfo_width())
        fh = int(getattr(self, "preview_box", self.preview_image_label).winfo_height())
        tw = max(w, fw, 120)
        th = max(h, fh, 120)
        return tw, th

    def _schedule_preview(self, path: Path, *, show_loading: bool = True) -> None:
        self._preview_gen += 1
        prev_path = self._preview_current_path
        self._preview_current_path = path
        target_size = self._current_preview_target_size()
        gen = self._preview_gen
        same_path = prev_path == path and self._preview_photo_large is not None
        if not same_path:
            self.preview_meta_label.configure(text=f"{path.name}\n{path.parent}")
        if show_loading and not same_path:
            self.preview_image_label.configure(image="", text="Cargando vista previa...", fg="#7aa2f7")
        if not HAS_PIL:
            self.preview_image_label.configure(
                image="",
                text="Instala Pillow (pip install pillow)\npara vista previa grande.",
                fg="#e0af68",
            )
            return

        def worker() -> None:
            try:
                photo = load_preview_photoimage_fill_box(path, target_size)
                self.root.after(0, lambda: self._apply_preview_image(gen, photo, path, target_size))
            except Exception:
                self.root.after(0, lambda: self._apply_preview_error(gen, path))

        threading.Thread(target=worker, daemon=True).start()

    def _apply_preview_image(self, gen: int, photo: object, path: Path, target_size: tuple[int, int]) -> None:
        if gen != self._preview_gen:
            return
        self._preview_last_target_size = target_size
        self._preview_photo_large = photo
        self.preview_image_label.configure(image=photo, text="")

        try:
            st = path.stat()
            size_mb = st.st_size / (1024 * 1024)
            meta = f"{path.name}\n{path.parent}\n{size_mb:.2f} MB"
        except OSError:
            meta = str(path)
        self.preview_meta_label.configure(text=meta)

    def _apply_preview_error(self, gen: int, path: Path) -> None:
        if gen != self._preview_gen:
            return
        self._preview_photo_large = None
        self.preview_image_label.configure(image="", text="No se pudo cargar la vista previa", fg="#f7768e")
        self.preview_meta_label.configure(text=f"{path.name}\n{path.parent}")
