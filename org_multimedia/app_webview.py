"""Entrypoint PyWebView para interfaz web Svelte."""

from __future__ import annotations

import os
from pathlib import Path

from .linux_gui_env import prepare_linux_gui_env

from .settings import load_app_settings
from .web_api import WebApi


def _resolve_frontend_url() -> str:
    env_url = os.environ.get("ORGANIZADOR_WEBUI_URL", "").strip()
    if env_url:
        return env_url
    base = Path(__file__).resolve().parent.parent
    dist = base / "webui" / "dist" / "index.html"
    if dist.exists():
        # Ruta absoluta (no file://): con http_server=True pywebview sirve por http://127.0.0.1 — mejor GPU/WebKit
        return str(dist.resolve())
    # Fallback a dev server Vite por defecto.
    return "http://127.0.0.1:5173"


def main() -> None:
    prepare_linux_gui_env()
    import webview  # type: ignore

    settings = load_app_settings()
    api = WebApi()
    window = webview.create_window(
        "Organizador Multimedia",
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
