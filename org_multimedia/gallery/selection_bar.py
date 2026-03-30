"""Botones de selección masiva y contador."""

from __future__ import annotations


class GallerySelectionBarMixin:
    def _update_selection_label(self) -> None:
        n = len(self.selected)
        total = len(self.ordered_paths)
        self.selection_count_var.set(f"{n} de {total} seleccionadas")

    def _select_all(self) -> None:
        self.selected = set(self.ordered_paths)
        if self.ordered_paths:
            self.anchor_index = 0
        self._highlight_selection()
        self._update_selection_label()
        if self.ordered_paths:
            self._schedule_preview(self.ordered_paths[0])

    def _select_none(self) -> None:
        self.selected.clear()
        self.anchor_index = None
        self._highlight_selection()
        self._update_selection_label()

    def _invert_selection(self) -> None:
        self.selected = {p for p in self.ordered_paths if p not in self.selected}
        self._highlight_selection()
        self._update_selection_label()
