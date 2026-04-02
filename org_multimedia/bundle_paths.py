"""Rutas al proyecto empaquetado (PyInstaller en Windows) o al árbol de fuentes en desarrollo."""

from __future__ import annotations

import sys
from pathlib import Path


def project_root() -> Path:
    """Raíz donde está `webui/dist` (repo en desarrollo o carpeta extraída del .exe)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parent.parent
