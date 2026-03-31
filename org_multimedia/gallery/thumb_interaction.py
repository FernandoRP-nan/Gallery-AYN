"""Clic en miniaturas, arrastre hacia destinos y resaltado."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path


class GalleryThumbInteractionMixin:
    def _on_ribbon_tab_changed(self, tab_id: str) -> None:
        self._active_ribbon_tab = tab_id
        self._update_thumb_check_visibility()

    def _update_thumb_check_visibility(self) -> None:
        show_checks = getattr(self, "_active_ribbon_tab", "ruta") in ("sel", "dest")
        for chk in getattr(self, "path_to_checkwidget", {}).values():
            if show_checks:
                chk.place(relx=0.98, rely=0.98, anchor="se")
            else:
                chk.place_forget()

    def _show_drag_badge(self, x_root: int, y_root: int) -> None:
        if self._drag_badge is None or not self._drag_badge.winfo_exists():
            self._drag_badge = tk.Toplevel(self.root)
            self._drag_badge.overrideredirect(True)
            self._drag_badge.attributes("-topmost", True)
            self._drag_badge.configure(bg="#24283b")
            self._drag_badge_label = tk.Label(
                self._drag_badge,
                bg="#24283b",
                fg="#c0caf5",
                padx=10,
                pady=6,
                font=("Sans", 10, "bold"),
                text="",
            )
            self._drag_badge_label.pack()
        if self._drag_badge_label is not None:
            n = len(self.selected)
            self._drag_badge_label.configure(text=f"Moviendo {n} imagen(es)")
        self._drag_badge.geometry(f"+{x_root + 18}+{y_root + 18}")
        self._drag_badge.deiconify()

    def _hide_drag_badge(self) -> None:
        if self._drag_badge is not None and self._drag_badge.winfo_exists():
            self._drag_badge.withdraw()

    def _index_of(self, path: Path) -> int | None:
        try:
            return self.ordered_paths.index(path)
        except ValueError:
            return None

    def _on_thumb_press(self, event: tk.Event, path: Path) -> None:
        self._drag_start = (event.x_root, event.y_root)
        self._drag_active = False
        idx = self._index_of(path)
        if idx is None:
            return
        if event.state & 0x0001:  # Shift
            if self.anchor_index is not None:
                a, b = sorted((self.anchor_index, idx))
                for i in range(a, b + 1):
                    self.selected.add(self.ordered_paths[i])
            else:
                self.selected.add(path)
                self.anchor_index = idx
        elif event.state & 0x0004:  # Control
            if path in self.selected:
                self.selected.discard(path)
            else:
                self.selected.add(path)
            self.anchor_index = idx
        elif self.toggle_click_var.get():
            if path in self.selected:
                self.selected.discard(path)
            else:
                self.selected.add(path)
            self.anchor_index = idx
        else:
            self.selected = {path}
            self.anchor_index = idx
        self._highlight_selection()
        self.status_gallery.set("Listo. Arrastra a un destino o usa los botones de seleccion.")
        self._schedule_preview(path)

    def _on_thumb_motion(self, event: tk.Event) -> None:
        if self._drag_start is None:
            return
        dx = event.x_root - self._drag_start[0]
        dy = event.y_root - self._drag_start[1]
        if (dx * dx + dy * dy) ** 0.5 > 10:
            self._drag_active = True
            if self.selected:
                self._show_drag_badge(event.x_root, event.y_root)
        if self._drag_active and self.selected:
            self._show_drag_badge(event.x_root, event.y_root)

    def _on_thumb_release(self, _event: tk.Event) -> None:
        self._drag_start = None

    def _on_global_release(self, event: tk.Event) -> None:
        if not self._drag_active or not self.selected:
            self._drag_active = False
            self._hide_drag_badge()
            return
        w = self.root.winfo_containing(event.x_root, event.y_root)
        dest_path = self._find_dest_path_widget(w)
        self._drag_active = False
        self._hide_drag_badge()
        if dest_path:
            self._move_to_dest(dest_path)

    def _release_on_destination(self, dest_path: Path) -> None:
        self._drag_active = False
        self._hide_drag_badge()
        if not self.selected:
            self.status_gallery.set("Selecciona imagenes en la galeria (usa 'Un clic alterna' o Ctrl+clic).")
            return
        self._move_to_dest(dest_path)

    def _find_dest_path_widget(self, w: tk.Misc | None) -> Path | None:
        while w is not None:
            p = getattr(w, "gallery_dest_path", None)
            if p is not None:
                return p  # type: ignore[no-any-return]
            try:
                parent_id = w.winfo_parent()
                if not parent_id or parent_id == ".":
                    break
                w = w.nametowidget(parent_id)
            except Exception:
                break
        return None

    def _on_thumb_checkbox_toggle(self, path: Path) -> None:
        """Casilla por miniatura: mismo criterio que Ctrl+clic (añade o quita)."""
        var = self.path_to_checkvar.get(path)
        if var is None:
            return
        if var.get():
            self.selected.add(path)
            idx = self._index_of(path)
            if idx is not None:
                self.anchor_index = idx
        else:
            self.selected.discard(path)
        self._highlight_selection()
        self._schedule_preview(path)
        self.status_gallery.set("Listo. Arrastra a un destino o usa los botones de seleccion.")

    def _highlight_selection(self) -> None:
        for path, frame in self.path_to_frame.items():
            col = "#414868" if path in self.selected else "#24283b"
            self._apply_bg_recursive(frame, col)
        for path, var in getattr(self, "path_to_checkvar", {}).items():
            want = path in self.selected
            if var.get() != want:
                var.set(want)
        self._update_selection_label()

    def _apply_bg_recursive(self, widget: tk.Misc, col: str) -> None:
        if isinstance(widget, (tk.Frame, tk.Label, tk.Canvas)):
            try:
                widget.configure(bg=col)
            except tk.TclError:
                pass
        elif isinstance(widget, tk.Checkbutton):
            try:
                widget.configure(bg=col, activebackground=col, highlightbackground=col)
            except tk.TclError:
                pass
        for ch in widget.winfo_children():
            self._apply_bg_recursive(ch, col)
