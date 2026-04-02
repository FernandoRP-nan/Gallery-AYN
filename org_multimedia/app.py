"""Entrypoint principal: prioriza PyWebView y usa Tkinter como fallback."""

from __future__ import annotations

from .app_tk import main as main_tk
from .app_webview import main as main_webview


def main() -> None:
    try:
        main_webview()
    except Exception:
        main_tk()
