"""Ventana principal: notebook con organización automática y galería manual."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .gallery_frame import GalleryManualFrame
from .organizer_tab import OrganizerApp
from .settings import load_app_settings, save_app_settings
from .ui_theme import apply_dark_theme


def main() -> None:
    root = tk.Tk()
    settings = load_app_settings()
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

    def _set_start_maximized() -> None:
        if not bool(settings.get("window_start_maximized", True)):
            return
        try:
            root.state("zoomed")
        except tk.TclError:
            try:
                root.attributes("-zoomed", True)
            except tk.TclError:
                pass

    def _on_close() -> None:
        is_zoomed = False
        try:
            is_zoomed = root.state() == "zoomed"
        except tk.TclError:
            try:
                is_zoomed = bool(root.attributes("-zoomed"))
            except tk.TclError:
                is_zoomed = False
        settings["window_start_maximized"] = is_zoomed or bool(settings.get("window_start_maximized", True))
        save_app_settings(settings)
        root.destroy()

    root.after(10, _set_start_maximized)
    root.protocol("WM_DELETE_WINDOW", _on_close)
    root.mainloop()
