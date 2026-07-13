"""Lógica de procesamiento de imágenes y generación de miniaturas (DataURLs)."""

import base64
import io
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError:
    Image = None
    ImageOps = None

def has_pil() -> bool:
    return Image is not None

def save_pil_to_path(im: Image.Image, path: Path) -> None:
    """Guarda una imagen PIL respetando el tipo de archivo."""
    if Image is None:
        raise RuntimeError("Pillow no disponible")
    ext = path.suffix.lower()
    if ext in (".jpg", ".jpeg"):
        rgb = im.convert("RGB") if im.mode in ("RGBA", "P", "LA") else im
        rgb.save(path, format="JPEG", quality=95, optimize=True)
    elif ext == ".png":
        im.save(path, format="PNG", optimize=True)
    elif ext == ".webp":
        im.save(path, format="WEBP", quality=90, method=4)
    elif ext in (".bmp",):
        im.convert("RGB").save(path, format="BMP")
    elif ext in (".gif",):
        im.save(path, format="GIF", save_all=True)
    elif ext in (".tif", ".tiff"):
        im.save(path, format="TIFF", compression="tiff_lzw")
    else:
        im.save(path)

def thumb_px_from_gallery_scale(scale: float) -> int:
    """Escala lineal 0.01–2.25 → ~48–400 px."""
    lo, hi = 0.01, 2.25
    px_min, px_max = 48, 400
    s = max(lo, min(hi, float(scale)))
    return int(round(px_min + (s - lo) / (hi - lo) * (px_max - px_min)))

def thumb_px_from_dest_scale(scale: float) -> int:
    """Vista previa de carpeta destino."""
    lo, hi = 0.7, 2.1
    px_min, px_max = 88, 360
    s = max(lo, min(hi, float(scale)))
    return int(round(px_min + (s - lo) / (hi - lo) * (px_max - px_min)))

def img_to_data_url(path: Path, size: tuple[int, int]) -> str | None:
    if Image is None:
        return None
    try:
        with Image.open(path) as im:
            im = im.convert("RGBA")
            if ImageOps is not None:
                im = ImageOps.fit(im, size, Image.Resampling.LANCZOS, centering=(0.5, 0.5))
            else:
                im.thumbnail(size, Image.Resampling.LANCZOS)
            bio = io.BytesIO()
            im.save(bio, format="PNG")
            payload = base64.b64encode(bio.getvalue()).decode("ascii")
            return f"data:image/png;base64,{payload}"
    except Exception:
        return None

def img_to_data_url_contain(path: Path, max_w: int, max_h: int) -> str | None:
    """Vista previa sin recorte."""
    if Image is None:
        return None
    try:
        mw, mh = max(1, int(max_w)), max(1, int(max_h))
        with Image.open(path) as im:
            im = im.convert("RGBA")
            im.thumbnail((mw, mh), Image.Resampling.LANCZOS)
            bio = io.BytesIO()
            im.save(bio, format="PNG")
            payload = base64.b64encode(bio.getvalue()).decode("ascii")
            return f"data:image/png;base64,{payload}"
    except Exception:
        return None

def _load_rgb_for_thumb(path: Path):
    """Carga RGB con orientación EXIF aplicada."""
    with Image.open(path) as im_raw:
        im = im_raw
        if ImageOps is not None:
            im = ImageOps.exif_transpose(im)
        return im.convert("RGB")


def masonry_thumb_target_size(src_w: int, src_h: int, max_w: int, max_h: int) -> tuple[int, int]:
    """Tamaño objetivo masonry: en vertical fija ancho (UI width:100%) para evitar upscale borroso."""
    mw, mh = max(1, int(max_w)), max(1, int(max_h))
    if src_w <= 0 or src_h <= 0:
        return mw, mh
    if src_h > src_w:
        tw = mw
        th = min(mh, max(1, int(round(mw * src_h / src_w))))
        return tw, th
    ratio = min(mw / src_w, mh / src_h)
    tw = max(1, int(round(src_w * ratio)))
    th = max(1, int(round(src_h * ratio)))
    return tw, th


def ffmpeg_masonry_scale_filter(max_w: int, max_h: int) -> str:
    """Filtro scale para vídeo masonry con la misma prioridad de ancho en vertical."""
    mw, mh = max(48, int(max_w)), max(48, int(max_h))
    if mw % 2:
        mw += 1
    if mh % 2:
        mh += 1
    return (
        f"scale=w='if(gt(ih\\,iw)\\,{mw}\\,-2)':"
        f"h='if(gt(ih\\,iw)\\,-2\\,{mh})':force_original_aspect_ratio=decrease"
    )


def thumb_jpeg_data_url_square(path: Path, size: int, quality: int = 90) -> str | None:
    """Miniatura JPEG cuadrada."""
    if Image is None:
        return None
    try:
        from .gallery_thumb_disk_cache import (
            jpeg_bytes_to_data_url,
            load_thumb_jpeg,
            make_thumb_cache_id,
            save_thumb_jpeg,
            thumb_disk_cache_enabled,
        )

        use_disk = thumb_disk_cache_enabled()
        cache_id = ""
        if use_disk:
            cache_id = make_thumb_cache_id(path, variant="square", size=size, max_w=0, max_h=0, quality=quality)
            cached = load_thumb_jpeg(cache_id)
            if cached:
                return jpeg_bytes_to_data_url(cached)
        im = _load_rgb_for_thumb(path)
        side = max(1, int(size))
        if ImageOps is not None:
            im = ImageOps.fit(im, (side, side), Image.Resampling.LANCZOS, centering=(0.5, 0.5))
        else:
            im.thumbnail((side, side), Image.Resampling.LANCZOS)
        bio = io.BytesIO()
        im.save(bio, format="JPEG", quality=quality, optimize=True)
        jpeg_bytes = bio.getvalue()
        if use_disk and cache_id:
            save_thumb_jpeg(cache_id, jpeg_bytes)
        return jpeg_bytes_to_data_url(jpeg_bytes)
    except Exception:
        return None


def thumb_jpeg_data_url_masonry(path: Path, max_w: int, max_h: int, quality: int = 90) -> str | None:
    """Miniatura JPEG masonry: proporción original con ancho completo en retrato."""
    if Image is None:
        return None
    try:
        from .gallery_thumb_disk_cache import (
            jpeg_bytes_to_data_url,
            load_thumb_jpeg,
            make_thumb_cache_id,
            save_thumb_jpeg,
            thumb_disk_cache_enabled,
        )

        use_disk = thumb_disk_cache_enabled()
        cache_id = ""
        if use_disk:
            cache_id = make_thumb_cache_id(
                path, variant="masonry", size=0, max_w=max_w, max_h=max_h, quality=quality
            )
            cached = load_thumb_jpeg(cache_id)
            if cached:
                return jpeg_bytes_to_data_url(cached)
        mw, mh = max(1, int(max_w)), max(1, int(max_h))
        im = _load_rgb_for_thumb(path)
        w, h = im.size
        tw, th = masonry_thumb_target_size(w, h, mw, mh)
        if (w, h) != (tw, th):
            im = im.resize((tw, th), Image.Resampling.LANCZOS)
        bio = io.BytesIO()
        im.save(bio, format="JPEG", quality=quality, optimize=True)
        jpeg_bytes = bio.getvalue()
        if use_disk and cache_id:
            save_thumb_jpeg(cache_id, jpeg_bytes)
        return jpeg_bytes_to_data_url(jpeg_bytes)
    except Exception:
        return None


def dest_thumb_jpeg_data_url_contain(path: Path, size: int, quality: int = 90) -> str | None:
    """Miniatura modal destino (contain)."""
    if Image is None:
        return None
    try:
        with Image.open(path) as im:
            im = im.convert("RGB")
            im.thumbnail((size, size), Image.Resampling.LANCZOS)
            bio = io.BytesIO()
            im.save(bio, format="JPEG", quality=quality, optimize=True)
            payload = base64.b64encode(bio.getvalue()).decode("ascii")
            return f"data:image/jpeg;base64,{payload}"
    except Exception:
        return None
