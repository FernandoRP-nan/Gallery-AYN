"""Entrypoint PyWebView para interfaz web Svelte."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from .bundle_paths import project_root
from .linux_gui_env import prepare_linux_gui_env

from .pywebview_bridge_return import patch_js_bridge_return_value
from .pywebview_qt_json import patch_qt_qjson_bridge
from .settings import load_app_settings
from .web_api import WebApi


def _resolve_frontend_url() -> str:
    env_url = os.environ.get("ORGANIZADOR_WEBUI_URL", "").strip()
    if env_url:
        return env_url
    base = project_root()
    dist = base / "webui" / "dist" / "index.html"
    if dist.exists():
        # Ruta absoluta (no file://): con http_server=True pywebview sirve por http://127.0.0.1 — mejor GPU/WebKit
        # WebView2 puede cachear agresivamente entre versiones; ?v=mtime fuerza recarga al actualizar el .exe.
        try:
            v = str(int(dist.stat().st_mtime_ns))
        except OSError:
            v = "0"
        uri = dist.resolve().as_uri()
        parts = urlsplit(uri)
        query = f"v={v}"
        if parts.query:
            query = f"{parts.query}&{query}"
        return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))
    # En ejecutable empaquetado no hay fallback a Vite: si falta dist/, otro proceso en :5173
    # podría mostrar una UI antigua o ajena y parecer "versión incorrecta".
    if getattr(sys, "frozen", False):
        raise RuntimeError(
            "No se encontró la interfaz empaquetada (webui/dist/index.html). "
            "Comprueba que el zip se descomprimió completo, que el antivirus no borró "
            "carpetas dentro de _internal y que no falta el directorio webui/dist."
        )
    # Solo en desarrollo: servidor Vite por defecto.
    return "http://127.0.0.1:5173"


def main() -> None:
    prepare_linux_gui_env()
    import webview  # type: ignore

    patch_js_bridge_return_value()
    patch_qt_qjson_bridge()

    settings = load_app_settings()
    api = WebApi()
    window = webview.create_window(
        "Galería AYN",
        _resolve_frontend_url(),
        js_api=api,
        width=1280,
        height=820,
        min_size=(980, 620),
        maximized=True,
    )
    webview.start(
        gui=None,
        debug=bool(os.environ.get("ORGANIZADOR_WEB_DEBUG", "")),
        # Sirve dist/ por http://127.0.0.1:puerto (mejor capas GPU que file:// en WebKitGTK)
        http_server=True,
    )
    _ = (window, settings)
