"""Entorno PyWebView en Windows (pythonnet / .NET, archivos bloqueados por descarga)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from .bundle_paths import project_root


def _unblock_file(path: Path) -> None:
    """Quita Zone.Identifier (MOTW) para que .NET pueda cargar DLLs del portable."""
    if not sys.platform.startswith("win"):
        return
    try:
        os.remove(f"{path}:Zone.Identifier")
    except OSError:
        pass


def _unblock_tree(root: Path) -> None:
    if not root.is_dir():
        return
    for item in root.rglob("*"):
        if item.is_file():
            _unblock_file(item)


def prepare_windows_gui_env() -> None:
    """Antes de importar webview: desbloquea el bundle y prioriza DLLs locales."""
    if not sys.platform.startswith("win"):
        return

    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        _unblock_file(Path(sys.executable))
        _unblock_tree(exe_dir)
        if hasattr(sys, "_MEIPASS"):
            _unblock_tree(Path(sys._MEIPASS))

    runtime_dll = project_root() / "pythonnet" / "runtime" / "Python.Runtime.dll"
    if runtime_dll.is_file():
        _unblock_file(runtime_dll)
