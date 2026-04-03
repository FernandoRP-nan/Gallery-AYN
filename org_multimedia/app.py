"""Entrypoint principal: interfaz web (Svelte) vía PyWebView; sin fallback a Tk salvo variable de entorno."""

from __future__ import annotations

import os
import sys
import traceback

from .app_tk import main as main_tk
from .app_webview import main as main_webview


def _notify_ui_failure(exc: BaseException) -> None:
    """Muestra el error real; la UI Tk legacy ya no se usa por defecto."""
    tb = traceback.format_exc()
    msg = (
        "No se pudo iniciar la interfaz web (PyWebView + Svelte).\n\n"
        "Comprueba en Windows:\n"
        "• Runtime WebView2 instalado (Edge WebView2).\n"
        "• El zip descomprimido entero en una carpeta real (Escritorio, etc.); "
        "no ejecutar el .exe desde dentro del .zip.\n"
        "• Antivirus sin bloquear la carpeta del programa.\n\n"
        f"Detalle técnico:\n{tb[:1600]}"
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
    # Solo desarrollo / depuración: UI antigua en Tk (ORGANIZADOR_LEGACY_TK_UI=1).
    if os.environ.get("ORGANIZADOR_LEGACY_TK_UI"):
        main_tk()
        return
    try:
        main_webview()
    except Exception as e:
        _notify_ui_failure(e)
        raise SystemExit(1) from e
