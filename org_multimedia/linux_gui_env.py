"""Entorno para PyWebView en Linux (GTK WebKit vs Qt WebEngine)."""

from __future__ import annotations

import os
import sys


def prepare_linux_gui_env() -> None:
    """Configura backend y variables para WebKitGTK o Qt WebEngine.

    ORGANIZADOR_PREFER_QT=1 — fuerza PYWEBVIEW_GUI=qt (Chromium vía Qt WebEngine).
    ORGANIZADOR_QT_API — opcional: pyqt6 (defecto), pyside6, pyqt5, pyside2.
    Hay que fijar QT_API antes de importar qtpy: si no, qtpy elige PyQt5 y falla sin PyQt5.QtWebChannel.

    ORGANIZADOR_WEBKIT_TRY_GPU=1 — en GTK, intenta DMA-BUF (riesgo pantalla en blanco).
    ORGANIZADOR_ALLOW_WAYLAND_GTK=1 — no fuerza GDK_BACKEND=x11 (solo GTK).
    """
    if not sys.platform.startswith("linux"):
        return

    prefer_qt = os.environ.get("ORGANIZADOR_PREFER_QT", "").lower() in ("1", "true", "yes")
    if prefer_qt:
        os.environ["PYWEBVIEW_GUI"] = "qt"

    if not os.environ.get("PYWEBVIEW_GUI"):
        os.environ["PYWEBVIEW_GUI"] = "gtk"

    gui = os.environ.get("PYWEBVIEW_GUI", "gtk").lower()

    if gui == "qt":
        # qtpy importa PyQt5 antes que PyQt6 si no se fuerza; pywebview Qt usa QtWebEngine vía qtpy
        if "QT_API" not in os.environ:
            os.environ["QT_API"] = os.environ.get("ORGANIZADOR_QT_API", "pyqt6")
        return

    if gui != "gtk":
        return

    try_gpu = os.environ.get("ORGANIZADOR_WEBKIT_TRY_GPU", "").lower() in ("1", "true", "yes")
    if not try_gpu:
        os.environ["WEBKIT_DISABLE_DMABUF_RENDERER"] = "1"
    else:
        os.environ.pop("WEBKIT_DISABLE_DMABUF_RENDERER", None)

    allow_native = os.environ.get("ORGANIZADOR_ALLOW_WAYLAND_GTK", "").lower() in (
        "1",
        "true",
        "yes",
    )
    if allow_native:
        return

    wayland = bool(os.environ.get("WAYLAND_DISPLAY")) or (
        os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"
    )
    if not wayland:
        return

    os.environ["GDK_BACKEND"] = "x11"
