"""Color medio por muestreo de imágenes (fondos de sección en vista agrupada)."""

from __future__ import annotations

from pathlib import Path

try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None


def average_rgb_from_image_path(path: Path, resize: int = 24) -> tuple[int, int, int] | None:
    """RGB medio de una imagen reducida (rápido, suficiente para un tinte suave)."""
    if Image is None:
        return None
    try:
        with Image.open(path) as im:
            im = im.convert("RGB")
            im = im.resize((resize, resize), Image.Resampling.LANCZOS)
            px = list(im.getdata())
            if not px:
                return None
            r = sum(p[0] for p in px) // len(px)
            g = sum(p[1] for p in px) // len(px)
            b = sum(p[2] for p in px) // len(px)
            return (r, g, b)
    except Exception:
        return None


def accent_hex_from_paths(paths: list[Path], *, max_samples: int = 3) -> str | None:
    """Promedia hasta `max_samples` imágenes y devuelve #rrggbb, o None si no hay muestras válidas."""
    if not paths:
        return None
    rgbs: list[tuple[int, int, int]] = []
    for p in paths[:max_samples]:
        c = average_rgb_from_image_path(p)
        if c:
            rgbs.append(c)
    if not rgbs:
        return None
    r = sum(x[0] for x in rgbs) // len(rgbs)
    g = sum(x[1] for x in rgbs) // len(rgbs)
    b = sum(x[2] for x in rgbs) // len(rgbs)
    return f"#{r:02x}{g:02x}{b:02x}"
