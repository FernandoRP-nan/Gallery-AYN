"""Carpeta actual, subcarpetas y barra de ruta."""

from __future__ import annotations

import os
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from ..gallery_paths import list_subdirs, scan_images_flat
from ..settings import save_app_settings


class GalleryNavigationMixin:
    def _browse_folder(self) -> None:
        initial = self.folder_var.get().strip() or os.path.expanduser("~")
        folder = filedialog.askdirectory(title="Carpeta de la galeria", initialdir=initial)
        if folder:
            self.folder_var.set(folder)
            self.settings["gallery_last_folder"] = folder
            save_app_settings(self.settings)

    def _load_gallery(self) -> None:
        raw = self.folder_var.get().strip()
        if not raw:
            messagebox.showwarning("Carpeta", "Indica una carpeta para la galeria.")
            return
        folder = Path(os.path.expandvars(os.path.expanduser(raw))).resolve()
        if not folder.is_dir():
            messagebox.showerror("Carpeta", f"No existe o no es carpeta:\n{folder}")
            return
        self.gallery_folder = folder
        self.settings["gallery_last_folder"] = str(folder)
        save_app_settings(self.settings)
        self._reload_current_folder()

    def _reload_current_folder(self) -> None:
        if not self.gallery_folder:
            messagebox.showinfo("Galeria", "Primero pulsa 'Cargar galeria' y elige una carpeta.")
            return
        folder = self.gallery_folder.resolve()
        if not folder.is_dir():
            messagebox.showerror("Carpeta", f"La carpeta ya no existe o no es valida:\n{folder}")
            return
        self.gallery_folder = folder
        self.folder_var.set(str(folder))
        self.path_display_var.set(str(folder))
        self.settings["gallery_last_folder"] = str(folder)
        save_app_settings(self.settings)
        self._refresh_subfolder_list()
        self._clear_grid()
        self.ordered_paths = scan_images_flat(folder)
        self.selected.clear()
        self.anchor_index = None
        self._thumb_offset = 0
        self._update_selection_label()
        n_img = len(self.ordered_paths)
        n_sub = len(self._subfolder_paths)
        self.status_gallery.set(
            f"En esta carpeta: {n_img} imagen(es), {n_sub} subcarpeta(s). "
            "(Solo archivos directos; no se busca en subcarpetas.)"
        )
        self._start_thumb_worker(reset_offset=True)

    def _nav_up(self) -> None:
        if not self.gallery_folder:
            messagebox.showinfo("Galeria", "Carga una carpeta primero.")
            return
        parent = self.gallery_folder.parent
        if parent == self.gallery_folder:
            return
        if not parent.is_dir():
            return
        self.gallery_folder = parent.resolve()
        self.settings["gallery_last_folder"] = str(self.gallery_folder)
        save_app_settings(self.settings)
        self._reload_current_folder()

    def _on_subfolder_activate(self, _event: tk.Event | None = None) -> None:
        sel = self.subfolder_lb.curselection()
        if not sel:
            return
        idx = int(sel[0])
        if 0 <= idx < len(self._subfolder_paths):
            self.gallery_folder = self._subfolder_paths[idx].resolve()
            self.settings["gallery_last_folder"] = str(self.gallery_folder)
            save_app_settings(self.settings)
            self._reload_current_folder()

    def _refresh_subfolder_list(self) -> None:
        self.subfolder_lb.delete(0, tk.END)
        self._subfolder_paths = []
        if not self.gallery_folder:
            return
        for d in list_subdirs(self.gallery_folder):
            self.subfolder_lb.insert(tk.END, f"  {d.name}")
            self._subfolder_paths.append(d)
