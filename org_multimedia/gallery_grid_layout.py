"""Metricas de rejilla de miniaturas (columnas, tamano) segun canvas y zoom."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GalleryGridMetrics:
    """Resultado de compute_metrics: todo lo necesario para pintar la rejilla."""

    layout_cols: int
    cell_outer_w: int
    thumb_size_tuple: tuple[int, int]
    gallery_cell_gap: int


class GalleryGridLayout:
    """Calcula columnas y lado de miniatura; filtra anchos espurios del canvas."""

    ZOOM_MIN = 0.75
    ZOOM_MAX = 2.25
    GAP = 6
    MARGIN_LR = 10
    CANVAS_TRIM = 14
    COLS_MIN = 2
    COLS_CAP = 16
    INNER_MARGIN = 8
    MIN_CELL = 48
    MIN_AVAIL = 48
    SAFE_W_MIN = 64
    # Lado objetivo de miniatura (px) en zoom min / max; de ahi se deduce cuantas columnas caben.
    # Tope moderado: PhotoImage por miniatura es un pixmap en X; valores muy altos + muchas a la vez -> BadAlloc.
    THUMB_TARGET_MIN = 58
    THUMB_TARGET_MAX = 280

    @classmethod
    def effective_canvas_width(cls, w: int | float, last_canvas_width: int) -> int:
        # Descarta anchos espurios durante reflow (frame vacio, eventos de Tk) que encogen la rejilla.
        try:
            iw = int(w)
        except (TypeError, ValueError):
            iw = 0
        last = int(last_canvas_width or 0)
        if iw < 80:
            return max(last, 400)
        if last >= 300 and iw < 120 and iw < (last * 22) // 100:
            return last
        return iw

    @classmethod
    def compute_metrics(cls, canvas_width: int, zoom: float) -> GalleryGridMetrics:
        # Ancho util del area de rejilla (ya excluye scrollbar del canvas).
        safe_w = max(cls.SAFE_W_MIN, int(canvas_width) - cls.CANVAS_TRIM)
        zoom = max(cls.ZOOM_MIN, min(cls.ZOOM_MAX, float(zoom)))
        avail = max(cls.MIN_AVAIL, safe_w - cls.MARGIN_LR)
        # Zoom alto => mayor objetivo de lado => menos columnas => celdas mas anchas (monotono y usa todo el ancho).
        t = (zoom - cls.ZOOM_MIN) / (cls.ZOOM_MAX - cls.ZOOM_MIN)
        thumb_target = int(
            cls.THUMB_TARGET_MIN + t * (cls.THUMB_TARGET_MAX - cls.THUMB_TARGET_MIN)
        )
        thumb_target = max(cls.MIN_CELL - cls.INNER_MARGIN, thumb_target)
        min_cell = thumb_target + cls.INNER_MARGIN
        gap = cls.GAP
        den = min_cell + gap
        if den <= 0:
            cols = cls.COLS_MIN
        else:
            cols_upper = int((avail + gap) // den)
            cols = max(cls.COLS_MIN, min(cls.COLS_CAP, cols_upper))
        total_gap = (cols - 1) * gap
        cell_w = (avail - total_gap) // cols
        cell_w = max(cls.MIN_CELL, cell_w)
        while cols > cls.COLS_MIN and cols * cell_w + total_gap > avail:
            cols -= 1
            total_gap = (cols - 1) * gap
            cell_w = (avail - total_gap) // cols
            cell_w = max(cls.MIN_CELL, cell_w)
        thumb_side = max(cls.MIN_CELL, cell_w - cls.INNER_MARGIN)
        return GalleryGridMetrics(
            layout_cols=cols,
            cell_outer_w=int(cell_w),
            thumb_size_tuple=(thumb_side, thumb_side),
            gallery_cell_gap=gap,
        )
