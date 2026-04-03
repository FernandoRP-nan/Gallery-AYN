"""Entrypoint principal: prioriza PyWebView y usa Tkinter como fallback."""

from __future__ import annotations

import os
import sys
import traceback

from .app_tk import main as main_tk
from .app_webview import main as main_webview


def _notify_webview_failure(exc: BaseException) -> None:
    """Aviso visible: el fallback Tk parece otra versión y confunde si ocurre en silencio."""
    tb = traceback.format_exc()
    msg = (
        "No se pudo iniciar la interfaz web (PyWebView).\n"
        "En Windows suele faltar el runtime WebView2 o hay un bloqueo del antivirus.\n\n"
        f"Detalle:\n{tb[:1800]}"
    )
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Galería AYN — error al iniciar", msg)
        root.destroy()
    except Exception:
        print(msg, file=sys.stderr)


def main() -> None:
    try:
        main_webview()
    except Exception as e:
        # En .exe empaquetado no abrir Tk en silencio: es la UI “clásica” y parece versión vieja.
        if getattr(sys, "frozen", False) and not os.environ.get("ORGANIZADOR_ALLOW_TK_FALLBACK"):
            _notify_webview_failure(e)
            raise SystemExit(1) from e
        main_tk()
