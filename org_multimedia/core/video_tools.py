"""Localización de ffmpeg/ffprobe (PATH, bundle portable, variable de entorno)."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def _exe(name: str) -> str:
    return f"{name}.exe" if sys.platform == "win32" else name


def _candidate_dirs() -> list[Path]:
    dirs: list[Path] = []
    env_dir = os.environ.get("ORGANIZADOR_FFMPEG_DIR", "").strip()
    if env_dir:
        dirs.append(Path(env_dir).expanduser())
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        dirs.extend(
            [
                exe_dir / "tools" / "ffmpeg",
                exe_dir / "_internal" / "tools" / "ffmpeg",
                exe_dir / "ffmpeg",
            ]
        )
    try:
        from ..bundle_paths import project_root

        root = project_root()
        dirs.extend([root / "tools" / "ffmpeg", root / "ffmpeg"])
    except Exception:
        pass
    return dirs


def resolve_ffmpeg() -> str | None:
    forced = os.environ.get("ORGANIZADOR_FFMPEG", "").strip()
    if forced and Path(forced).is_file():
        return str(Path(forced).resolve())
    for d in _candidate_dirs():
        p = d / _exe("ffmpeg")
        if p.is_file():
            return str(p.resolve())
    found = shutil.which("ffmpeg")
    return found or None


def resolve_ffprobe() -> str | None:
    forced = os.environ.get("ORGANIZADOR_FFPROBE", "").strip()
    if forced and Path(forced).is_file():
        return str(Path(forced).resolve())
    for d in _candidate_dirs():
        p = d / _exe("ffprobe")
        if p.is_file():
            return str(p.resolve())
    found = shutil.which("ffprobe")
    return found or None


def ffmpeg_available() -> bool:
    return resolve_ffmpeg() is not None


def ffprobe_available() -> bool:
    return resolve_ffprobe() is not None
