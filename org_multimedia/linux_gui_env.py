"""Entorno para PyWebView en Linux (GTK WebKit vs Qt WebEngine)."""

from __future__ import annotations

import importlib.util
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


def _qt_webengine_available() -> bool:
    """Comprueba si hay Qt WebEngine instalado (reproducción de vídeo más fiable)."""
    pairs = (
        ("PyQt6", "PyQt6.QtWebEngineWidgets"),
        ("PyQt5", "PyQt5.QtWebEngineWidgets"),
        ("PySide6", "PySide6.QtWebEngineWidgets"),
        ("PySide2", "PySide2.QtWebEngineWidgets"),
    )
    for pkg, webeng in pairs:
        if importlib.util.find_spec(pkg) and importlib.util.find_spec(webeng):
            return True
    return False


def _read_prefer_qt_from_settings() -> bool | None:
    try:
        from .core.settings import load_app_settings

        raw = load_app_settings().get("web_prefer_qt_engine")
        if raw is None:
            return None
        return bool(raw)
    except Exception:
        return None


def prepare_linux_gui_env() -> None:
    """Configura backend y variables para WebKitGTK o Qt WebEngine.

    ORGANIZADOR_FORCE_GTK=1 — fuerza WebKitGTK (útil si Qt falla).

    ORGANIZADOR_PREFER_QT=1 — fuerza Qt WebEngine (Chromium).

    Por defecto en Linux: Qt si está instalado (vídeos MP4 en WebKitGTK suelen fallar en Fedora).
    Ajuste persistente: web_prefer_qt_engine en ~/.config/organizador_multimedia/settings.json
    (requiere reiniciar la app).
    """
    if not sys.platform.startswith("linux"):
        return

    force_gtk = os.environ.get("ORGANIZADOR_FORCE_GTK", "").lower() in ("1", "true", "yes")
    prefer_qt = os.environ.get("ORGANIZADOR_PREFER_QT", "").lower() in ("1", "true", "yes")
    settings_qt = _read_prefer_qt_from_settings()

    if force_gtk:
        os.environ["PYWEBVIEW_GUI"] = "gtk"
    elif prefer_qt or settings_qt is True:
        os.environ["PYWEBVIEW_GUI"] = "qt"
    elif settings_qt is False:
        os.environ["PYWEBVIEW_GUI"] = "gtk"
    elif not os.environ.get("PYWEBVIEW_GUI"):
        os.environ["PYWEBVIEW_GUI"] = "qt" if _qt_webengine_available() else "gtk"

    gui = os.environ.get("PYWEBVIEW_GUI", "gtk").lower()

    if gui == "qt":
        if "QT_API" not in os.environ:
            os.environ["QT_API"] = os.environ.get("ORGANIZADOR_QT_API", "pyqt6")
        skip_sandbox = os.environ.get("ORGANIZADOR_QT_SKIP_NO_SANDBOX", "").lower() in (
            "1",
            "true",
            "yes",
        )
        if not skip_sandbox:
            _merge_qt_chromium_flags("--no-sandbox")
        _merge_qt_chromium_flags(
            "--autoplay-policy=no-user-gesture-required",
            "--disable-features=BlockInsecurePrivateNetworkRequests",
        )
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
