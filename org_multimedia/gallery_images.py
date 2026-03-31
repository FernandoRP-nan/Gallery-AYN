"""Generacion de PhotoImage para miniaturas y vista previa (Pillow)."""

from __future__ import annotations

from pathlib import Path

from .pil_compat import HAS_PIL, Image, ImageOps, ImageTk


def make_thumbnail_photoimage(path: Path, thumb_size: tuple[int, int]) -> object | None:
    if not HAS_PIL or Image is None or ImageTk is None:
        return None
    tw, th = int(thumb_size[0]), int(thumb_size[1])
    size = (tw, th)
    try:
        with Image.open(path) as im:
            im = im.convert("RGBA")
            # Rellena el cuadrado (recorta bordes si hace falta).
            if ImageOps is not None:
                im = ImageOps.fit(
                    im,
                    size,
                    Image.Resampling.LANCZOS,
                    bleed=0.0,
                    centering=(0.5, 0.5),
                )
            else:
                im.thumbnail(size, Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(im)
    except Exception:
        return None


def load_preview_photoimage(path: Path, max_size: tuple[int, int]) -> object:
    """Solo llamar si HAS_PIL; si no hay PIL, la UI no debe invocar esto."""
    if Image is None or ImageTk is None:
        raise RuntimeError("Pillow no disponible")
    with Image.open(path) as im:
        im = im.copy()
        im.thumbnail(max_size, Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(im)


def load_preview_photoimage_fill_box(path: Path, box: tuple[int, int]) -> object:
    """Escala la imagen para caber en la caja y rellena el resto (color fondo galeria #16161e)."""
    if Image is None or ImageTk is None:
        raise RuntimeError("Pillow no disponible")
    bw, bh = int(box[0]), int(box[1])
    bg = (22, 22, 30)  # #16161e
    with Image.open(path) as im:
        im = im.convert("RGBA")
        if ImageOps is not None:
            im = ImageOps.pad(
                im,
                (bw, bh),
                method=Image.Resampling.LANCZOS,
                color=bg + (255,),
                centering=(0.5, 0.5),
            )
        else:
            im.thumbnail((bw, bh), Image.Resampling.LANCZOS)
            canvas = Image.new("RGBA", (bw, bh), bg + (255,))
            x = (bw - im.width) // 2
            y = (bh - im.height) // 2
            canvas.paste(im, (x, y), im)
            im = canvas
    return ImageTk.PhotoImage(im.convert("RGB"))
