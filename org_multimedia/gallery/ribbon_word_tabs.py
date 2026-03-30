"""Cinta superior tipo Microsoft Word: fila de pestañas y un panel que cambia según la pestaña activa."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class GalleryWordRibbon(tk.Frame):
    """Una sola franja: pestañas arriba y debajo el contenido de la pestaña seleccionada."""

    STRIP_BG = "#16161e"
    TAB_INACTIVE = "#24283b"
    TAB_ACTIVE = "#3b4261"
    TAB_HOVER = "#414868"
    FG = "#c0caf5"

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, bg="#1a1b26")
        self._tabs_bar = tk.Frame(self, bg=self.STRIP_BG)
        self._tabs_bar.pack(fill=tk.X)
        tk.Frame(self, height=1, bg="#565f89").pack(fill=tk.X)
        self._body = ttk.Frame(self)
        self._body.pack(fill=tk.X, padx=4, pady=(6, 8))
        self._pages: dict[str, ttk.Frame] = {}
        self._labels: dict[str, tk.Label] = {}
        self._active: str | None = None

    def add_tab(self, tab_id: str, title: str) -> ttk.Frame:
        lbl = tk.Label(
            self._tabs_bar,
            text=title,
            bg=self.TAB_INACTIVE,
            fg=self.FG,
            font=("Sans", 10, "bold"),
            padx=18,
            pady=10,
            cursor="hand2",
        )
        lbl.pack(side=tk.LEFT, padx=(2, 0), pady=(4, 0))
        lbl.bind("<Button-1>", lambda _e, tid=tab_id: self.select(tid))
        lbl.bind("<Enter>", lambda _e, tid=tab_id: self._hover(tid, True))
        lbl.bind("<Leave>", lambda _e, tid=tab_id: self._hover(tid, False))
        page = ttk.Frame(self._body)
        self._pages[tab_id] = page
        self._labels[tab_id] = lbl
        return page

    def _hover(self, tab_id: str, on: bool) -> None:
        if self._active == tab_id:
            return
        bg = self.TAB_HOVER if on else self.TAB_INACTIVE
        self._labels[tab_id].configure(bg=bg)

    def select(self, tab_id: str) -> None:
        if tab_id not in self._pages:
            return
        if self._active == tab_id:
            return
        if self._active is not None:
            self._pages[self._active].pack_forget()
            if self._active in self._labels:
                self._labels[self._active].configure(bg=self.TAB_INACTIVE)
        self._active = tab_id
        self._pages[tab_id].pack(fill=tk.X)
        self._labels[tab_id].configure(bg=self.TAB_ACTIVE)
