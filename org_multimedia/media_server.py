"""Servidor de streaming de vídeo/SVG para la galería web."""

from __future__ import annotations

import mimetypes
import os
import re
import threading
import urllib.parse
from pathlib import Path

import bottle

from .core.fs_path import resolve_file_path
from .core.media_organizer import MediaOrganizer
from .core.video_transcode import (
    ensure_transcoded_mp4,
    ensure_transcoded_webm,
    is_browser_playable,
    resolve_webm_source,
    warm_transcode_async,
)
from .core.viewer_playback import viewer_prefers_webm, warm_viewer_playback_async

_VIDEO_MIME = {
    ".mp4": "video/mp4",
    ".m4v": "video/mp4",
    ".webm": "video/webm",
    ".mkv": "video/x-matroska",
    ".avi": "video/x-msvideo",
    ".mov": "video/quicktime",
    ".wmv": "video/x-ms-wmv",
    ".flv": "video/x-flv",
    ".mpeg": "video/mpeg",
    ".mpg": "video/mpeg",
    ".3gp": "video/3gpp",
}

_MEDIA_CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "Origin, Accept, Content-Type, Range, X-Requested-With, X-CSRF-Token",
    "Access-Control-Expose-Headers": "Content-Length, Content-Range, Accept-Ranges, Content-Type",
}

_RANGE_RE = re.compile(r"^bytes=(\d+)-(\d*)$")


def media_cache_dir() -> Path:
    """Caché escribible de enlaces a vídeos (evita query strings largos en la URL)."""
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    d = Path(base) / "organizador-ayn" / "om-media"
    d.mkdir(parents=True, exist_ok=True)
    return d


def mime_for_path(path: Path) -> str:
    ext = path.suffix.lower()
    mime = _VIDEO_MIME.get(ext)
    if mime is None:
        mime, _ = mimetypes.guess_type(path.name)
    return mime or "application/octet-stream"


class _RangeReader:
    """Lee solo el tramo solicitado (streaming compatible con WebKit)."""

    def __init__(self, fh, remaining: int) -> None:
        self._fh = fh
        self._remaining = remaining

    def read(self, size: int = -1) -> bytes:
        if self._remaining <= 0:
            return b""
        if size < 0 or size > self._remaining:
            size = self._remaining
        chunk = self._fh.read(size)
        self._remaining -= len(chunk)
        return chunk

    def close(self) -> None:
        self._fh.close()


def _stream_file_range(path: Path, mime: str) -> bottle.HTTPResponse:
    size = path.stat().st_size
    headers = {
        "Content-Type": mime,
        "Accept-Ranges": "bytes",
        "Cache-Control": "no-store",
    }
    range_header = bottle.request.environ.get("HTTP_RANGE", "")
    match = _RANGE_RE.match(range_header.strip()) if range_header else None

    if not match:
        headers["Content-Length"] = str(size)
        return bottle.HTTPResponse(body=open(path, "rb"), headers=headers)

    start = int(match.group(1))
    end = int(match.group(2)) if match.group(2) else size - 1
    end = min(max(start, end), size - 1)
    length = end - start + 1

    fh = open(path, "rb")
    fh.seek(start)
    headers["Content-Range"] = f"bytes {start}-{end}/{size}"
    headers["Content-Length"] = str(length)
    return bottle.HTTPResponse(body=_RangeReader(fh, length), status=206, headers=headers)


def _safe_cache_name(filename: str) -> str | None:
    name = Path(filename).name
    if not name or name != filename or ".." in name:
        return None
    return name


def build_media_stream_url(path: Path, *, transcode: bool = False, format: str = "") -> str:
    """URL en /media (ruta exacta: no la intercepta el catch-all de PyWebView)."""
    params: dict[str, str] = {"path": str(path.resolve())}
    if transcode:
        params["transcode"] = "1"
        fmt = (format or ("webm" if viewer_prefers_webm() else "mp4")).lower()
        if fmt in ("webm", "mp4"):
            params["format"] = fmt
    return f"/media?{urllib.parse.urlencode(params, quote_via=urllib.parse.quote)}"


def publish_media_url(path: Path) -> str:
    return build_media_stream_url(path)


def publish_transcode_url(path: Path) -> str:
    return build_media_stream_url(path, transcode=True)


def publish_viewer_playback_url(path: Path) -> str:
    """URL corta al caché transcodificado (evita query strings con rutas con espacios)."""
    from .core.video_transcode import publish_mp4_playback_name, publish_webm_playback_name

    resolved = path.resolve()
    if viewer_prefers_webm():
        return f"/om-webm/{publish_webm_playback_name(resolved)}"
    return f"/om-transcode/{publish_mp4_playback_name(resolved)}"


def build_media_file_url(path: Path) -> str:
    return build_media_stream_url(path)


def _serve_media_file() -> bottle.HTTPResponse | str:
    path_str = bottle.request.query.path
    if not path_str:
        return bottle.HTTPError(400, "Parámetro 'path' requerido")

    try:
        p = resolve_file_path(urllib.parse.unquote_plus(path_str))
    except ValueError:
        return bottle.HTTPError(404, "Archivo no encontrado")

    transcode = str(bottle.request.query.get("transcode", "")).lower() in ("1", "true", "yes")
    if transcode:
        if p.suffix.lower() not in MediaOrganizer.VIDEO_EXTENSIONS:
            return bottle.HTTPError(400, "Solo se transcodifican vídeos")
        fmt = str(bottle.request.query.get("format", "")).lower()
        if not fmt:
            fmt = "webm" if viewer_prefers_webm() else "mp4"
        try:
            if fmt == "webm":
                out = ensure_transcoded_webm(p)
                return _stream_file_range(out, "video/webm")
            out = ensure_transcoded_mp4(p)
            return _stream_file_range(out, "video/mp4")
        except Exception as exc:
            return bottle.HTTPError(500, f"No se pudo preparar el vídeo: {exc}")

    return _stream_file_range(p, mime_for_path(p))


def _serve_cached_media(filename: str) -> bottle.HTTPResponse | str:
    name = _safe_cache_name(filename)
    if not name:
        return bottle.HTTPError(403, "Nombre inválido")

    cached = media_cache_dir() / name
    if cached.is_symlink():
        try:
            p = cached.resolve()
        except OSError:
            return bottle.HTTPError(404, "Archivo no encontrado")
    elif cached.is_file():
        p = cached
    else:
        return bottle.HTTPError(404, "Archivo no encontrado")

    if not p.is_file():
        return bottle.HTTPError(404, "Archivo no encontrado")
    return _stream_file_range(p, mime_for_path(p))


def _serve_transcoded_media(filename: str) -> bottle.HTTPResponse | str:
    from .core.video_transcode import ensure_transcoded_mp4, resolve_transcode_source, transcode_cache_dir

    name = _safe_cache_name(filename)
    if not name:
        return bottle.HTTPError(403, "Nombre inválido")

    root = str(transcode_cache_dir())
    cached = transcode_cache_dir() / name
    if not cached.is_file() or cached.stat().st_size <= 512:
        source = resolve_transcode_source(name)
        if source is None:
            return bottle.HTTPError(404, "Archivo no encontrado")
        try:
            ensure_transcoded_mp4(source)
        except Exception as exc:
            return bottle.HTTPError(500, f"No se pudo preparar el vídeo: {exc}")

    return bottle.static_file(name, root=root, mimetype="video/mp4")


def _serve_transcoded_webm(filename: str) -> bottle.HTTPResponse | str:
    from .core.video_transcode import ensure_transcoded_webm, resolve_webm_source, transcode_cache_dir

    name = _safe_cache_name(filename)
    if not name:
        return bottle.HTTPError(403, "Nombre inválido")

    root = str(transcode_cache_dir())
    cached = transcode_cache_dir() / name
    if not cached.is_file() or cached.stat().st_size <= 512:
        source = resolve_webm_source(name)
        if source is None:
            return bottle.HTTPError(404, "Archivo no encontrado")
        try:
            ensure_transcoded_webm(source)
        except Exception as exc:
            return bottle.HTTPError(500, f"No se pudo preparar el vídeo: {exc}")

    return bottle.static_file(name, root=root, mimetype="video/webm")


def _apply_media_cors() -> None:
    for key, value in _MEDIA_CORS_HEADERS.items():
        bottle.response.headers[key] = value


def register_media_routes(app: bottle.Bottle) -> None:
    """Monta rutas de medios en el Bottle app de PyWebView."""

    @app.route("/om-media/<filename:path>", method=["OPTIONS"])
    def om_media_options(filename: str):
        _ = filename
        _apply_media_cors()
        return ""

    @app.route("/om-media/<filename:path>", method=["GET"])
    def om_media_get(filename: str):
        _apply_media_cors()
        return _serve_cached_media(filename)

    @app.route("/media", method=["OPTIONS"])
    def media_options():
        _apply_media_cors()
        return ""

    @app.route("/media", method=["GET"])
    def media_get():
        _apply_media_cors()
        return _serve_media_file()

    @app.route("/om-transcode/<filename:path>", method=["OPTIONS"])
    def om_transcode_options(filename: str):
        _ = filename
        _apply_media_cors()
        return ""

    @app.route("/om-transcode/<filename:path>", method=["GET"])
    def om_transcode_get(filename: str):
        _apply_media_cors()
        return _serve_transcoded_media(filename)

    @app.route("/om-webm/<filename:path>", method=["OPTIONS"])
    def om_webm_options(filename: str):
        _ = filename
        _apply_media_cors()
        return ""

    @app.route("/om-webm/<filename:path>", method=["GET"])
    def om_webm_get(filename: str):
        _apply_media_cors()
        return _serve_transcoded_webm(filename)

    @app.hook("after_request")
    def _media_cors_after_request():
        path = bottle.request.path
        if (
            path == "/media"
            or path.startswith("/om-media/")
            or path.startswith("/om-transcode/")
            or path.startswith("/om-webm/")
        ):
            _apply_media_cors()


# Servidor independiente solo para desarrollo con Vite (proxy /media → :51234)
media_app = bottle.Bottle()
register_media_routes(media_app)


def start_media_server(port: int = 51234) -> None:
    """Arranca el servidor de medios en un hilo daemon (modo desarrollo)."""

    def _run() -> None:
        bottle.run(app=media_app, host="127.0.0.1", port=port, quiet=True)

    threading.Thread(target=_run, daemon=True).start()
