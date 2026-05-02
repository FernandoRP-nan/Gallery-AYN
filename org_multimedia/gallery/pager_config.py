"""Barra de paginacion de la galeria y ventana de configuracion (tuerca)."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..core.settings import save_app_settings

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

    @staticmethod
    def _pager_compact_page_list(total_pages: int, current_1: int) -> list[int | None]:
        """Lista de numeros de pagina (1-based); None = hueco (puntos suspensivos)."""
        tp = total_pages
        if tp <= 0:
            return []
        if tp <= 14:
            return list(range(1, tp + 1))
        cur = max(1, min(current_1, tp))
        edges = {1, 2, tp - 1, tp, cur - 2, cur - 1, cur, cur + 1, cur + 2}
        nums = sorted({p for p in edges if 1 <= p <= tp})
        out: list[int | None] = []
        prev = 0
        for p in nums:
            if prev and p > prev + 1:
                out.append(None)
            out.append(p)
            prev = p
        return out

    def _rebuild_pager_number_buttons(self) -> None:
        if not hasattr(self, "gallery_pager_numbers"):
            return
        for w in self.gallery_pager_numbers.winfo_children():
            w.destroy()
        total = len(self.ordered_paths)
        if total == 0:
            return
        tp = self._gallery_total_pages()
        cur_1 = self._gallery_page + 1
        pages = self._pager_compact_page_list(tp, cur_1)
        wrap = ttk.Frame(self.gallery_pager_numbers)
        wrap.pack(expand=True)
        row = ttk.Frame(wrap)
        row.pack(anchor="center")
        for item in pages:
            if item is None:
                ttk.Label(row, text="…", width=2).pack(side=tk.LEFT, padx=2)
                continue
            if item == cur_1:
                ttk.Label(
                    row,
                    text=str(item),
                    font=("Sans", 10, "bold"),
                    foreground="#7aa2f7",
                    width=3,
                ).pack(side=tk.LEFT, padx=2)
            else:
                ttk.Button(
                    row,
                    text=str(item),
                    width=3,
                    command=lambda p=item: self._gallery_go_page(p - 1),
                ).pack(side=tk.LEFT, padx=2)

    def _gallery_jump_from_spin(self) -> None:
        if not self.ordered_paths or not hasattr(self, "gallery_pager_jump_var"):
            return
        tp = self._gallery_total_pages()
        try:
            p1 = int(str(self.gallery_pager_jump_var.get()).strip())
        except ValueError:
            return
        p1 = max(1, min(p1, tp))
        self.gallery_pager_jump_var.set(str(p1))
        self._gallery_go_page(p1 - 1)

    def _apply_gallery_settings_refresh(self) -> None:
        self._update_pager_ui()
        if self.ordered_paths:
            self._start_thumb_worker(scroll_top_after=False)

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
        if hasattr(self, "gallery_pager_jump_spin"):
            tp_spin = max(1, tp) if total else 1
            self.gallery_pager_jump_spin.config(from_=1, to=tp_spin)
            self.gallery_pager_jump_var.set(str(page_1 if total else 1))
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
        self._rebuild_pager_number_buttons()

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
        ttk.Label(
            frm,
            text="Los cambios se aplican al instante.",
            foreground="#565f89",
            font=("Sans", 9),
        ).pack(anchor="w", pady=(0, 8))

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

        def sync_from_dialog(*_args: object) -> None:
            try:
                pp = int(per_page.get())
            except ValueError:
                return
            if pp not in ALLOWED_THUMBS_PER_PAGE:
                return
            self.settings["gallery_show_thumb_filename"] = show_name.get()
            self.settings["gallery_thumbs_per_page"] = pp
            self.settings["gallery_scroll_top_on_page_change"] = scroll_top.get()
            self.settings["gallery_compact_thumb_padding"] = dense.get()
            save_app_settings(self.settings)
            self._clamp_gallery_page()
            self._apply_gallery_settings_refresh()

        show_name.trace_add("write", lambda *_a: sync_from_dialog())
        scroll_top.trace_add("write", lambda *_a: sync_from_dialog())
        dense.trace_add("write", lambda *_a: sync_from_dialog())
        cb.bind("<<ComboboxSelected>>", sync_from_dialog)

        btn_row = ttk.Frame(frm)
        btn_row.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(btn_row, text="Cerrar", command=top.destroy).pack(side=tk.RIGHT)
