"""Entrypoint principal: interfaz web (Svelte) vía PyWebView."""

from __future__ import annotations

import sys
import traceback

from .app_webview import main as main_webview


def _notify_ui_failure(exc: BaseException) -> None:
    """Muestra el error real al usuario cuando la UI web no arranca."""
    tb = traceback.format_exc()
    msg = (
        "No se pudo iniciar la interfaz web (PyWebView + Svelte).\n\n"
        "Comprueba en Windows:\n"
        "• .NET Framework 4.7.2 o superior.\n"
        "• Si el zip se descargó de internet: clic derecho en el .zip → Propiedades → «Desbloquear» "
        "→ volver a extraer.\n"
        "• Runtime WebView2 instalado (Edge WebView2).\n"
        "• Descomprimir el zip completo en una carpeta real; no ejecutar el .exe desde dentro del zip.\n"
        "• Antivirus sin bloquear la carpeta del programa.\n\n"
        f"Detalle técnico:\n{tb[:1600]}"
    )
    try:
        if sys.platform == "win32":
            import ctypes

            ctypes.windll.user32.MessageBoxW(0, msg, "Galería AYN — error al iniciar", 0x10)
            return
    except Exception:
        pass
    print(msg, file=sys.stderr)


def main() -> None:
    try:
        main_webview()
    except Exception as e:
        _notify_ui_failure(e)
        raise SystemExit(1) from e
