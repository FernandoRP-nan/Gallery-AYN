"""Evita ventanas de consola al lanzar procesos hijos en Windows (GUI / PyInstaller)."""

from __future__ import annotations

import subprocess
import sys
from typing import Any

_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)


def subprocess_hide_window_kwargs() -> dict[str, Any]:
    if not sys.platform.startswith("win"):
        return {}
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = subprocess.SW_HIDE
    return {"creationflags": _CREATE_NO_WINDOW, "startupinfo": si}


def run_hidden(*popenargs: Any, **kwargs: Any) -> subprocess.CompletedProcess[Any]:
    kw = subprocess_hide_window_kwargs()
    kw.update(kwargs)
    return subprocess.run(*popenargs, **kw)


def popen_hidden(*popenargs: Any, **kwargs: Any) -> subprocess.Popen[Any]:
    kw = subprocess_hide_window_kwargs()
    kw.update(kwargs)
    return subprocess.Popen(*popenargs, **kw)
