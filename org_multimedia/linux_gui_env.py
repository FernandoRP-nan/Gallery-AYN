"""Entorno para PyWebView en Linux (GTK WebKit vs Qt WebEngine)."""

from __future__ import annotations

import os
import sys


def _merge_qt_chromium_flags(*flags: str) -> None:
    """Añade flags a QTWEBENGINE_CHROMIUM_FLAGS sin pisar los que ya hubiera."""
    key = "QTWEBENGINE_CHROMIUM_FLAGS"
    parts = [x for x in os.environ.get(key, "").split() if x]
    seen = set(parts)
    for f in flags:
        if f and f not in seen:
            parts.append(f)
            seen.add(f)
    os.environ[key] = " ".join(parts)


def prepare_linux_gui_env() -> None:
    """Configura backend y variables para WebKitGTK o Qt WebEngine.

    ORGANIZADOR_FORCE_GTK=1 — fuerza WebKitGTK aunque tengas ORGANIZADOR_PREFER_QT (útil si Qt falla).

    ORGANIZADOR_PREFER_QT=1 — fuerza PYWEBVIEW_GUI=qt (Chromium vía Qt WebEngine).
    ORGANIZADOR_QT_API — opcional: pyqt6 (defecto), pyside6, pyqt5, pyside2.
    Hay que fijar QT_API antes de importar qtpy: si no, qtpy elige PyQt5 y falla sin PyQt5.QtWebChannel.

    ORGANIZADOR_WEBKIT_TRY_GPU=1 — en GTK, intenta DMA-BUF (riesgo pantalla en blanco).
    ORGANIZADOR_ALLOW_WAYLAND_GTK=1 — no fuerza GDK_BACKEND=x11 (solo GTK).

    Qt WebEngine (Chromium): en Fedora y otras distros la vista puede quedar en blanco sin
    --no-sandbox (pywebview hace algo parecido en Arch/Manjaro). Se añade por defecto con Qt;
    ORGANIZADOR_QT_SKIP_NO_SANDBOX=1 lo evita. Si sigue en blanco o ves fallos GBM/Vulkan:
    ORGANIZADOR_QT_DISABLE_GPU=1 añade --disable-gpu al proceso de render.
    """
    if not sys.platform.startswith("linux"):
        return

    force_gtk = os.environ.get("ORGANIZADOR_FORCE_GTK", "").lower() in ("1", "true", "yes")
    prefer_qt = os.environ.get("ORGANIZADOR_PREFER_QT", "").lower() in ("1", "true", "yes")
    if force_gtk:
        os.environ["PYWEBVIEW_GUI"] = "gtk"
    elif prefer_qt:
        os.environ["PYWEBVIEW_GUI"] = "qt"

    if not os.environ.get("PYWEBVIEW_GUI"):
        os.environ["PYWEBVIEW_GUI"] = "gtk"

    gui = os.environ.get("PYWEBVIEW_GUI", "gtk").lower()

    if gui == "qt":
        # qtpy importa PyQt5 antes que PyQt6 si no se fuerza; pywebview Qt usa QtWebEngine vía qtpy
        if "QT_API" not in os.environ:
            os.environ["QT_API"] = os.environ.get("ORGANIZADOR_QT_API", "pyqt6")
        skip_sandbox = os.environ.get("ORGANIZADOR_QT_SKIP_NO_SANDBOX", "").lower() in (
            "1",
            "true",
            "yes",
        )
        if not skip_sandbox:
            _merge_qt_chromium_flags("--no-sandbox")
        if os.environ.get("ORGANIZADOR_QT_DISABLE_GPU", "").lower() in ("1", "true", "yes"):
            _merge_qt_chromium_flags("--disable-gpu")
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
