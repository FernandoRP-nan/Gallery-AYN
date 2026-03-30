"""Tema oscuro ttk / ventana raiz."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


def apply_dark_theme(root: tk.Tk, style: ttk.Style) -> None:
    bg = "#1a1b26"
    fg = "#c0caf5"
    fg_dim = "#a9b1d6"
    accent = "#7aa2f7"
    surface = "#24283b"
    entry_bg = "#16161e"
    if "clam" in style.theme_names():
        style.theme_use("clam")
    root.configure(bg=bg)
    style.configure("TFrame", background=bg)
    style.configure("TLabel", background=bg, foreground=fg)
    style.configure("TLabelframe", background=bg, foreground=fg)
    style.configure("TLabelframe.Label", background=bg, foreground=accent)
    style.configure("TButton", background=surface, foreground=fg)
    style.map("TButton", background=[("active", "#414868")])
    style.configure("TCheckbutton", background=bg, foreground=fg)
    style.configure("TEntry", fieldbackground=entry_bg, foreground=fg)
    style.configure("TNotebook", background=bg)
    style.configure("TNotebook.Tab", background=surface, foreground=fg_dim, padding=[12, 6])
    style.map("TNotebook.Tab", background=[("selected", "#414868")], foreground=[("selected", fg)])
    style.configure("Horizontal.TProgressbar", troughcolor=entry_bg, background=accent, thickness=8)
    style.configure("Card.TFrame", background=surface, relief="flat")
    style.configure("Dest.TLabel", background=surface, foreground=fg, font=("Sans", 10, "bold"))
    style.configure("DestPath.TLabel", background=surface, foreground=fg_dim, font=("Sans", 8))
    style.configure("GalleryThumb.TFrame", background=surface, relief="flat")
    style.configure("GalleryTitle.TLabel", background=bg, foreground=accent, font=("Sans", 14, "bold"))


