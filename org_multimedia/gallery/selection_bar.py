"""Botones de selección masiva y contador."""

from __future__ import annotations


class GallerySelectionBarMixin:
    def _update_selection_label(self) -> None:
        n = len(self.selected)
        total = len(self.ordered_paths)
        self.selection_count_var.set(f"{n} de {total} seleccionadas")

    def _select_all(self) -> None:
        if not self.ordered_paths:
            return
        start, end = self._gallery_page_slice()
        page_paths = self.ordered_paths[start:end]
        self.selected = set(page_paths)
        self.anchor_index = start if page_paths else None
        self._highlight_selection()
        self._update_selection_label()
        if page_paths:
            self._schedule_preview(page_paths[0])

    def _select_none(self) -> None:
        self.selected.clear()
        self.anchor_index = None
        self._highlight_selection()
        self._update_selection_label()

    def _invert_selection(self) -> None:
        self.selected = {p for p in self.ordered_paths if p not in self.selected}
        self._highlight_selection()
        self._update_selection_label()
