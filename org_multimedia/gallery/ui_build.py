"""Construcción de widgets de la pestaña galería."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class GalleryUIBuildMixin:
    def _build_ui(self) -> None:
        title = ttk.Label(self, text="Galeria manual", style="GalleryTitle.TLabel")
        title.pack(anchor="w", pady=(0, 4))
        sub = ttk.Label(
            self,
            text=(
                "Solo esta carpeta (no recursivo). Navega con Subcarpetas / Carpeta superior. "
                "Las miniaturas se adaptan al ancho de la ventana."
            ),
            wraplength=780,
        )
        sub.pack(anchor="w", pady=(0, 8))

        sel_bar = ttk.LabelFrame(self, text="Seleccion")
        sel_bar.pack(fill=tk.X, pady=(0, 8))
        sel_inner = ttk.Frame(sel_bar)
        sel_inner.pack(fill=tk.X, padx=8, pady=6)
        ttk.Button(sel_inner, text="Seleccionar todas", command=self._select_all).pack(side=tk.LEFT, padx=(0, 6))
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
        help_sel = ttk.Label(
            sel_bar,
            text=(
                "Si alternar esta desactivado: clic = una sola imagen + vista previa. "
                "Ctrl+clic = añadir o quitar. Shift+clic = rango. "
                "Arrastra la seleccion a un destino abajo o suelta sobre la tarjeta."
            ),
            wraplength=760,
            foreground="#565f89",
        )
        help_sel.pack(anchor="w", padx=8, pady=(0, 6))

        row1 = ttk.Frame(self)
        row1.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(row1, text="Carpeta:").pack(side=tk.LEFT)
        entry = ttk.Entry(row1, textvariable=self.folder_var, width=70)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 8))
        ttk.Button(row1, text="Explorar...", command=self._browse_folder).pack(side=tk.LEFT)
        ttk.Button(row1, text="Cargar galeria", command=self._load_gallery).pack(side=tk.LEFT, padx=(4, 0))
        self.more_thumbs_btn = ttk.Button(row1, text="Mas miniaturas", command=self._load_more_thumbs, state=tk.DISABLED)
        self.more_thumbs_btn.pack(side=tk.LEFT, padx=(4, 0))
        ttk.Button(row1, text="Ajustes destinos...", command=self._open_settings).pack(side=tk.LEFT, padx=(8, 0))

        nav_row = ttk.Frame(self)
        nav_row.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(nav_row, text="Carpeta superior", command=self._nav_up).pack(side=tk.LEFT)
        ttk.Button(nav_row, text="Actualizar esta carpeta", command=self._reload_current_folder).pack(
            side=tk.LEFT, padx=(8, 0)
        )
        ttk.Label(nav_row, textvariable=self.path_display_var, wraplength=560, foreground="#a9b1d6").pack(
            side=tk.LEFT, padx=(12, 0), fill=tk.X, expand=True
        )

        sub_frame = ttk.LabelFrame(self, text="Subcarpetas (doble clic o Enter para entrar)")
        sub_frame.pack(fill=tk.X, pady=(0, 8))
        self.subfolder_lb = tk.Listbox(
            sub_frame,
            height=5,
            bg="#16161e",
            fg="#c0caf5",
            selectbackground="#414868",
            selectforeground="#c0caf5",
            relief=tk.FLAT,
            highlightthickness=0,
        )
        sf_scroll = ttk.Scrollbar(sub_frame, orient="vertical", command=self.subfolder_lb.yview)
        self.subfolder_lb.configure(yscrollcommand=sf_scroll.set)
        self.subfolder_lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 0), pady=4)
        sf_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=4, padx=(0, 4))
        self.subfolder_lb.bind("<Double-Button-1>", self._on_subfolder_activate)
        self.subfolder_lb.bind("<Return>", self._on_subfolder_activate)

        self.main_pane = tk.PanedWindow(
            self,
            orient=tk.HORIZONTAL,
            sashwidth=5,
            bg="#1a1b26",
            sashrelief=tk.FLAT,
        )
        self.main_pane.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        gallery_wrap = ttk.Frame(self.main_pane)
        self.preview_column = ttk.Frame(self.main_pane, width=460)
        self.main_pane.add(gallery_wrap, minsize=420)
        self.main_pane.add(self.preview_column, minsize=360)

        zoom_row = ttk.Frame(gallery_wrap)
        zoom_row.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(zoom_row, text="Tamaño miniaturas:").pack(side=tk.LEFT, padx=(0, 8))
        self.thumb_scale_slider = ttk.Scale(
            zoom_row,
            from_=0.75,
            to=2.25,
            orient=tk.HORIZONTAL,
            length=260,
            variable=self.thumb_scale_var,
            command=self._on_thumb_scale_slider,
        )
        self.thumb_scale_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.thumb_scale_label = ttk.Label(zoom_row, text="", foreground="#a9b1d6", width=6)
        self.thumb_scale_label.pack(side=tk.LEFT, padx=(8, 0))
        self.thumb_scale_label.configure(text=f"{int(self.thumb_scale_var.get() * 100)}%")
        ttk.Label(
            zoom_row,
            text="(Derecha = menos columnas y mas grande | miniaturas recortan para llenar el cuadrado)",
            foreground="#565f89",
        ).pack(side=tk.LEFT, padx=(12, 0))

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
        self.gallery_canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.gallery_canvas.bind("<Button-4>", lambda e: self.gallery_canvas.yview_scroll(-2, "units"))
        self.gallery_canvas.bind("<Button-5>", lambda e: self.gallery_canvas.yview_scroll(2, "units"))

        preview_title = ttk.Label(self.preview_column, text="Vista previa", font=("Sans", 11, "bold"))
        preview_title.pack(anchor="w", pady=(0, 6))
        prev_box = tk.Frame(self.preview_column, bg="#16161e", height=self.PREVIEW_MAX[1], width=self.PREVIEW_MAX[0])
        prev_box.pack(fill=tk.X, pady=(0, 6))
        prev_box.pack_propagate(False)
        self.preview_image_label = tk.Label(
            prev_box,
            bg="#16161e",
            fg="#565f89",
            text="Clic en una miniatura",
            font=("Sans", 10),
        )
        self.preview_image_label.pack(expand=True, fill=tk.BOTH)
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

        dest_frame = ttk.LabelFrame(self, text="Destinos rapidos (+ anade carpeta | arrastra o clic con seleccion)")
        dest_frame.pack(fill=tk.X, pady=(12, 0))
        dest_outer = ttk.Frame(dest_frame)
        dest_outer.pack(fill=tk.X, padx=4, pady=4)
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

        st = ttk.Label(self, textvariable=self.status_gallery, foreground="#7aa2f7")
        st.pack(anchor="w", pady=(8, 0))
