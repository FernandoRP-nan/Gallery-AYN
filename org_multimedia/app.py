"""Ventana principal: notebook con organización automática y galería manual."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .gallery_frame import GalleryManualFrame
from .organizer_tab import OrganizerApp
from .ui_theme import apply_dark_theme


def main() -> None:
    root = tk.Tk()
    style = ttk.Style()
    apply_dark_theme(root, style)
    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
    tab_auto = ttk.Frame(notebook, padding=4)
    tab_gallery = ttk.Frame(notebook, padding=4)
    notebook.add(tab_auto, text="  Organizacion automatica  ")
    notebook.add(tab_gallery, text="  Galeria manual  ")
    _auto = OrganizerApp(tab_auto)
    _gallery = GalleryManualFrame(tab_gallery)
    _ = (_auto, _gallery)
    root.mainloop()
