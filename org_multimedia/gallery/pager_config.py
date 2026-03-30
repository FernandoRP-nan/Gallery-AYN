"""Barra de paginacion de la galeria y ventana de configuracion (tuerca)."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from ..settings import save_app_settings

# Valores permitidos para miniaturas por pagina (pixmaps en X ~ proporcional).
ALLOWED_THUMBS_PER_PAGE = (60, 90, 120, 150, 180, 240)


class GalleryPagerAndSettingsMixin:
    def _thumbs_per_page(self) -> int:
        n = int(self.settings.get("gallery_thumbs_per_page", 120))
        if n not in ALLOWED_THUMBS_PER_PAGE:
            return min(ALLOWED_THUMBS_PER_PAGE, key=lambda x: abs(x - n))
        return n

    def _gallery_show_filename(self) -> bool:
        return bool(self.settings.get("gallery_show_thumb_filename", True))

    def _gallery_total_pages(self) -> int:
        total = len(self.ordered_paths)
        if total == 0:
            return 1
        ps = self._thumbs_per_page()
        return max(1, (total + ps - 1) // ps)

    def _clamp_gallery_page(self) -> None:
        tp = self._gallery_total_pages()
        self._gallery_page = max(0, min(self._gallery_page, tp - 1))

    def _gallery_page_slice(self) -> tuple[int, int]:
        """Indices [start, end) en ordered_paths para la pagina actual."""
        ps = self._thumbs_per_page()
        start = self._gallery_page * ps
        end = min(start + ps, len(self.ordered_paths))
        return start, end

    def _update_pager_ui(self) -> None:
        if not hasattr(self, "gallery_pager_label"):
            return
        total = len(self.ordered_paths)
        tp = self._gallery_total_pages()
        self._clamp_gallery_page()
        page_1 = self._gallery_page + 1
        start, end = self._gallery_page_slice()
        self.gallery_pager_label.configure(
            text=(
                f"Pagina {page_1} de {tp}  ·  "
                f"imagenes {start + 1}-{end} de {total}" if total else "Sin imagenes en esta carpeta"
            )
        )
        empty = total == 0
        first = self._gallery_page <= 0 or empty
        last = self._gallery_page >= tp - 1 or empty
        for btn, dis in (
            (self.gallery_pager_first, first),
            (self.gallery_pager_prev, first),
            (self.gallery_pager_next, last),
            (self.gallery_pager_last, last),
        ):
            btn.config(state=tk.DISABLED if dis else tk.NORMAL)

    def _gallery_go_page(self, index: int) -> None:
        if not self.ordered_paths:
            return
        tp = self._gallery_total_pages()
        self._gallery_page = max(0, min(index, tp - 1))
        self._reload_gallery_page()

    def _gallery_first_page(self) -> None:
        self._gallery_go_page(0)

    def _gallery_prev_page(self) -> None:
        self._gallery_go_page(self._gallery_page - 1)

    def _gallery_next_page(self) -> None:
        self._gallery_go_page(self._gallery_page + 1)

    def _gallery_last_page(self) -> None:
        self._gallery_go_page(self._gallery_total_pages() - 1)

    def _reload_gallery_page(self) -> None:
        self._update_pager_ui()
        self._start_thumb_worker(
            scroll_top_after=bool(self.settings.get("gallery_scroll_top_on_page_change", True)),
        )

    def _open_gallery_settings_dialog(self) -> None:
        top = tk.Toplevel(self.root)
        top.title("Configuracion de la galeria")
        top.configure(bg="#1a1b26")
        top.geometry("420x320")
        top.transient(self.root)
        top.grab_set()

        frm = ttk.Frame(top, padding=16)
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text="Apariencia y listado", font=("Sans", 11, "bold")).pack(anchor="w", pady=(0, 10))

        show_name = tk.BooleanVar(value=bool(self.settings.get("gallery_show_thumb_filename", True)))
        ttk.Checkbutton(
            frm,
            text="Mostrar nombre del archivo bajo cada miniatura",
            variable=show_name,
        ).pack(anchor="w", pady=(0, 8))

        row = ttk.Frame(frm)
        row.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(row, text="Miniaturas por pagina:").pack(side=tk.LEFT)
        per_page = tk.StringVar(value=str(self._thumbs_per_page()))
        cb = ttk.Combobox(
            row,
            textvariable=per_page,
            values=[str(x) for x in ALLOWED_THUMBS_PER_PAGE],
            state="readonly",
            width=6,
        )
        cb.pack(side=tk.LEFT, padx=(8, 0))
        ttk.Label(row, text="(menos = menos memoria grafica)", foreground="#565f89", font=("Sans", 8)).pack(
            side=tk.LEFT, padx=(8, 0)
        )

        scroll_top = tk.BooleanVar(value=bool(self.settings.get("gallery_scroll_top_on_page_change", True)))
        ttk.Checkbutton(
            frm,
            text="Al cambiar de pagina, desplazar la galeria al inicio",
            variable=scroll_top,
        ).pack(anchor="w", pady=(0, 8))

        dense = tk.BooleanVar(value=bool(self.settings.get("gallery_compact_thumb_padding", False)))
        ttk.Checkbutton(
            frm,
            text="Celdas mas compactas (menos padding vertical entre filas)",
            variable=dense,
        ).pack(anchor="w", pady=(0, 12))

        hint = ttk.Label(
            frm,
            text="El tamano del zoom de miniaturas sigue en la pestaña Ruta.",
            foreground="#565f89",
            wraplength=380,
        )
        hint.pack(anchor="w", pady=(0, 12))

        def apply_settings() -> None:
            try:
                pp = int(per_page.get())
            except ValueError:
                pp = 120
            if pp not in ALLOWED_THUMBS_PER_PAGE:
                messagebox.showwarning("Valor invalido", "Elige un tamano de pagina de la lista.", parent=top)
                return
            old_pp = self._thumbs_per_page()
            self.settings["gallery_show_thumb_filename"] = show_name.get()
            self.settings["gallery_thumbs_per_page"] = pp
            self.settings["gallery_scroll_top_on_page_change"] = scroll_top.get()
            self.settings["gallery_compact_thumb_padding"] = dense.get()
            save_app_settings(self.settings)
            if pp != old_pp:
                self._gallery_page = 0
            self._clamp_gallery_page()
            self._update_pager_ui()
            top.destroy()
            if self.ordered_paths:
                self._start_thumb_worker(scroll_top_after=True)

        btn_row = ttk.Frame(frm)
        btn_row.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(btn_row, text="Aplicar", command=apply_settings).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(btn_row, text="Cancelar", command=top.destroy).pack(side=tk.RIGHT)
