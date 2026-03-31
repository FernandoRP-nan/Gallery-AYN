"""Construcción de widgets de la pestaña galería."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .ribbon_word_tabs import GalleryWordRibbon
from ..settings import save_app_settings


class GalleryUIBuildMixin:
    def _build_ui(self) -> None:
        self.ribbon = GalleryWordRibbon(self, on_tab_changed=self._on_ribbon_tab_changed)
        self.ribbon.pack(fill=tk.X)
        ttk.Button(
            self.ribbon._tabs_bar,
            text="\u2699",
            width=3,
            command=self._open_gallery_settings_dialog,
        ).pack(side=tk.RIGHT, padx=(8, 6), pady=(4, 0))

        # --- Pestaña Ruta (carpeta y navegacion) ---
        page_ruta = self.ribbon.add_tab("ruta", "Ruta")
        row1 = ttk.Frame(page_ruta)
        row1.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(row1, text="Carpeta:").pack(side=tk.LEFT)
        entry = ttk.Entry(row1, textvariable=self.folder_var, width=70)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 8))
        ttk.Button(row1, text="Explorar...", command=self._browse_folder).pack(side=tk.LEFT)
        ttk.Button(row1, text="Cargar galeria", command=self._load_gallery).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Button(row1, text="Ajustes destinos...", command=self._open_settings).pack(side=tk.LEFT, padx=(8, 0))

        nav_row = ttk.Frame(page_ruta)
        nav_row.pack(fill=tk.X, pady=(0, 4))
        ttk.Button(nav_row, text="Carpeta superior", command=self._nav_up).pack(side=tk.LEFT)
        ttk.Button(nav_row, text="Actualizar esta carpeta", command=self._reload_current_folder).pack(
            side=tk.LEFT, padx=(8, 0)
        )
        ttk.Label(nav_row, textvariable=self.path_display_var, wraplength=400, foreground="#a9b1d6").pack(
            side=tk.LEFT, padx=(12, 0), fill=tk.X, expand=True
        )

        # --- Pestaña Seleccion ---
        page_sel = self.ribbon.add_tab("sel", "Seleccion")
        sel_inner = ttk.Frame(page_sel)
        sel_inner.pack(fill=tk.X, pady=2)
        ttk.Button(sel_inner, text="Seleccionar pagina actual", command=self._select_all).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Button(sel_inner, text="Quitar seleccion", command=self._select_none).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(sel_inner, text="Invertir seleccion", command=self._invert_selection).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Checkbutton(
            sel_inner,
            text="Un clic alterna (sin Ctrl): añade o quita de la seleccion",
            variable=self.toggle_click_var,
        ).pack(side=tk.LEFT, padx=(12, 0))
        ttk.Label(sel_inner, textvariable=self.selection_count_var, foreground="#9ece6a", font=("Sans", 10, "bold")).pack(
            side=tk.RIGHT, padx=(8, 0)
        )
        ttk.Label(
            page_sel,
            text=(
                "Si alternar esta desactivado: clic = una sola imagen + vista previa. "
                "Ctrl+clic = añadir o quitar. Shift+clic = rango. "
                "Arrastra la seleccion a un destino (pestaña Destinos) o suelta sobre la tarjeta."
            ),
            wraplength=900,
            foreground="#565f89",
        ).pack(anchor="w", pady=(4, 0))

        # --- Pestaña Subcarpetas ---
        page_sub = self.ribbon.add_tab("sub", "Subcarpetas")
        ttk.Label(
            page_sub,
            text="Doble clic o Enter en una fila para entrar en esa carpeta.",
            foreground="#565f89",
        ).pack(anchor="w", pady=(0, 4))
        sub_inner = ttk.Frame(page_sub)
        sub_inner.pack(fill=tk.BOTH, expand=True)
        self.subfolder_lb = tk.Listbox(
            sub_inner,
            height=5,
            bg="#16161e",
            fg="#c0caf5",
            selectbackground="#414868",
            selectforeground="#c0caf5",
            relief=tk.FLAT,
            highlightthickness=0,
        )
        sf_scroll = ttk.Scrollbar(sub_inner, orient="vertical", command=self.subfolder_lb.yview)
        self.subfolder_lb.configure(yscrollcommand=sf_scroll.set)
        self.subfolder_lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sf_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.subfolder_lb.bind("<Double-Button-1>", self._on_subfolder_activate)
        self.subfolder_lb.bind("<Return>", self._on_subfolder_activate)

        # --- Pestaña Destinos ---
        page_dest = self.ribbon.add_tab("dest", "Destinos")
        ttk.Label(
            page_dest,
            text="Arrastra seleccion aqui o pulsa una tarjeta. '+' anade carpeta (tambien en Ajustes destinos).",
            foreground="#565f89",
        ).pack(anchor="w", pady=(0, 4))
        dest_outer = ttk.Frame(page_dest)
        dest_outer.pack(fill=tk.X)
        self.dest_hcanvas = tk.Canvas(dest_outer, bg="#1a1b26", height=104, highlightthickness=0)
        dest_hscroll = ttk.Scrollbar(dest_outer, orient="horizontal", command=self.dest_hcanvas.xview)
        self.dest_container = tk.Frame(self.dest_hcanvas, bg="#1a1b26")
        self.dest_hcanvas.create_window((0, 0), window=self.dest_container, anchor="nw")

        def _on_dest_configure(_event: tk.Event) -> None:
            self.dest_hcanvas.configure(scrollregion=self.dest_hcanvas.bbox("all"))

        self.dest_container.bind("<Configure>", _on_dest_configure)
        self.dest_hcanvas.pack(side=tk.TOP, fill=tk.X, expand=True)
        dest_hscroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.dest_hcanvas.configure(xscrollcommand=dest_hscroll.set)
        self._refresh_destinations()

        self.ribbon.select("ruta")
        self.ribbon.set_collapsed(True)

        # Control global: visible siempre, sin depender de la pestaña activa.
        zoom_row = ttk.Frame(self)
        zoom_row.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(zoom_row, text="Tamaño miniaturas:").pack(side=tk.LEFT, padx=(0, 8))
        self.thumb_scale_slider = ttk.Scale(
            zoom_row,
            from_=0.75,
            to=2.25,
            orient=tk.HORIZONTAL,
            length=280,
            variable=self.thumb_scale_var,
            command=self._on_thumb_scale_slider,
        )
        self.thumb_scale_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.thumb_scale_label = ttk.Label(zoom_row, text="", foreground="#a9b1d6", width=6)
        self.thumb_scale_label.pack(side=tk.LEFT, padx=(8, 0))
        self.thumb_scale_label.configure(text=f"{int(self.thumb_scale_var.get() * 100)}%")
        ttk.Label(
            zoom_row,
            text="(Derecha = menos columnas y mas grande | recortan para cuadrado)",
            foreground="#565f89",
        ).pack(side=tk.LEFT, padx=(12, 0))

        # --- Cuerpo principal: galeria + vista previa (todo el espacio vertical restante) ---
        self.main_pane = tk.PanedWindow(
            self,
            orient=tk.HORIZONTAL,
            sashwidth=5,
            bg="#1a1b26",
            sashrelief=tk.FLAT,
        )
        self.main_pane.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        gallery_wrap = ttk.Frame(self.main_pane)
        self.preview_column = ttk.Frame(self.main_pane, width=460)
        self.main_pane.add(gallery_wrap, minsize=420)
        self.main_pane.add(self.preview_column, minsize=360)
        self.main_pane.bind("<ButtonRelease-1>", self._save_preview_pane_position, add="+")

        self.gallery_canvas = tk.Canvas(gallery_wrap, bg="#16161e", highlightthickness=0, height=380)
        scroll_y = ttk.Scrollbar(gallery_wrap, orient="vertical", command=self.gallery_canvas.yview)
        self.gallery_inner = tk.Frame(self.gallery_canvas, bg="#16161e")
        self.gallery_inner.bind(
            "<Configure>",
            lambda _e: self.gallery_canvas.configure(scrollregion=self.gallery_canvas.bbox("all")),
        )
        self._gallery_window_id = self.gallery_canvas.create_window((0, 0), window=self.gallery_inner, anchor="nw")
        self.gallery_canvas.configure(yscrollcommand=scroll_y.set)
        self.gallery_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.gallery_canvas.bind("<Configure>", self._on_gallery_canvas_configure)
        self._bind_gallery_scroll_events(self.gallery_canvas)
        self._bind_gallery_scroll_events(self.gallery_inner)

        preview_title = ttk.Label(self.preview_column, text="Vista previa", font=("Sans", 11, "bold"))
        preview_title.pack(anchor="w", pady=(0, 6))
        self.preview_box = tk.Frame(self.preview_column, bg="#16161e")
        self.preview_box.pack(fill=tk.BOTH, expand=True, pady=(0, 6))
        self.preview_box.pack_propagate(False)
        self.preview_image_label = tk.Label(
            self.preview_box,
            bg="#16161e",
            fg="#565f89",
            text="Clic en una miniatura",
            font=("Sans", 10),
        )
        self.preview_image_label.pack(expand=True, fill=tk.BOTH)
        self.preview_box.bind("<Configure>", self._on_preview_box_configure)
        self.preview_meta_label = tk.Label(
            self.preview_column,
            bg="#1a1b26",
            fg="#a9b1d6",
            font=("Sans", 8),
            wraplength=420,
            justify=tk.LEFT,
            text="",
        )
        self.preview_meta_label.pack(anchor="w", fill=tk.X)

        self.gallery_pager = tk.Frame(self, bg="#16161e", highlightthickness=1, highlightbackground="#414868")
        self.gallery_pager.pack(fill=tk.X, pady=(4, 0))
        pinner = ttk.Frame(self.gallery_pager)
        pinner.pack(fill=tk.X, padx=10, pady=(8, 4))
        row_nav = ttk.Frame(pinner)
        row_nav.pack(fill=tk.X)
        self.gallery_pager_first = ttk.Button(row_nav, text="|<<", width=5, command=self._gallery_first_page)
        self.gallery_pager_first.pack(side=tk.LEFT, padx=(0, 4))
        self.gallery_pager_prev = ttk.Button(row_nav, text="<", width=4, command=self._gallery_prev_page)
        self.gallery_pager_prev.pack(side=tk.LEFT, padx=(0, 6))
        self.gallery_pager_numbers = ttk.Frame(row_nav)
        self.gallery_pager_numbers.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.gallery_pager_next = ttk.Button(row_nav, text=">", width=4, command=self._gallery_next_page)
        self.gallery_pager_next.pack(side=tk.LEFT, padx=(6, 0))
        self.gallery_pager_last = ttk.Button(row_nav, text=">>|", width=5, command=self._gallery_last_page)
        self.gallery_pager_last.pack(side=tk.LEFT, padx=(4, 0))
        row_meta = ttk.Frame(pinner)
        row_meta.pack(fill=tk.X, pady=(6, 4))
        self.gallery_pager_label = ttk.Label(row_meta, text="", font=("Sans", 10))
        self.gallery_pager_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        jump = ttk.Frame(row_meta)
        jump.pack(side=tk.RIGHT)
        ttk.Label(jump, text="Ir a pag.").pack(side=tk.LEFT, padx=(0, 4))
        self.gallery_pager_jump_var = tk.StringVar(value="1")
        self.gallery_pager_jump_spin = ttk.Spinbox(
            jump,
            from_=1,
            to=1,
            width=5,
            textvariable=self.gallery_pager_jump_var,
            command=self._gallery_jump_from_spin,
        )
        self.gallery_pager_jump_spin.pack(side=tk.LEFT, padx=(0, 4))
        self.gallery_pager_jump_spin.bind("<Return>", lambda _e: self._gallery_jump_from_spin())
        ttk.Button(jump, text="Ir", width=4, command=self._gallery_jump_from_spin).pack(side=tk.LEFT)
        self._update_pager_ui()

        st = ttk.Label(self, textvariable=self.status_gallery, foreground="#7aa2f7")
        st.pack(anchor="w", fill=tk.X, pady=(6, 0))
        self.root.after(120, self._restore_preview_pane_position)

    def _restore_preview_pane_position(self) -> None:
        x = self.settings.get("gallery_preview_sash_x")
        if x is None:
            return
        try:
            self.main_pane.sash_place(0, int(x), 1)
        except (tk.TclError, ValueError):
            return

    def _save_preview_pane_position(self, _event: tk.Event | None = None) -> None:
        try:
            x, _y = self.main_pane.sash_coord(0)
        except tk.TclError:
            return
        self.settings["gallery_preview_sash_x"] = int(x)
        save_app_settings(self.settings)

    def _on_preview_box_configure(self, _event: tk.Event) -> None:
        w = int(self.preview_box.winfo_width())
        h = int(self.preview_box.winfo_height())
        lw, lh = getattr(self, "_preview_last_target_size", (0, 0))
        if abs(w - lw) < 24 and abs(h - lh) < 24:
            return
        if getattr(self, "_preview_resize_after", None) is not None:
            try:
                self.root.after_cancel(self._preview_resize_after)
            except tk.TclError:
                pass
        self._preview_resize_after = self.root.after(220, self._refresh_preview_on_resize)

    def _refresh_preview_on_resize(self) -> None:
        self._preview_resize_after = None
        path = getattr(self, "_preview_current_path", None)
        if path is not None:
            self._schedule_preview(path, show_loading=False)
