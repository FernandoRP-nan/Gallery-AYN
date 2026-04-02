"""Punto de entrada para `pip install` / comando `organizador`."""

from __future__ import annotations


def main() -> None:
    # Misma secuencia que `python -m org_multimedia` (variables de entorno + ventana).
    from .linux_gui_env import prepare_linux_gui_env

    prepare_linux_gui_env()
    from .app import main as app_main

    app_main()
