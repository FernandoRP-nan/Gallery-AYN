"""Servidor de streaming de vídeo/SVG para la galería web."""

from __future__ import annotations

import mimetypes
import threading
import urllib.parse
from pathlib import Path

import bottle

from .core.fs_path import resolve_file_path
from .core.media_organizer import MediaOrganizer

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
}


def _serve_media_file() -> bottle.HTTPResponse | str:
    path_str = bottle.request.query.path
    if not path_str:
        return bottle.HTTPError(400, "Parámetro 'path' requerido")

    try:
        p = resolve_file_path(urllib.parse.unquote(path_str))
    except ValueError:
        return bottle.HTTPError(404, "Archivo no encontrado")

    # bottle.static_file gestiona Range (imprescindible para vídeo)
    ext = p.suffix.lower()
    mime = _VIDEO_MIME.get(ext)
    if mime is None and ext in MediaOrganizer.VIDEO_EXTENSIONS:
        mime, _ = mimetypes.guess_type(p.name)
    if mime is None:
        mime, _ = mimetypes.guess_type(p.name)
    return bottle.static_file(p.name, root=str(p.parent), mimetype=mime)


def _apply_media_cors() -> None:
    for key, value in _MEDIA_CORS_HEADERS.items():
        bottle.response.headers[key] = value


def register_media_routes(app: bottle.Bottle) -> None:
    """Monta /media en un Bottle app (mismo origen que la UI de PyWebView)."""

    @app.route("/media", method=["OPTIONS"])
    def media_options():
        _apply_media_cors()
        return ""

    @app.route("/media", method=["GET"])
    def media_get():
        _apply_media_cors()
        return _serve_media_file()

    @app.hook("after_request")
    def _media_cors_after_request():
        if bottle.request.path == "/media":
            _apply_media_cors()


def build_media_file_url(path: Path) -> str:
    """URL relativa al origen de la UI (evita bloqueos cross-origin en WebKit)."""
    return f"/media?path={urllib.parse.quote(str(path))}"


# Servidor independiente solo para desarrollo con Vite (proxy /media → :51234)
media_app = bottle.Bottle()
register_media_routes(media_app)


def start_media_server(port: int = 51234) -> None:
    """Arranca el servidor de medios en un hilo daemon (modo desarrollo)."""

    def _run() -> None:
        bottle.run(app=media_app, host="127.0.0.1", port=port, quiet=True)

    threading.Thread(target=_run, daemon=True).start()
