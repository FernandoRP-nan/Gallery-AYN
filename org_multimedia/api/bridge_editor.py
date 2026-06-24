from __future__ import annotations

"""API bridge para PyWebView (frontend web -> backend Python)."""


import base64

import datetime

import io

import os

import shutil

import threading

import time

from concurrent.futures import ThreadPoolExecutor

from pathlib import Path

from ..core.fs_utils import ensure_unique_destination

from ..core.gallery_images import make_thumbnail_photoimage

from ..core.gallery_paths import (
    list_subdirs,
    scan_images_flat,
    scan_media_flat,
    scan_media_recursive,
    sort_image_paths,
)

from ..core.section_color import accent_hex_from_paths

_MONTH_NAMES_ES = (
    "",
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)

from ..core.media_organizer import MediaOrganizer
from ..core.viewer_playback import (
    needs_viewer_transcode,
    viewer_engine_label,
    viewer_playback_cache_status,
    viewer_prefers_webm,
    warm_viewer_playback_async,
)
from ..media_server import (
    build_media_file_url,
    mime_for_path,
    publish_media_url,
    publish_transcode_url,
    publish_viewer_playback_url,
)

from ..core.settings import load_app_settings, save_app_settings

try:
    from PIL import Image, ImageOps
except Exception:  # pragma: no cover
    Image = None
    ImageOps = None

def _save_pil_to_path(im: Image.Image, path: Path) -> None:
    """Guarda una imagen PIL respetando el tipo de archivo cuando es posible."""
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

def _thumb_px_from_gallery_scale(scale: float) -> int:
    """Escala lineal 0.01–2.25 → ~80–340 px (zoom-out máximo en miniaturas)."""
    lo, hi = 0.01, 2.25
    px_min, px_max = 48, 400
    s = max(lo, min(hi, float(scale)))
    return int(round(px_min + (s - lo) / (hi - lo) * (px_max - px_min)))

def _thumb_px_from_dest_scale(scale: float) -> int:
    """Vista previa de carpeta destino (rango de escala distinto en la UI)."""
    lo, hi = 0.7, 2.1
    px_min, px_max = 88, 360
    s = max(lo, min(hi, float(scale)))
    return int(round(px_min + (s - lo) / (hi - lo) * (px_max - px_min)))

def _img_to_data_url(path: Path, size: tuple[int, int]) -> str | None:
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

def _img_to_data_url_contain(path: Path, max_w: int, max_h: int) -> str | None:
    """Vista previa mostrando la imagen completa (sin recorte a 1:1)."""
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

def _thumb_jpeg_data_url_square(path: Path, size: int, quality: int = 90) -> str | None:
    """Miniatura cuadrada para la rejilla; JPEG reduce mucho el tamaño frente a PNG."""
    if Image is None:
        return None
    try:
        with Image.open(path) as im:
            im = im.convert("RGB")
            if ImageOps is not None:
                im = ImageOps.fit(im, (size, size), Image.Resampling.LANCZOS, centering=(0.5, 0.5))
            else:
                im.thumbnail((size, size), Image.Resampling.LANCZOS)
            bio = io.BytesIO()
            im.save(bio, format="JPEG", quality=quality, optimize=True)
            payload = base64.b64encode(bio.getvalue()).decode("ascii")
            return f"data:image/jpeg;base64,{payload}"
    except Exception:
        return None

def _dest_thumb_jpeg_data_url_contain(path: Path, size: int, quality: int = 90) -> str | None:
    """Miniatura modal destino: encaja en size×size manteniendo proporción."""
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

def _video_thumb_jpeg_data_url_square(path: Path, size: int, quality: int = 80) -> str | None:
    """Miniatura del primer fotograma de un video usando ffmpeg."""
    import subprocess
    if Image is None:
        return None
    try:
        # ffmpeg extrae el fotograma más cercano al segundo 0.5 como PNG en stdout
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-ss", "0.5",          # posición temporal (evita fotogramas negros)
                "-i", str(path),
                "-vframes", "1",       # solo un fotograma
                "-vf", f"scale={size}:{size}:force_original_aspect_ratio=decrease,pad={size}:{size}:(ow-iw)/2:(oh-ih)/2:black",
                "-f", "image2pipe",
                "-vcodec", "mjpeg",
                "pipe:1",
            ],
            capture_output=True,
            timeout=10,
        )
        if result.returncode != 0 or not result.stdout:
            return None
        payload = base64.b64encode(result.stdout).decode("ascii")
        return f"data:image/jpeg;base64,{payload}"
    except Exception:
        return None

class EditorBridgeMixin:
    def gallery_media_url(self, path: str) -> dict:
        """URL de streaming para vídeo/SVG (ruta corta /om-media/…)."""
        from ..core.fs_path import resolve_file_path

        try:
            p = resolve_file_path(path)
        except ValueError:
            return {"path": path, "fileUrl": None, "mimeType": None}
        ext = p.suffix.lower()
        if ext in MediaOrganizer.VIDEO_EXTENSIONS:
            warm_viewer_playback_async(p)
            cache = viewer_playback_cache_status(p)
            return {
                "path": str(p),
                "fileUrl": publish_media_url(p),
                "transcodeUrl": publish_viewer_playback_url(p),
                "needsTranscode": needs_viewer_transcode(p),
                "playbackMime": cache["playbackMime"],
                "playbackFormat": cache["playbackFormat"],
                "viewerEngine": viewer_engine_label(),
                "mimeType": mime_for_path(p),
            }
        if ext == ".svg":
            return {
                "path": str(p),
                "fileUrl": publish_media_url(p),
                "transcodeUrl": None,
                "needsTranscode": False,
                "mimeType": "image/svg+xml",
            }
        return {"path": str(p), "fileUrl": None, "transcodeUrl": None, "needsTranscode": False, "mimeType": None}

    def gallery_video_diagnostics(self, path: str, test_transcode: bool = False) -> dict:
        """Diagnóstico detallado cuando falla la reproducción en el visor integrado."""
        from ..core.fs_path import resolve_file_path
        from ..core.video_probe import video_diagnostics

        try:
            p = resolve_file_path(path)
        except ValueError as exc:
            return {"path": path, "exists": False, "error": str(exc)}
        return video_diagnostics(p, test_transcode=bool(test_transcode))

    def gallery_video_playback_blob(self, path: str) -> dict:
        """Data URL del vídeo transcodificado (PyWebView a veces no reproduce /om-webm/)."""
        import base64

        from ..core.fs_path import resolve_file_path
        from ..core.viewer_playback import ensure_viewer_playback

        max_bytes = 12 * 1024 * 1024
        try:
            p = resolve_file_path(path)
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}
        if p.suffix.lower() not in MediaOrganizer.VIDEO_EXTENSIONS:
            return {"ok": False, "error": "No es un vídeo"}
        stream_url = publish_viewer_playback_url(p)
        try:
            out, mime = ensure_viewer_playback(p)
        except Exception as exc:
            return {"ok": False, "error": str(exc), "streamUrl": stream_url}
        size = out.stat().st_size
        if size > max_bytes:
            return {"ok": False, "error": "too_large", "bytes": size, "streamUrl": stream_url}
        data = out.read_bytes()
        b64 = base64.b64encode(data).decode("ascii")
        return {
            "ok": True,
            "dataUrl": f"data:{mime};base64,{b64}",
            "mimeType": mime,
            "bytes": size,
            "streamUrl": stream_url,
        }

    def gallery_preview(self, path: str, width: int, height: int) -> dict:
        from ..core.fs_path import resolve_file_path

        try:
            p = resolve_file_path(path)
        except ValueError:
            fallback = Path(path).name
            return {
                "path": path,
                "name": fallback,
                "dataUrl": None,
                "mediaType": "image",
                "fileUrl": None,
            }
        ext = p.suffix.lower()
        if ext in MediaOrganizer.VIDEO_EXTENSIONS:
            warm_viewer_playback_async(p)
            cache = viewer_playback_cache_status(p)
            return {
                "path": str(p),
                "name": p.name,
                "dataUrl": None,
                "mediaType": "video",
                "fileUrl": build_media_file_url(p),
                "transcodeUrl": publish_viewer_playback_url(p),
                "needsTranscode": needs_viewer_transcode(p),
                "playbackMime": cache["playbackMime"],
                "playbackFormat": cache["playbackFormat"],
                "viewerEngine": viewer_engine_label(),
            }
        if ext == ".svg":
            return {
                "path": str(p),
                "name": p.name,
                "dataUrl": None,
                "mediaType": "svg",
                "fileUrl": build_media_file_url(p),
            }
        data_url = _img_to_data_url_contain(p, max(80, int(width)), max(80, int(height)))
        return {
            "path": str(p),
            "name": p.name,
            "dataUrl": data_url,
            "mediaType": "image",
            "fileUrl": None,
        }

    def gallery_file_base64(self, path: str) -> dict:
        """Lee el archivo original y lo codifica en base64 para evitar el alto consumo de memoria de decodificar/re-codificar PNG grandes."""
        import mimetypes
        p = Path(path).expanduser().resolve()
        if not p.is_file():
            return {"error": "File not found"}
        mime, _ = mimetypes.guess_type(str(p))
        if not mime:
            mime = "image/jpeg"
        try:
            with open(p, "rb") as f:
                data = base64.b64encode(f.read()).decode("ascii")
            return {"dataUrl": f"data:{mime};base64,{data}"}
        except Exception as e:
            return {"error": str(e)}

    def gallery_copy_to_clipboard(self, path: str) -> dict:
        """Copia una imagen directamente al portapapeles del SO (Wayland o X11)."""
        import subprocess
        p = Path(path).expanduser().resolve()
        if not p.is_file():
            return {"error": "Archivo no encontrado"}
        
        if Image is None:
            return {"error": "Pillow no disponible"}
            
        try:
            with Image.open(p) as im:
                bio = io.BytesIO()
                im.save(bio, format="PNG")
                png_data = bio.getvalue()
        except Exception as e:
            return {"error": f"Error al procesar la imagen: {e}"}

        # Wayland
        try:
            subprocess.run(["wl-copy", "-t", "image/png"], input=png_data, check=True)
            return {"ok": True}
        except FileNotFoundError:
            pass
        except Exception as e:
            pass

        # X11
        try:
            subprocess.run(["xclip", "-selection", "clipboard", "-t", "image/png"], input=png_data, check=True)
            return {"ok": True}
        except Exception as e:
            return {"error": "No se pudo copiar: falta wl-copy o xclip"}

    def gallery_copy_text_to_clipboard(self, text: str) -> dict:
        """Copia texto plano al portapapeles (Wayland o X11)."""
        import subprocess

        payload = str(text or "")
        if not payload.strip():
            return {"ok": False, "error": "Texto vacío"}
        data = payload.encode("utf-8")

        try:
            subprocess.run(["wl-copy"], input=data, check=True)
            return {"ok": True}
        except FileNotFoundError:
            pass
        except Exception:
            pass

        try:
            subprocess.run(["xclip", "-selection", "clipboard"], input=data, check=True)
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": f"No se pudo copiar: {exc}"}

    def gallery_image_rotate(self, path: str, degrees: int) -> dict:
        """Rota la imagen en disco (±90° o 180°)."""
        if Image is None or ImageOps is None:
            raise ValueError("Pillow no está disponible.")
        d = int(degrees)
        if d not in (-180, -90, 90, 180):
            raise ValueError("Solo rotaciones de ±90° o 180°.")
        p = Path(path).expanduser().resolve()
        if not p.is_file():
            raise ValueError("Archivo no encontrado.")
        if p.suffix.lower() not in MediaOrganizer.IMAGE_EXTENSIONS:
            raise ValueError("Formato no soportado para edición.")
        if p.suffix.lower() == ".svg":
            raise ValueError("SVG no se puede rotar desde aquí (usa un editor vectorial).")
        with self.lock:
            self._clear_thumb_cache()
            try:
                with Image.open(p) as im:
                    im = ImageOps.exif_transpose(im)
                    im = im.rotate(-d, expand=True, resample=Image.Resampling.BICUBIC)
                    _save_pil_to_path(im, p)
            except Exception as exc:
                raise ValueError(f"No se pudo rotar: {exc}") from exc
        return self.gallery_reload()

    def gallery_image_crop_normalized(self, path: str, left: float, top: float, width: float, height: float) -> dict:
        """Recorte con coordenadas 0–1 respecto al bitmap tras orientación EXIF."""
        if Image is None or ImageOps is None:
            raise ValueError("Pillow no está disponible.")
        p = Path(path).expanduser().resolve()
        if not p.is_file():
            raise ValueError("Archivo no encontrado.")
        if p.suffix.lower() not in MediaOrganizer.IMAGE_EXTENSIONS:
            raise ValueError("Formato no soportado para edición.")
        if p.suffix.lower() == ".svg":
            raise ValueError("SVG no se puede recortar desde aquí (usa un editor vectorial).")
        l = max(0.0, min(1.0, float(left)))
        t = max(0.0, min(1.0, float(top)))
        w = max(0.0, min(1.0, float(width)))
        h = max(0.0, min(1.0, float(height)))
        if w < 0.02 or h < 0.02:
            raise ValueError("El recorte es demasiado pequeño.")
        if l + w > 1.0 + 1e-6:
            w = 1.0 - l
        if t + h > 1.0 + 1e-6:
            h = 1.0 - t
        with self.lock:
            self._clear_thumb_cache()
            try:
                with Image.open(p) as im:
                    im = ImageOps.exif_transpose(im)
                    W, H = im.size
                    x0 = int(round(l * W))
                    y0 = int(round(t * H))
                    x1 = int(round((l + w) * W))
                    y1 = int(round((t + h) * H))
                    x1 = max(x0 + 1, min(W, x1))
                    y1 = max(y0 + 1, min(H, y1))
                    im = im.crop((x0, y0, x1, y1))
                    _save_pil_to_path(im, p)
            except Exception as exc:
                raise ValueError(f"No se pudo recortar: {exc}") from exc
        return self.gallery_reload()

    def _clear_thumb_cache(self) -> None:
        self._thumb_cache.clear()

    def _thumb_data_url_cached(self, path: Path, thumb_px: int, profile: str = "hq") -> str | None:
        key = (str(path.resolve()), thumb_px, profile)
        try:
            mtime = path.stat().st_mtime
        except OSError:
            return None
        with self._thumb_cache_lock:
            hit = self._thumb_cache.get(key)
            if hit is not None and hit[0] == mtime:
                return hit[1]
        if path.suffix.lower() in MediaOrganizer.VIDEO_EXTENSIONS:
            # Genera miniatura del primer fotograma con ffmpeg
            data = _video_thumb_jpeg_data_url_square(path, thumb_px)
            with self._thumb_cache_lock:
                self._thumb_cache[key] = (mtime, data)
            return data
        # Pillow no rasteriza SVG de forma fiable; la UI usa `file://` en vista previa.
        if path.suffix.lower() == ".svg":
            return None
        if profile == "lq":
            # Fase 1: miniatura rápida (menos calidad) para pintar la rejilla antes.
            data = _thumb_jpeg_data_url_square(path, max(48, int(thumb_px * 0.55)), quality=40)
        else:
            # Fase 2: miniatura nítida.
            data = _thumb_jpeg_data_url_square(path, int(round(thumb_px * 1.35)), quality=96)
        with self._thumb_cache_lock:
            self._thumb_cache[key] = (mtime, data)
        return data
