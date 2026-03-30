"""Barra de destinos, diálogo de ajustes y mover archivos."""

from __future__ import annotations

import shutil
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from ..fs_utils import ensure_unique_destination
from ..gallery_paths import scan_images_flat
from ..settings import save_app_settings


class GalleryDestinationsMixin:
    def _quick_add_destination(self) -> None:
        path = self._browse_dest_folder()
        if not path:
            return
        p = Path(path).expanduser().resolve()
        default_label = p.name
        label = simpledialog.askstring(
            "Nombre del destino",
            "Etiqueta visible en la barra:",
            initialvalue=default_label,
            parent=self.root,
        )
        if label is None:
            return
        label = label.strip() or default_label
        self.settings.setdefault("destinations", []).append({"label": label, "path": str(p)})
        save_app_settings(self.settings)
        self._refresh_destinations()

    def _browse_dest_folder(self) -> str | None:
        return filedialog.askdirectory(title="Elegir carpeta destino")

    def _refresh_destinations(self) -> None:
        for w in self.dest_container.winfo_children():
            w.destroy()
        self.dest_widgets.clear()

        plus = tk.Frame(self.dest_container, bg="#414868", padx=14, pady=18, cursor="hand2")
        plus.pack(side=tk.LEFT, padx=(0, 10), pady=4)
        tk.Label(plus, text="+", bg="#414868", fg="#c0caf5", font=("Sans", 22, "bold")).pack()
        tk.Label(plus, text="Anadir", bg="#414868", fg="#a9b1d6", font=("Sans", 8)).pack()
        for w in plus.winfo_children():
            w.bind("<ButtonRelease-1>", lambda _e: self._quick_add_destination())
        plus.bind("<ButtonRelease-1>", lambda _e: self._quick_add_destination())

        dests = self.settings.get("destinations", [])
        if not dests:
            hint = ttk.Label(
                self.dest_container,
                text="Ningun destino: pulsa + o 'Ajustes destinos...'",
                foreground="#565f89",
            )
            hint.pack(side=tk.LEFT, anchor="w")
            return
        for item in dests:
            label = item.get("label") or "Destino"
            path_str = item.get("path") or ""
            card = tk.Frame(self.dest_container, bg="#24283b", padx=14, pady=12, cursor="hand2")
            card.pack(side=tk.LEFT, padx=(0, 8), pady=4)
            card.gallery_dest_path = Path(path_str).expanduser()  # type: ignore[attr-defined]
            l1 = tk.Label(card, text=label, bg="#24283b", fg="#c0caf5", font=("Sans", 10, "bold"))
            l1.pack(anchor="w")
            short = path_str if len(path_str) < 42 else path_str[:19] + "..." + path_str[-18:]
            l2 = tk.Label(card, text=short, bg="#24283b", fg="#565f89", font=("Sans", 8))
            l2.pack(anchor="w")
            dest_path = card.gallery_dest_path

            def on_enter(_e: tk.Event, c: tk.Frame = card) -> None:
                c.configure(bg="#565f89")

            def on_leave(_e: tk.Event, c: tk.Frame = card) -> None:
                c.configure(bg="#24283b")

            for w in (card, l1, l2):
                w.bind("<ButtonRelease-1>", lambda e, p=dest_path: self._release_on_destination(p))
                w.bind("<Enter>", on_enter)
                w.bind("<Leave>", on_leave)

    def _open_settings(self) -> None:
        top = tk.Toplevel(self.root)
        top.title("Destinos predefinidos")
        top.configure(bg="#1a1b26")
        top.geometry("520x320")
        ttk.Label(top, text="Etiqueta y ruta de cada carpeta destino:").pack(anchor="w", padx=12, pady=(12, 6))
        list_frame = ttk.Frame(top)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)
        scroll = ttk.Scrollbar(list_frame)
        lb = tk.Listbox(list_frame, height=10, bg="#16161e", fg="#c0caf5", selectbackground="#414868")
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.config(command=lb.yview)
        lb.config(yscrollcommand=scroll.set)

        def refresh_list() -> None:
            lb.delete(0, tk.END)
            for d in self.settings.get("destinations", []):
                lb.insert(tk.END, f"{d.get('label','')}  ->  {d.get('path','')}")

        refresh_list()

        btn_row = ttk.Frame(top)
        btn_row.pack(fill=tk.X, padx=12, pady=8)

        def add_dest() -> None:
            path = self._browse_dest_folder()
            if not path:
                return
            label = Path(path).name
            self.settings.setdefault("destinations", []).append({"label": label, "path": path})
            save_app_settings(self.settings)
            refresh_list()
            self._refresh_destinations()

        def remove_sel() -> None:
            sel = lb.curselection()
            if not sel:
                return
            idx = sel[0]
            dests = self.settings.get("destinations", [])
            if 0 <= idx < len(dests):
                dests.pop(idx)
                save_app_settings(self.settings)
                refresh_list()
                self._refresh_destinations()

        ttk.Button(btn_row, text="Anadir carpeta", command=add_dest).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_row, text="Quitar seleccionado", command=remove_sel).pack(side=tk.LEFT)
        ttk.Button(top, text="Cerrar", command=top.destroy).pack(anchor="e", padx=12, pady=12)

    def _move_to_dest(self, dest_dir: Path) -> None:
        if not self.selected:
            messagebox.showinfo("Galeria", "Selecciona al menos una imagen.")
            return
        dest_dir = dest_dir.expanduser().resolve()
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            messagebox.showerror("Destino", f"No se pudo crear o acceder:\n{e}")
            return
        moved = 0
        errors = 0
        for src in list(self.selected):
            try:
                target = dest_dir / src.name
                target = ensure_unique_destination(target)
                if src.resolve() == target.resolve():
                    continue
                shutil.move(str(src), str(target))
                moved += 1
            except Exception:
                errors += 1
        self.selected.clear()
        self._refresh_after_move()
        self.status_gallery.set(f"Movidas {moved} imagen(es). Errores: {errors}.")

    def _refresh_after_move(self) -> None:
        if not self.gallery_folder:
            return
        self._clear_grid()
        self.ordered_paths = scan_images_flat(self.gallery_folder)
        self.selected.clear()
        self.anchor_index = None
        self._gallery_page = 0
        self._update_selection_label()
        self._start_thumb_worker(scroll_top_after=True)
